"""
Live End-to-End Smoke Test for Admin Console and Escalation System.
Tests all four mandatory scenarios against a running backend:
  1. Full refund escalation workflow (Chat -> Pending Approval -> Take -> Reply -> Polling -> Approve -> Bilingual Notify -> Resolve).
  2. Chat deduplication (single active case per session) & refund rejection with bilingual notification.
  3. Concurrent case assignment race condition (optimistic locking / SELECT FOR UPDATE -> exactly one 200, one 409).
  4. Concurrent refund approval race condition (exactly one 200, one 409, single payout).
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
ADMIN_HEADERS = {"X-Requested-With": "admin-console"}


async def maybe_reseed_db():
    try:
        from app.db import async_session_factory
        from scripts.seed import seed_data
        print("[SETUP] Re-seeding database for idempotent clean run...")
        async with async_session_factory() as session:
            await seed_data(session)
        print("[SETUP] Database seeded successfully.")
    except Exception as e:
        print(f"[SETUP] Skipping direct DB re-seed ({e}). Running against existing data.")


def log_step(name: str) -> None:
    print(f"\n[SCENARIO] {name}")


def log_check(msg: str) -> None:
    print(f"  [PASS] {msg}")


async def create_chat_message(client: httpx.AsyncClient, customer_id: str, message: str, session_id: str | None = None) -> dict:
    payload = {
        "customer_id": customer_id,
        "message": message,
        "channel": "web",
    }
    if session_id:
        payload["session_id"] = session_id
    res = await client.post("/chat", json=payload, timeout=30.0)
    assert res.status_code == 200, f"Chat failed ({res.status_code}): {res.text}"
    return res.json()


async def get_demo_customers(client: httpx.AsyncClient) -> list[dict]:
    res = await client.get("/customers/demo", timeout=10.0)
    if res.status_code == 200:
        data = res.json()
        if isinstance(data, list):
            return data
        return data.get("customers", [])
    return []


async def test_scenario_1_refund_workflow():
    log_step("Scenario 1: High-Value Refund Workflow & Customer Chat Polling")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as anon_client, httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as agent_client:
        # 1. Fetch Deepa Raman who owns ORD-10012 (Amount: Rs 2001.00)
        customers = await get_demo_customers(anon_client)
        deepa = next((c for c in customers if "Deepa" in c["name"]), None)
        assert deepa, "Customer Deepa Raman not found in demo customers"
        customer_id = deepa["id"]

        # 2. Customer chats requesting refund for ORD-10012
        chat_resp = await create_chat_message(
            anon_client,
            customer_id=customer_id,
            message="I want to return and get a refund for order ORD-10012 because it arrived defective.",
        )
        print("DEBUG chat_resp:", chat_resp)
        session_id = chat_resp["session_id"]
        assert chat_resp["requires_human"] is True
        log_check("Customer requested refund > ₹2000; bot marked requires_human=True")

        # 3. Agent logs in
        login_res = await agent_client.post(
            "/admin/auth/login",
            json={"email": "agent@example.com", "password": "AgentPass123!"},
            headers=ADMIN_HEADERS,
        )
        assert login_res.status_code == 200, f"Agent login failed: {login_res.text}"
        log_check("Agent logged in successfully via /admin/auth/login")

        # 4. Agent finds the case in /admin/cases
        cases_res = await agent_client.get(
            "/admin/cases",
            params={"status": "open", "reason_type": "refund_pending_approval"},
            headers=ADMIN_HEADERS,
        )
        assert cases_res.status_code == 200
        items = cases_res.json()["items"]
        case_item = next((item for item in items if item["customer"]["id"] == customer_id), None)
        assert case_item, f"Expected escalation case for customer {customer_id} not found"
        case_id = case_item["id"]
        log_check(f"High-priority escalation case found: {case_id}")

        # 5. Agent inspects case detail
        detail_res = await agent_client.get(f"/admin/cases/{case_id}", headers=ADMIN_HEADERS)
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["status"] == "open"
        assert detail["linked_refund"] is not None
        assert float(detail["linked_refund"]["amount"]) == 2001.0
        version = detail["version"]
        log_check(f"Case detail inspected (Refund Amount: ₹2001.00, Version: {version})")

        # 6. Agent takes case
        take_res = await agent_client.post(
            f"/admin/cases/{case_id}/take",
            json={"version": version},
            headers=ADMIN_HEADERS,
        )
        assert take_res.status_code == 200
        updated_case = take_res.json()
        assert updated_case["status"] == "in_progress"
        version = updated_case["version"]
        log_check(f"Agent took case -> status=in_progress (Version: {version})")

        # 7. Agent replies to customer
        agent_reply_text = "Hello Deepa, I have reviewed your defect photos and approved your refund request."
        reply_res = await agent_client.post(
            f"/admin/cases/{case_id}/reply",
            json={"message": agent_reply_text},
            headers=ADMIN_HEADERS,
        )
        assert reply_res.status_code == 200
        version = reply_res.json()["version"]
        log_check(f"Agent posted reply to customer (Version: {version})")

        # 8. Customer polls /sessions/{session_id}/messages
        poll_res = await anon_client.get(
            f"/sessions/{session_id}/messages",
            params={"customer_id": customer_id},
        )
        assert poll_res.status_code == 200
        messages = poll_res.json()
        agent_msg = next((m for m in messages if m["role"] == "agent"), None)
        assert agent_msg is not None
        assert agent_msg["sender_label"] == "Support executive"
        assert agent_reply_text in agent_msg["content"]
        assert "agent@example.com" not in str(agent_msg)
        log_check("Customer polling verified: message labelled 'Support executive' with no identity leakage")

        # 9. Agent approves refund
        approve_res = await agent_client.post(
            f"/admin/cases/{case_id}/approve-refund",
            json={"version": version},
            headers=ADMIN_HEADERS,
        )
        assert approve_res.status_code == 200
        approved_case = approve_res.json()
        assert approved_case["linked_refund"]["status"] == "processed"
        version = approved_case["version"]
        log_check("Agent approved refund -> Mock payout executed, status=processed")

        # 10. Customer verifies bilingual approval notification
        poll_res_2 = await anon_client.get(
            f"/sessions/{session_id}/messages",
            params={"customer_id": customer_id},
        )
        assert poll_res_2.status_code == 200
        latest_msgs = poll_res_2.json()
        assert len(latest_msgs) > 0
        latest_text = latest_msgs[-1]["content"]
        assert "approved" in latest_text.lower() or "processed" in latest_text.lower()
        assert "ஒப்புதல்" in latest_text or "செயலாக்கப்பட்டது" in latest_text
        log_check("Customer verified bilingual approval message (English + Tamil)")

        # 11. Agent resolves case
        resolve_res = await agent_client.post(
            f"/admin/cases/{case_id}/resolve",
            json={"note": "Refund processed and customer notified.", "version": version},
            headers=ADMIN_HEADERS,
        )
        assert resolve_res.status_code == 200
        resolved_case = resolve_res.json()
        assert resolved_case["status"] == "resolved"
        assert resolved_case["resolution_note"] == "Refund processed and customer notified."
        log_check("Agent resolved case successfully")


async def test_scenario_2_deduplication_and_rejection():
    log_step("Scenario 2: Escalation Deduplication & Refund Rejection")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as anon_client, httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as agent_client:
        customers = await get_demo_customers(anon_client)
        karthik = next((c for c in customers if "Karthik" in c["name"]), None)
        assert karthik, "Customer Karthik Raja not found"
        customer_id = karthik["id"]

        # 1. Customer says "I want to talk to a human"
        chat_1 = await create_chat_message(
            anon_client,
            customer_id=customer_id,
            message="I want to talk to a human support agent",
        )
        session_id = chat_1["session_id"]
        assert chat_1["requires_human"] is True

        # 2. Customer repeats escalation request in SAME session
        chat_2 = await create_chat_message(
            anon_client,
            customer_id=customer_id,
            session_id=session_id,
            message="Please connect me to human support right now!",
        )
        assert chat_2["requires_human"] is True

        # 3. Verify exactly ONE active escalation exists for this session
        await agent_client.post(
            "/admin/auth/login",
            json={"email": "agent@example.com", "password": "AgentPass123!"},
            headers=ADMIN_HEADERS,
        )
        cases_res = await agent_client.get(
            "/admin/cases",
            params={"status": "open", "reason_type": "user_requested"},
            headers=ADMIN_HEADERS,
        )
        assert cases_res.status_code == 200
        matching = [c for c in cases_res.json()["items"] if c.get("session_id") == session_id]
        assert len(matching) == 1, f"Expected 1 deduplicated escalation for session, found {len(matching)}"
        log_check("Escalation deduplication verified: only 1 active case created for session")

        # 4. Test Rejection flow on a pending refund case
        # Find the seeded pending refund escalation for Karthik (ORD-10005)
        ref_cases = await agent_client.get(
            "/admin/cases",
            params={"status": "open", "reason_type": "refund_pending_approval"},
            headers=ADMIN_HEADERS,
        )
        assert ref_cases.status_code == 200
        karthik_case = next(c for c in ref_cases.json()["items"] if c["customer"]["id"] == customer_id)
        case_id = karthik_case["id"]

        # Fetch case detail to get session_id
        detail_res = await agent_client.get(f"/admin/cases/{case_id}", headers=ADMIN_HEADERS)
        ref_session_id = detail_res.json()["session_id"]

        # Agent takes the case
        take_res = await agent_client.post(
            f"/admin/cases/{case_id}/take",
            json={"version": karthik_case["version"]},
            headers=ADMIN_HEADERS,
        )
        assert take_res.status_code == 200
        version = take_res.json()["version"]

        # Agent rejects the refund
        rejection_reason = "Exceeded the 7-day return policy window."
        reject_res = await agent_client.post(
            f"/admin/cases/{case_id}/reject-refund",
            json={"reason": rejection_reason, "version": version},
            headers=ADMIN_HEADERS,
        )
        assert reject_res.status_code == 200
        rejected_case = reject_res.json()
        assert rejected_case["linked_refund"]["status"] == "rejected"
        log_check("Agent rejected refund with reason")

        # Verify customer received bilingual rejection notification
        poll_res = await anon_client.get(
            f"/sessions/{ref_session_id}/messages",
            params={"customer_id": customer_id},
        )
        assert poll_res.status_code == 200
        msgs = poll_res.json()
        assert len(msgs) > 0
        last_text = msgs[-1]["content"]
        assert "rejected" in last_text.lower()
        assert "நிராகரிக்கப்பட்டது" in last_text
        assert rejection_reason in last_text
        log_check("Customer verified bilingual rejection message with reason")


async def test_scenario_3_concurrent_case_take():
    log_step("Scenario 3: Concurrency Control - Concurrent Case Take")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as anon_client, \
               httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as agent_1, \
               httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as agent_2:

        # 1. Login agent 1 and agent 2 (admin)
        await agent_1.post("/admin/auth/login", json={"email": "agent@example.com", "password": "AgentPass123!"}, headers=ADMIN_HEADERS)
        await agent_2.post("/admin/auth/login", json={"email": "admin@example.com", "password": "AdminPass123!"}, headers=ADMIN_HEADERS)

        # 2. Create fresh escalation
        customers = await get_demo_customers(anon_client)
        suresh = next((c for c in customers if "Suresh" in c["name"]), customers[0])
        await create_chat_message(anon_client, customer_id=suresh["id"], message="I need a human agent now!")

        cases_res = await agent_1.get("/admin/cases", params={"status": "open"}, headers=ADMIN_HEADERS)
        target_case = next(c for c in cases_res.json()["items"] if c["customer"]["id"] == suresh["id"])
        case_id = target_case["id"]
        v = target_case["version"]

        # 3. Simultaneously attempt to take the case with both agents
        res1, res2 = await asyncio.gather(
            agent_1.post(f"/admin/cases/{case_id}/take", json={"version": v}, headers=ADMIN_HEADERS),
            agent_2.post(f"/admin/cases/{case_id}/take", json={"version": v}, headers=ADMIN_HEADERS),
            return_exceptions=True,
        )

        status_codes = sorted([res1.status_code, res2.status_code])
        assert status_codes == [200, 409], f"Expected exactly one 200 and one 409, got: {status_codes}"

        # Verify 409 error structure
        conflict_res = res1 if res1.status_code == 409 else res2
        assert "error" in conflict_res.json()
        log_check("Concurrency race resolved: exactly one agent won (200), one was rejected (409)")


async def test_scenario_4_concurrent_refund_approval():
    log_step("Scenario 4: Concurrency Control - Concurrent Refund Approval")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0), \
               httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as agent_client_1, \
               httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as agent_client_2:

        # Login admin sessions
        await agent_client_1.post("/admin/auth/login", json={"email": "admin@example.com", "password": "AdminPass123!"}, headers=ADMIN_HEADERS)
        await agent_client_2.post("/admin/auth/login", json={"email": "admin@example.com", "password": "AdminPass123!"}, headers=ADMIN_HEADERS)

        # Find an open refund escalation
        cases_res = await agent_client_1.get(
            "/admin/cases",
            params={"status": "open", "reason_type": "refund_pending_approval"},
            headers=ADMIN_HEADERS,
        )
        refund_cases = cases_res.json()["items"]
        assert len(refund_cases) > 0, "No pending refund cases available for test"
        target_case = refund_cases[0]
        case_id = target_case["id"]

        # Take the case first
        take_res = await agent_client_1.post(
            f"/admin/cases/{case_id}/take",
            json={"version": target_case["version"]},
            headers=ADMIN_HEADERS,
        )
        assert take_res.status_code == 200
        v = take_res.json()["version"]

        # Concurrently attempt approval with the same initial version
        res1, res2 = await asyncio.gather(
            agent_client_1.post(f"/admin/cases/{case_id}/approve-refund", json={"version": v}, headers=ADMIN_HEADERS),
            agent_client_2.post(f"/admin/cases/{case_id}/approve-refund", json={"version": v}, headers=ADMIN_HEADERS),
            return_exceptions=True,
        )

        status_codes = sorted([res1.status_code, res2.status_code])
        assert status_codes == [200, 409], f"Expected exactly one 200 and one 409, got: {status_codes}"

        log_check("Concurrent refund approval prevented double payout: exactly one 200 and one 409")


async def main():
    print("=" * 60)
    print("STARTING ADMIN CONSOLE & ESCALATION LIVE SMOKE TESTS")
    print(f"Target URL: {BASE_URL}")
    print("=" * 60)

    # Wait for backend to be ready
    for attempt in range(15):
        try:
            async with httpx.AsyncClient(base_url=BASE_URL) as c:
                r = await c.get("/health", timeout=2.0)
                if r.status_code == 200:
                    break
        except Exception:
            await asyncio.sleep(1.0)

    await maybe_reseed_db()

    try:
        await test_scenario_1_refund_workflow()
        await test_scenario_2_deduplication_and_rejection()
        await test_scenario_3_concurrent_case_take()
        await test_scenario_4_concurrent_refund_approval()
        print("\n" + "=" * 60)
        print("ALL 4 SCENARIOS PASSED SUCCESSFULLY (100% GREEN)")
        print("=" * 60)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
