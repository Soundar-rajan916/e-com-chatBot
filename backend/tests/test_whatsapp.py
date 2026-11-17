"""Tests for WhatsApp OpenWA Integration (Channel, Webhook, Identity, Pacing, Security)."""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.main import create_app
from app.models import (
    Customer,
    Order,
    PendingConfirmation,
    WhatsAppContact,
    WhatsAppGatewayState,
    WhatsAppInboundEvent,
    WhatsAppLinkCode,
    WhatsAppOutbound,
)
from app.services.whatsapp.confirmations import (
    create_pending_confirmation,
    verify_and_execute_confirmation,
)
from app.services.whatsapp.fake import FakeWhatsAppProvider
from app.services.whatsapp.formatter import chunk_whatsapp_message, format_for_whatsapp
from app.services.whatsapp.identity import (
    chat_id_to_phone,
    create_link_code,
    get_or_create_contact,
    mask_phone_number,
    normalize_phone_number,
    parse_inbound_command,
    phone_to_chat_id,
    redeem_link_code,
    unlink_contact,
)
from app.services.whatsapp.worker import (
    process_pending_inbound_events,
    process_pending_outbound_messages,
    queue_outbound_message,
)


def compute_signature(payload_bytes: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# =========================================================================
# 1. Identity, Phone Normalization, and Command Parsing Tests
# =========================================================================


def test_phone_normalization_and_chat_id():
    assert normalize_phone_number("+91 98765 43210") == "+919876543210"
    assert normalize_phone_number("919876543210") == "+919876543210"
    assert normalize_phone_number("") == ""

    assert chat_id_to_phone("919876543210@c.us") == "+919876543210"
    assert chat_id_to_phone("919876543210@lid") == "+919876543210"
    assert phone_to_chat_id("+919876543210") == "919876543210@c.us"

    assert mask_phone_number("+919876543210") == "+91***210"
    assert mask_phone_number("12345") == "***"


def test_command_parsing():
    assert parse_inbound_command("STOP") == ("STOP", None)
    assert parse_inbound_command("stopall") == ("STOP", None)
    assert parse_inbound_command("unsubscribe") == ("STOP", None)
    assert parse_inbound_command("START") == ("START", None)
    assert parse_inbound_command("UNLINK") == ("UNLINK", None)
    assert parse_inbound_command("LINK 123456") == ("LINK", "123456")
    assert parse_inbound_command("connect ABCD") == ("LINK", "ABCD")
    assert parse_inbound_command("YES 7X3K") == ("YES", "7X3K")
    assert parse_inbound_command("confirm REF12") == ("YES", "REF12")
    assert parse_inbound_command("cancel") == ("STOP", None)
    assert parse_inbound_command("where is my order?") == ("MESSAGE", "where is my order?")


# =========================================================================
# 2. Markdown Formatter and Message Chunking Tests
# =========================================================================


def test_formatter_markdown_to_whatsapp():
    raw = (
        "### Order Details\n"
        "Your order **ORD-10001** is confirmed.\n"
        "- Item 1: Cotton Saree\n"
        "- Item 2: Silk Kurti\n"
        "Discount was ~~₹500~~.\n"
        "Check [Storefront Link](https://example.com/orders/10001) for tracking."
    )
    formatted = format_for_whatsapp(raw)

    assert "*Order Details*" in formatted
    assert "*ORD-10001*" in formatted
    assert "• Item 1: Cotton Saree" in formatted
    assert "~₹500~" in formatted
    assert "Storefront Link: https://example.com/orders/10001" in formatted


def test_chunk_whatsapp_message():
    short_text = "Hello customer! Your order has shipped."
    chunks = chunk_whatsapp_message(short_text, max_chars=100)
    assert chunks == [short_text]

    long_paragraph = "A" * 80 + "\n\n" + "B" * 80
    chunks = chunk_whatsapp_message(long_paragraph, max_chars=100)
    assert len(chunks) == 2
    assert chunks[0] == "A" * 80
    assert chunks[1] == "B" * 80


# =========================================================================
# 3. Webhook Ingress and HMAC Signature Verification Tests
# =========================================================================


@pytest.mark.asyncio
async def test_webhook_hmac_signature_verification(db_session):
    app = create_app()
    secret = "test_webhook_secret_key_16chars_min"

    # Temporary override secret in settings
    settings = get_settings()
    orig_secret = settings.OPENWA_WEBHOOK_SECRET
    settings.OPENWA_WEBHOOK_SECRET = secret

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "event": "message.received",
                "sessionId": "ecom-store",
                "idempotencyKey": f"key_{uuid.uuid4().hex}",
                "deliveryId": f"dlv_{uuid.uuid4().hex}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "id": f"msg_{uuid.uuid4().hex[:8]}",
                    "from": "919876543210@c.us",
                    "body": "Hello support",
                    "type": "text",
                    "fromMe": False,
                },
            }
            body_bytes = json.dumps(payload).encode("utf-8")

            # 1. Missing signature -> 401
            res = await ac.post("/whatsapp/openwa/webhook", content=body_bytes)
            assert res.status_code == 401

            # 2. Invalid signature -> 401
            res = await ac.post(
                "/whatsapp/openwa/webhook",
                content=body_bytes,
                headers={"X-OpenWA-Signature": "sha256=invalidhex0123456789"},
            )
            assert res.status_code == 401

            # 3. Valid signature -> 200 accepted
            valid_sig = compute_signature(body_bytes, secret)
            res = await ac.post(
                "/whatsapp/openwa/webhook",
                content=body_bytes,
                headers={"X-OpenWA-Signature": valid_sig},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "accepted"

            # 4. Ingress deduplication -> duplicate returns 200 status="duplicate"
            res_dup = await ac.post(
                "/whatsapp/openwa/webhook",
                content=body_bytes,
                headers={"X-OpenWA-Signature": valid_sig},
            )
            assert res_dup.status_code == 200
            assert res_dup.json()["status"] == "duplicate"
    finally:
        settings.OPENWA_WEBHOOK_SECRET = orig_secret


# =========================================================================
# 4. Identity Linking and Confirmation Flow Tests
# =========================================================================


@pytest.mark.asyncio
async def test_identity_linking_and_unlinking(db_session):
    # Create customer
    customer = Customer(
        name="Ramesh Kumar",
        phone="+919876543210",
        preferred_language="en",
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)

    # 1. Create link code
    link_code = await create_link_code(db_session, customer.id)
    await db_session.commit()
    assert len(link_code.code) == 6

    # 2. Contact with different phone attempts redemption
    contact = await get_or_create_contact(db_session, chat_id="919111222333@c.us")
    assert contact.customer_id is None

    # Redeem with correct code
    success, msg, linked_cust = await redeem_link_code(db_session, contact, link_code.code)
    assert success is True
    assert linked_cust.id == customer.id
    assert contact.customer_id == customer.id

    # Trying to reuse the same code fails
    success_reuse, err_msg, _ = await redeem_link_code(db_session, contact, link_code.code)
    assert success_reuse is False
    assert "Invalid or expired" in err_msg

    # 3. Unlink
    unlinked, unlink_msg = await unlink_contact(db_session, contact)
    assert unlinked is True
    assert contact.customer_id is None


@pytest.mark.asyncio
async def test_auto_linking_by_matching_phone_number(db_session):
    # Customer registers on store with phone +919876543210
    customer = Customer(
        name="Auto Linked User",
        phone="+919876543210",
        preferred_language="ta",
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)

    # When this customer messages WhatsApp from their registered phone number
    contact = await get_or_create_contact(db_session, chat_id="919876543210@c.us")
    # They should be automatically recognized and linked!
    assert contact.customer_id == customer.id


@pytest.mark.asyncio
async def test_typed_refund_confirmation_workflow(db_session):
    # Create customer with order
    customer = Customer(
        name="Suresh Raina",
        phone="+919876543211",
        preferred_language="en",
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)

    order = Order(
        customer_id=customer.id,
        order_number="ORD-77701",
        status="delivered",
        total_amount=1200.0,
        placed_at=datetime.now(timezone.utc) - timedelta(days=5),
        delivered_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(order)
    await db_session.commit()

    contact = await get_or_create_contact(db_session, chat_id="919876543211@c.us")
    contact.customer_id = customer.id
    await db_session.commit()

    # Create pending confirmation for refund
    conf = await create_pending_confirmation(
        db=db_session,
        contact=contact,
        action_type="refund",
        payload={"order_number": "ORD-77701", "reason": "Size too small"},
    )
    await db_session.commit()
    assert conf.status == "pending"

    # Verify and execute typed confirmation with code
    success, reply, res_data = await verify_and_execute_confirmation(
        db=db_session,
        contact=contact,
        code=conf.code,
    )
    await db_session.commit()

    assert success is True
    assert "Refund Processed" in reply or "Refund Request" in reply
    assert conf.status == "confirmed"


# =========================================================================
# 5. Worker Inbound Processing and Opt-Out Tests
# =========================================================================


@pytest.mark.asyncio
async def test_worker_opt_out_stop_and_start(db_session):
    provider = FakeWhatsAppProvider()
    chat_id = "919876543299@c.us"

    # 1. Customer sends STOP
    stop_event = WhatsAppInboundEvent(
        event_type="message.received",
        session_id="ecom-store",
        delivery_id=f"dlv_{uuid.uuid4().hex}",
        raw_payload={
            "data": {
                "id": "msg_stop",
                "from": chat_id,
                "body": "STOP",
                "type": "text",
                "fromMe": False,
            }
        },
        status="pending",
    )
    db_session.add(stop_event)
    await db_session.commit()

    await process_pending_inbound_events(db_session, provider)

    stmt = select(WhatsAppContact).where(WhatsAppContact.chat_id == chat_id)
    contact = (await db_session.execute(stmt)).scalar_one()
    assert contact.opted_out is True

    # Check that STOP acknowledgment was queued
    out_stmt = select(WhatsAppOutbound).where(WhatsAppOutbound.contact_id == contact.id)
    out_items = list((await db_session.execute(out_stmt)).scalars().all())
    assert any("unsubscribed" in item.body.lower() for item in out_items)

    # 2. Customer sends normal message while opted out -> ignored
    msg_event = WhatsAppInboundEvent(
        event_type="message.received",
        session_id="ecom-store",
        delivery_id=f"dlv_{uuid.uuid4().hex}",
        raw_payload={
            "data": {
                "id": "msg_while_opted_out",
                "from": chat_id,
                "body": "Hi are you there?",
                "type": "text",
                "fromMe": False,
            }
        },
        status="pending",
    )
    db_session.add(msg_event)
    await db_session.commit()

    await process_pending_inbound_events(db_session, provider)
    await db_session.refresh(msg_event)
    assert msg_event.status == "ignored"

    # 3. Customer sends START -> opted back in
    start_event = WhatsAppInboundEvent(
        event_type="message.received",
        session_id="ecom-store",
        delivery_id=f"dlv_{uuid.uuid4().hex}",
        raw_payload={
            "data": {
                "id": "msg_start",
                "from": chat_id,
                "body": "START",
                "type": "text",
                "fromMe": False,
            }
        },
        status="pending",
    )
    db_session.add(start_event)
    await db_session.commit()

    await process_pending_inbound_events(db_session, provider)
    await db_session.refresh(contact)
    assert contact.opted_out is False


# =========================================================================
# 6. Outbound Pacing and 72-Hour Reply-Only Rule Tests
# =========================================================================


@pytest.mark.asyncio
async def test_outbound_reply_only_guard(db_session):
    provider = FakeWhatsAppProvider()
    settings = get_settings()
    settings.WHATSAPP_OUTBOUND_MIN_DELAY_MS = 10  # Faster for tests

    # Contact with expired last_seen_at (> 72 hours ago)
    expired_contact = WhatsAppContact(
        phone_number="+919876543288",
        chat_id="919876543288@c.us",
        last_seen_at=datetime.now(timezone.utc) - timedelta(hours=75),
    )
    db_session.add(expired_contact)
    await db_session.commit()
    await db_session.refresh(expired_contact)

    # Queue an outbound message
    outbound = WhatsAppOutbound(
        contact_id=expired_contact.id,
        chat_id=expired_contact.chat_id,
        body="Proactive promotional update",
        idempotency_key=f"out_{uuid.uuid4().hex}",
        status="pending",
    )
    db_session.add(outbound)
    await db_session.commit()

    # Outbound worker should refuse to send because 72h window expired
    sent = await process_pending_outbound_messages(db_session, provider)
    await db_session.refresh(outbound)

    assert sent == 0
    assert outbound.status == "failed"
    assert "72h reply window expired" in outbound.error_message
    assert len(provider.sent_messages) == 0
