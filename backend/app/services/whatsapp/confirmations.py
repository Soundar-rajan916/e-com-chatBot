"""Typed Confirmations for High-Impact Actions on WhatsApp (YES <code>)."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import PendingConfirmation, WhatsAppContact
from app.services.refunds import request_refund

logger = logging.getLogger(__name__)


async def create_pending_confirmation(
    db: AsyncSession,
    contact: WhatsAppContact,
    action_type: str,
    payload: dict[str, Any],
) -> PendingConfirmation:
    """Create a new typed confirmation record (expires after configured minutes)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.WHATSAPP_CONFIRMATION_EXPIRE_MINUTES)

    # 4-character uppercase alphanumeric code (e.g. 7X3K)
    code = "".join(secrets.choice("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(4))

    conf = PendingConfirmation(
        contact_id=contact.id,
        action_type=action_type,
        code=code,
        payload=payload,
        expires_at=expires_at,
        status="pending",
    )
    db.add(conf)
    await db.flush()
    return conf


async def verify_and_execute_confirmation(
    db: AsyncSession,
    contact: WhatsAppContact,
    code: str,
    chat_session_id: Any | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Verify typed confirmation code and execute the held action."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(PendingConfirmation)
        .where(
            PendingConfirmation.contact_id == contact.id,
            PendingConfirmation.code == code.strip().upper(),
            PendingConfirmation.status == "pending",
            PendingConfirmation.expires_at > now,
        )
        .order_by(PendingConfirmation.created_at.desc())
    )
    res = await db.execute(stmt)
    conf = res.scalar_one_or_none()

    if not conf:
        return (
            False,
            "Invalid or expired confirmation code. Please request the action again.",
            None,
        )

    action_type = conf.action_type
    payload = conf.payload or {}

    try:
        if action_type == "refund":
            if not contact.customer_id:
                return (False, "Please link your account first to process refunds.", None)

            order_number = payload.get("order_number")
            reason = payload.get("reason", "Customer requested via WhatsApp")
            if not order_number:
                return (False, "Missing order number in pending refund request.", None)

            result = await request_refund(
                session=db,
                customer_id=contact.customer_id,
                order_number=order_number,
                reason=reason,
                source="whatsapp",
                session_id=chat_session_id,
            )

            conf.status = "confirmed"
            await db.flush()

            status = result.get("status")
            if status == "processed":
                msg = (
                    f"✅ *Refund Processed Successfully*\n\n"
                    f"Order: *{order_number}*\n"
                    f"Refund Amount: *₹{result.get('amount')}*\n"
                    f"Reference: `{result.get('refund_id')}`\n\n"
                    f"The amount has been credited to your original payment method."
                )
                return (True, msg, result)
            elif status == "pending_approval":
                msg = (
                    f"⏳ *Refund Request Under Review*\n\n"
                    f"Order: *{order_number}*\n"
                    f"Amount: *₹{result.get('amount')}*\n\n"
                    f"Your request exceeds the automatic threshold and has been submitted to our support team. "
                    f"Ticket: `{result.get('escalation_id')}`. We will update you here once reviewed."
                )
                return (True, msg, result)
            else:
                err_msg = result.get("message") or "Refund request could not be processed."
                return (False, f"❌ *Refund Failed*: {err_msg}", result)

        elif action_type == "unlink":
            contact.customer_id = None
            conf.status = "confirmed"
            await db.flush()
            return (True, "✅ Your WhatsApp account has been successfully unlinked from your store account.", payload)

        else:
            conf.status = "confirmed"
            await db.flush()
            return (True, f"✅ Action *{action_type}* confirmed successfully.", payload)

    except Exception as exc:
        logger.error("Error executing confirmation %s: %s", conf.id, str(exc))
        return (False, f"Error processing confirmed action: {str(exc)}", None)
