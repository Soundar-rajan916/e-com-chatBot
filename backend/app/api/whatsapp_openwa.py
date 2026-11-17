"""OpenWA Webhook Ingress Endpoint with HMAC Signature Verification and Immediate 200 ACK."""

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import WhatsAppInboundEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp/openwa", tags=["whatsapp-openwa"])


def verify_openwa_signature(raw_body: bytes, signature_header: str | None, secret: str | None) -> bool:
    """Verify X-OpenWA-Signature HMAC-SHA256 over raw request bytes.

    OpenWA format: 'sha256=<hex_digest>'
    """
    if not secret:
        # If no secret configured in environment, allow in dev/test
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    received_sig = signature_header[7:].strip()
    expected_sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    return hmac.compare_digest(received_sig, expected_sig)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def openwa_webhook_ingress(
    request: Request,
    x_openwa_signature: str | None = Header(None, alias="X-OpenWA-Signature"),
    x_openwa_event: str | None = Header(None, alias="X-OpenWA-Event"),
    x_openwa_idempotency_key: str | None = Header(None, alias="X-OpenWA-Idempotency-Key"),
    x_openwa_delivery_id: str | None = Header(None, alias="X-OpenWA-Delivery-Id"),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Ingest OpenWA webhooks, verify HMAC signature, deduplicate, and record event.

    Responds with HTTP 200 immediately to avoid OpenWA delivery timeouts.
    """
    settings = get_settings()

    # 1. Read raw unparsed body for strict signature verification
    raw_body = await request.body()

    if not verify_openwa_signature(raw_body, x_openwa_signature, settings.OPENWA_WEBHOOK_SECRET):
        logger.warning("Rejected OpenWA webhook: invalid or missing HMAC signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # 2. Parse JSON payload
    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as exc:
        logger.error("Failed to parse OpenWA webhook JSON: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload",
        )

    # 3. Extract metadata
    event_type = payload.get("event") or x_openwa_event or "unknown"
    session_id = payload.get("sessionId") or settings.OPENWA_SESSION_ID
    idempotency_key = payload.get("idempotencyKey") or x_openwa_idempotency_key
    delivery_id = payload.get("deliveryId") or x_openwa_delivery_id

    # Extract sender chat id if present
    data = payload.get("data") or {}
    sender_chat_id = data.get("from") or data.get("chatId")
    message_id = data.get("id")

    # 4. Ingress deduplication (canonicalized by message ID to prevent multi-webhook duplicates)
    canonical_idempotency_key = (
        f"wa_msg_{session_id}_{message_id}" if message_id else (idempotency_key or delivery_id)
    )

    conditions = []
    if canonical_idempotency_key:
        conditions.append(WhatsAppInboundEvent.idempotency_key == canonical_idempotency_key)
    if idempotency_key and idempotency_key != canonical_idempotency_key:
        conditions.append(WhatsAppInboundEvent.idempotency_key == idempotency_key)
    if delivery_id:
        conditions.append(WhatsAppInboundEvent.delivery_id == delivery_id)

    if conditions:
        from sqlalchemy import or_

        stmt = select(WhatsAppInboundEvent).where(or_(*conditions))
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            logger.info(
                "Ignoring duplicate webhook delivery: key=%s, deliveryId=%s",
                canonical_idempotency_key,
                delivery_id,
            )
            return {"status": "duplicate", "id": str(existing.id)}

    # 5. Record pending inbound event for asynchronous processing
    inbound_event = WhatsAppInboundEvent(
        delivery_id=delivery_id,
        idempotency_key=canonical_idempotency_key or idempotency_key,
        event_type=event_type,
        session_id=session_id,
        sender_chat_id=sender_chat_id,
        raw_payload=payload,
        status="pending",
    )
    db.add(inbound_event)
    await db.commit()
    await db.refresh(inbound_event)

    return {
        "status": "accepted",
        "id": str(inbound_event.id),
        "event": event_type,
    }
