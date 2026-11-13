from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.models import (
    Agent,
    ChatMessage,
    ChatSession,
    Customer,
    Escalation,
    Order,
    Refund,
)


@pytest.mark.asyncio
async def test_admin_auth_and_lockout(client: AsyncClient, db_session: AsyncSession):
    # Create test agent
    agent = Agent(
        email="test_agent@example.com",
        name="Test Agent",
        password_hash=hash_password("ValidPassword123!"),
        role="agent",
        is_active=True,
    )
    db_session.add(agent)
    await db_session.commit()

    # 1. CSRF rejection without X-Requested-With
    res = await client.post(
        "/admin/auth/login",
        json={"email": "test_agent@example.com", "password": "ValidPassword123!"},
    )
    assert res.status_code == 403

    headers = {"X-Requested-With": "admin-console"}

    # 2. Failed password attempts
    for _ in range(4):
        res = await client.post(
            "/admin/auth/login",
            json={"email": "test_agent@example.com", "password": "WrongPassword"},
            headers=headers,
        )
        assert res.status_code == 401

    # 5th failed attempt locks out account
    res = await client.post(
        "/admin/auth/login",
        json={"email": "test_agent@example.com", "password": "WrongPassword"},
        headers=headers,
    )
    assert res.status_code == 401

    # Now even valid password is rejected due to lockout
    res = await client.post(
        "/admin/auth/login",
        json={"email": "test_agent@example.com", "password": "ValidPassword123!"},
        headers=headers,
    )
    assert res.status_code == 401

    # Reset lockout in DB to test successful login
    agent.failed_attempts = 0
    agent.locked_until = None
    await db_session.commit()

    res = await client.post(
        "/admin/auth/login",
        json={"email": "test_agent@example.com", "password": "ValidPassword123!"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "test_agent@example.com"
    assert "admin_session" in res.cookies

    # 3. GET /admin/auth/me with session cookie
    me_res = await client.get("/admin/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Test Agent"

    # 4. Logout
    logout_res = await client.post("/admin/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # After logout, me is 401
    me_after = await client.get("/admin/auth/me")
    assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_admin_escalation_workflow(client: AsyncClient, db_session: AsyncSession):
    # Setup agent
    agent = Agent(
        email="workflow_agent@example.com",
        name="Workflow Agent",
        password_hash=hash_password("AgentPass123!"),
        role="admin",
        is_active=True,
    )
    db_session.add(agent)

    # Setup customer, session, order, refund, escalation
    customer = Customer(
        name="Ananya Sharma",
        phone="+919876543210",
        preferred_language="en",
    )
    db_session.add(customer)
    await db_session.flush()

    chat_session = ChatSession(
        customer_id=customer.id,
        channel="web",
    )
    db_session.add(chat_session)
    await db_session.flush()

    order = Order(
        customer_id=customer.id,
        order_number="ORD-TEST-99",
        total_amount=Decimal("2500.00"),
        status="delivered",
        placed_at=datetime.now(UTC),
    )
    db_session.add(order)
    await db_session.flush()

    from app.models import OrderItem

    item = OrderItem(
        order_id=order.id,
        product_name="Silk Saree",
        quantity=1,
        unit_price=Decimal("2500.00"),
    )
    db_session.add(item)

    refund = Refund(
        order_id=order.id,
        customer_id=customer.id,
        amount=Decimal("2500.00"),
        reason="Defective item received",
        status="pending_approval",
    )
    db_session.add(refund)
    await db_session.flush()

    esc = Escalation(
        session_id=chat_session.id,
        customer_id=customer.id,
        refund_id=refund.id,
        reason="High-value refund pending approval",
        reason_type="refund_pending_approval",
        priority="high",
        status="open",
        version=1,
    )
    db_session.add(esc)

    # Add customer message
    user_msg = ChatMessage(
        session_id=chat_session.id,
        role="user",
        content="I want a refund for my order ORD-TEST-99",
        input_mode="text",
    )
    db_session.add(user_msg)
    await db_session.commit()

    headers = {"X-Requested-With": "admin-console"}

    # Login agent
    login_res = await client.post(
        "/admin/auth/login",
        json={"email": "workflow_agent@example.com", "password": "AgentPass123!"},
        headers=headers,
    )
    assert login_res.status_code == 200

    # 1. List escalations (verify phone is masked)
    list_res = await client.get("/admin/escalations")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    found_esc = next(item for item in list_data["items"] if item["id"] == str(esc.id))
    assert found_esc["customer_name"] == "Ananya Sharma"
    assert found_esc["customer_phone_masked"] == "+9198*** **210"
    assert found_esc["priority"] == "high"
    assert found_esc["reason_type"] == "refund_pending_approval"

    # 2. Stats
    stats_res = await client.get("/admin/escalations/stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert stats_data["open_count"] >= 1

    # 3. Get Detail
    detail_res = await client.get(f"/admin/escalations/{esc.id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["customer"]["phone"] == "+919876543210"  # unmasked in detail
    assert len(detail["recent_orders"]) == 1
    assert detail["refund"]["amount"] == "2500.00"
    assert len(detail["messages"]) == 1

    # 4. Concurrency: Assign with wrong version -> 409
    assign_conflict = await client.post(
        f"/admin/escalations/{esc.id}/assign",
        json={"version": 999},
        headers=headers,
    )
    assert assign_conflict.status_code == 409

    # Assign with correct version (1)
    assign_ok = await client.post(
        f"/admin/escalations/{esc.id}/assign",
        json={"version": 1},
        headers=headers,
    )
    assert assign_ok.status_code == 200
    assert assign_ok.json()["version"] == 2
    assert assign_ok.json()["status"] == "in_progress"

    # 5. Add note
    note_res = await client.post(
        f"/admin/escalations/{esc.id}/notes",
        json={"body": "Checked order logs, defect confirmed by customer photo."},
        headers=headers,
    )
    assert note_res.status_code == 200

    # 6. Reply to customer
    reply_res = await client.post(
        f"/admin/escalations/{esc.id}/reply",
        json={"message": "Hello Ananya, I am looking into your refund request now."},
        headers=headers,
    )
    assert reply_res.status_code == 200

    # Customer polls messages via public endpoint
    poll_res = await client.get(
        f"/sessions/{chat_session.id}/messages",
        params={"customer_id": str(customer.id)},
    )
    assert poll_res.status_code == 200
    poll_msgs = poll_res.json()
    assert len(poll_msgs) == 2
    assert poll_msgs[-1]["role"] == "agent"
    assert "Hello Ananya" in poll_msgs[-1]["content"]

    # 7. Try to resolve before refund decision -> 409 Conflict
    resolve_block = await client.post(
        f"/admin/escalations/{esc.id}/resolve",
        json={"resolution_note": "Case closed prematurely.", "version": 2},
        headers=headers,
    )
    assert resolve_block.status_code == 409

    # 8. Approve Refund
    approve_res = await client.post(
        f"/admin/escalations/{esc.id}/refund/approve",
        json={"version": 2},
        headers=headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["version"] == 3

    # Check notification in chat
    poll_res2 = await client.get(
        f"/sessions/{chat_session.id}/messages",
        params={"customer_id": str(customer.id)},
    )
    assert len(poll_res2.json()) == 3
    assert "approved and processed" in poll_res2.json()[-1]["content"]

    # 9. Now resolve escalation successfully
    resolve_ok = await client.post(
        f"/admin/escalations/{esc.id}/resolve",
        json={"resolution_note": "Refund processed and customer notified.", "version": 3},
        headers=headers,
    )
    assert resolve_ok.status_code == 200
    assert resolve_ok.json()["version"] == 4

    # 10. Reopen escalation
    reopen_ok = await client.post(
        f"/admin/escalations/{esc.id}/reopen",
        json={"version": 4},
        headers=headers,
    )
    assert reopen_ok.status_code == 200
    assert reopen_ok.json()["version"] == 5
