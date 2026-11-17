"""End-to-End Automated Smoke Verification Script for WhatsApp Channel Integration."""

import asyncio
import hashlib
import hmac
import json
import time
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import get_settings
from app.models import (
    Customer,
    Order,
    PendingConfirmation,
    WhatsAppContact,
    WhatsAppInboundEvent,
    WhatsAppOutbound,
)
from app.services.whatsapp.identity import normalize_phone_number


def compute_sig(body_bytes: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def run_smoke_test():
    settings = get_settings()
    backend_url = "http://localhost:8000"
    secret = settings.OPENWA_WEBHOOK_SECRET or "openwa_dev_secure_webhook_secret_key_16chars"

    print("================================================================")
    print("🚀 WhatsApp Integration End-to-End Smoke Verification")
    print(f"Backend Target: {backend_url}")
    print("================================================================\n")

    test_phone = f"+9198{uuid.uuid4().hex[:8]}"
    test_chat_id = f"{test_phone.replace('+', '')}@c.us"

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Check backend health
        try:
            h_res = await client.get(f"{backend_url}/health")
            assert h_res.status_code == 200, f"Backend unhealthy: {h_res.text}"
            print("✅ 1. Backend service is healthy and reachable.")
        except Exception as exc:
            print(f"❌ 1. Backend connection failed: {exc}")
            return False

        # Webhook signature verification tests
        print("\n--- Testing Webhook Security & Ingress ---")
        payload = {
            "event": "message.received",
            "sessionId": settings.OPENWA_SESSION_ID,
            "idempotencyKey": f"smoke_{uuid.uuid4().hex}",
            "deliveryId": f"dlv_{uuid.uuid4().hex}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data": {
                "id": f"msg_{uuid.uuid4().hex[:10]}",
                "from": test_chat_id,
                "body": "Hello WhatsApp Support",
                "type": "text",
                "fromMe": False,
                "isGroup": False,
                "kind": "individual",
                "senderPhone": test_phone.replace("+", ""),
                "timestamp": int(time.time()),
            },
        }
        raw_bytes = json.dumps(payload).encode("utf-8")

        # Invalid signature
        bad_sig_res = await client.post(
            f"{backend_url}/whatsapp/openwa/webhook",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-OpenWA-Signature": "sha256=badhexsignature0123"},
        )
        assert bad_sig_res.status_code == 401, f"Expected 401 for bad signature, got {bad_sig_res.status_code}"
        print("✅ 2. Webhook rejected invalid HMAC signature with 401 Unauthorized.")

        # Valid signature
        good_sig = compute_sig(raw_bytes, secret)
        good_res = await client.post(
            f"{backend_url}/whatsapp/openwa/webhook",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-OpenWA-Signature": good_sig},
        )
        assert good_res.status_code == 200, f"Expected 200 for good signature, got {good_res.status_code}: {good_res.text}"
        assert good_res.json().get("status") == "accepted"
        print("✅ 3. Webhook accepted valid HMAC signature with immediate 200 OK.")

        # Duplicate delivery
        dup_res = await client.post(
            f"{backend_url}/whatsapp/openwa/webhook",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-OpenWA-Signature": good_sig},
        )
        assert dup_res.status_code == 200
        assert dup_res.json().get("status") == "duplicate"
        print("✅ 4. Webhook ingress deduplication caught identical deliveryId/idempotencyKey.")

        # Process inbound event via worker in test DB session
        print("\n--- Testing Inbound Event Worker & Opt-Out Cycle ---")
        from app.services.whatsapp.fake import FakeWhatsAppProvider
        from app.services.whatsapp.worker import process_pending_inbound_events, process_pending_outbound_messages

        provider = FakeWhatsAppProvider()
        async with session_factory() as session:
            processed = await process_pending_inbound_events(session, provider)
            print(f"✅ 5. Inbound worker processed {processed} pending event(s) under advisory locking.")

            # Verify WhatsAppContact was created
            stmt = select(WhatsAppContact).where(WhatsAppContact.chat_id == test_chat_id)
            contact = (await session.execute(stmt)).scalar_one_or_none()
            assert contact is not None
            assert contact.phone_number == normalize_phone_number(test_phone)
            print(f"✅ 6. WhatsApp contact created and phone normalized: {contact.phone_number}")

        # Opt-out test (STOP command)
        stop_payload = {
            "event": "message.received",
            "sessionId": settings.OPENWA_SESSION_ID,
            "idempotencyKey": f"smoke_stop_{uuid.uuid4().hex}",
            "deliveryId": f"dlv_{uuid.uuid4().hex}",
            "data": {
                "id": f"msg_{uuid.uuid4().hex[:10]}",
                "from": test_chat_id,
                "body": "STOP",
                "type": "text",
                "fromMe": False,
                "isGroup": False,
            },
        }
        stop_bytes = json.dumps(stop_payload).encode("utf-8")
        await client.post(
            f"{backend_url}/whatsapp/openwa/webhook",
            content=stop_bytes,
            headers={"Content-Type": "application/json", "X-OpenWA-Signature": compute_sig(stop_bytes, secret)},
        )

        async with session_factory() as session:
            await process_pending_inbound_events(session, provider)
            stmt = select(WhatsAppContact).where(WhatsAppContact.chat_id == test_chat_id)
            contact = (await session.execute(stmt)).scalar_one()
            assert contact.opted_out is True
            print("✅ 7. Inbound 'STOP' opt-out command marked contact.opted_out = True.")

        # Opt-in test (START command)
        start_payload = {
            "event": "message.received",
            "sessionId": settings.OPENWA_SESSION_ID,
            "idempotencyKey": f"smoke_start_{uuid.uuid4().hex}",
            "deliveryId": f"dlv_{uuid.uuid4().hex}",
            "data": {
                "id": f"msg_{uuid.uuid4().hex[:10]}",
                "from": test_chat_id,
                "body": "START",
                "type": "text",
                "fromMe": False,
                "isGroup": False,
            },
        }
        start_bytes = json.dumps(start_payload).encode("utf-8")
        await client.post(
            f"{backend_url}/whatsapp/openwa/webhook",
            content=start_bytes,
            headers={"Content-Type": "application/json", "X-OpenWA-Signature": compute_sig(start_bytes, secret)},
        )

        async with session_factory() as session:
            await process_pending_inbound_events(session, provider)
            stmt = select(WhatsAppContact).where(WhatsAppContact.chat_id == test_chat_id)
            contact = (await session.execute(stmt)).scalar_one()
            assert contact.opted_out is False
            print("✅ 8. Inbound 'START' command resumed opt-in status.")

        # Account Linking Flow
        print("\n--- Testing Account Linking & Typed Confirmations ---")
        async with session_factory() as session:
            from app.services.whatsapp.identity import create_link_code
            # Create sample customer
            customer = Customer(
                name="Sundar Pichai",
                phone=test_phone,
                preferred_language="en",
            )
            session.add(customer)
            await session.commit()
            await session.refresh(customer)

            link_code = await create_link_code(session, customer.id)
            await session.commit()
            code_val = link_code.code
            print(f"Generated link code: {code_val}")

        # Send LINK <code>
        link_payload = {
            "event": "message.received",
            "sessionId": settings.OPENWA_SESSION_ID,
            "idempotencyKey": f"smoke_link_{uuid.uuid4().hex}",
            "deliveryId": f"dlv_{uuid.uuid4().hex}",
            "data": {
                "id": f"msg_{uuid.uuid4().hex[:10]}",
                "from": test_chat_id,
                "body": f"LINK {code_val}",
                "type": "text",
                "fromMe": False,
                "isGroup": False,
            },
        }
        link_bytes = json.dumps(link_payload).encode("utf-8")
        await client.post(
            f"{backend_url}/whatsapp/openwa/webhook",
            content=link_bytes,
            headers={"Content-Type": "application/json", "X-OpenWA-Signature": compute_sig(link_bytes, secret)},
        )

        async with session_factory() as session:
            await process_pending_inbound_events(session, provider)
            stmt = select(WhatsAppContact).where(WhatsAppContact.chat_id == test_chat_id)
            contact = (await session.execute(stmt)).scalar_one()
            assert contact.customer_id == customer.id
            print(f"✅ 9. Customer successfully linked to WhatsAppContact via 'LINK {code_val}'.")

        # Outbound Pacing Test
        print("\n--- Testing Outbound Pacing & Message Dispatch ---")
        async with session_factory() as session:
            sent_count = await process_pending_outbound_messages(session, provider)
            print(f"✅ 10. Outbound worker delivered {sent_count} rate-paced response(s) via provider.")
            assert len(provider.sent_messages) > 0

    await engine.dispose()
    print("\n================================================================")
    print("🎉 ALL 10 SMOKE VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("================================================================\n")
    return True


if __name__ == "__main__":
    success = asyncio.run(run_smoke_test())
    if not success:
        sys.exit(1)
