import logging
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import (
    ChatSession,
    Escalation,
    EscalationEvent,
    Order,
    OrderStatusHistory,
    Refund,
)
from app.services.payments import MockPaymentGateway
from app.services.tools import check_refund_eligibility

logger = logging.getLogger("app.services.refunds")


async def request_refund(
    session: AsyncSession,
    customer_id: uuid.UUID,
    order_number: str,
    reason: str,
    source: str = "web",
    session_id: uuid.UUID | None = None,
    payment_gateway: MockPaymentGateway | None = None,
) -> dict[str, Any]:
    """
    Unified refund service used by both Chat tool and Storefront return endpoints.
    Enforces customer ownership, return window, row locks, threshold check,
    mock payment payout, and escalations.
    """
    settings = get_settings()
    auto_approve_limit = settings.REFUND_AUTO_APPROVE_LIMIT_INR
    gateway = payment_gateway or MockPaymentGateway()

    # 1. Eligibility check
    eligibility = await check_refund_eligibility(
        session=session,
        customer_id=customer_id,
        order_number=order_number,
        return_window_days=settings.RETURN_WINDOW_DAYS,
    )
    if not eligibility.get("eligible"):
        return {
            "success": False,
            "order_number": order_number,
            "reason": eligibility.get("reason"),
            "message": eligibility.get("message", "Order is not eligible for refund."),
            "requires_human": False,
        }

    # 2. Lock the order row
    order_stmt = (
        select(Order)
        .where(Order.order_number == order_number, Order.customer_id == customer_id)
        .with_for_update()
    )
    res = await session.execute(order_stmt)
    order = res.scalar_one_or_none()
    if order is None:
        return {
            "success": False,
            "order_number": order_number,
            "reason": "not_found",
            "message": "Order not found under your account.",
            "requires_human": False,
        }

    # 3. Check for existing active refund with row lock
    refund_stmt = (
        select(Refund)
        .where(
            Refund.order_id == order.id,
            Refund.status.in_(["processed", "pending_approval", "approved"]),
        )
        .with_for_update()
    )
    existing_refund = (await session.execute(refund_stmt)).scalar_one_or_none()
    if existing_refund is not None:
        return {
            "success": False,
            "order_number": order_number,
            "reason": "already_refunded",
            "refund_id": str(existing_refund.id),
            "refund_status": existing_refund.status,
            "message": f"A refund request already exists with status '{existing_refund.status}'.",
            "requires_human": existing_refund.status == "pending_approval",
        }

    # 4. Decision based on threshold
    amount = order.total_amount
    payout_info: dict[str, Any] | None = None

    if amount <= auto_approve_limit:
        refund_status = "processed"
        decided_by = "auto_rule_threshold"
        requires_human = False
        payout_info = await gateway.payout(customer_id, order.id, amount)
        order.payment_status = "refunded"
        # Record order status history
        hist = OrderStatusHistory(
            order_id=order.id,
            status="refunded",
            note=f"Refund auto-approved: ₹{amount:,.2f} ({source})",
        )
        session.add(hist)
    else:
        refund_status = "pending_approval"
        decided_by = None
        requires_human = True

    new_refund = Refund(
        order_id=order.id,
        customer_id=customer_id,
        amount=amount,
        status=refund_status,
        reason=reason,
        decided_by=decided_by,
    )
    session.add(new_refund)
    await session.flush()

    escalation_id: str | None = None
    if refund_status == "pending_approval":
        # Ensure we have a session_id to link escalation
        active_session_id = session_id
        if active_session_id is None:
            # Look up customer's latest chat session or create one
            s_stmt = (
                select(ChatSession.id)
                .where(ChatSession.customer_id == customer_id)
                .order_by(ChatSession.created_at.desc())
                .limit(1)
            )
            active_session_id = (await session.execute(s_stmt)).scalar_one_or_none()
            if active_session_id is None:
                new_cs = ChatSession(customer_id=customer_id, channel="web_store")
                session.add(new_cs)
                await session.flush()
                active_session_id = new_cs.id

        # Idempotently check if active escalation exists
        esc_stmt = (
            select(Escalation)
            .where(
                Escalation.session_id == active_session_id,
                Escalation.status.in_(["open", "in_progress"]),
            )
            .with_for_update()
        )
        existing_esc = (await session.execute(esc_stmt)).scalar_one_or_none()

        if existing_esc:
            existing_esc.refund_id = new_refund.id
            existing_esc.priority = "high"
            existing_esc.reason_type = "refund_pending_approval"
            escalation_id = str(existing_esc.id)
            event = EscalationEvent(
                escalation_id=existing_esc.id,
                actor_type="system",
                actor_id=None,
                action="priority_changed",
                detail={
                    "priority": "high",
                    "refund_id": str(new_refund.id),
                    "reason_type": "refund_pending_approval",
                    "source": source,
                },
            )
            session.add(event)
        else:
            new_esc = Escalation(
                session_id=active_session_id,
                customer_id=customer_id,
                reason=f"Refund approval required for {order_number} (₹{amount})",
                reason_type="refund_pending_approval",
                status="open",
                priority="high",
                refund_id=new_refund.id,
                version=1,
            )
            session.add(new_esc)
            await session.flush()
            escalation_id = str(new_esc.id)
            event = EscalationEvent(
                escalation_id=new_esc.id,
                actor_type="system",
                actor_id=None,
                action="created",
                detail={
                    "reason_type": "refund_pending_approval",
                    "order_number": order_number,
                    "amount": str(amount),
                    "refund_id": str(new_refund.id),
                    "source": source,
                },
            )
            session.add(event)

    await session.commit()
    await session.refresh(new_refund)

    return {
        "success": True,
        "refund_id": str(new_refund.id),
        "escalation_id": escalation_id,
        "order_number": order_number,
        "amount": amount,
        "status": refund_status,
        "auto_approved": refund_status == "processed",
        "requires_human": requires_human,
        "payout_info": payout_info,
        "message": (
            f"Refund for ₹{amount:,.2f} has been processed successfully."
            if refund_status == "processed"
            else f"Refund request for ₹{amount:,.2f} has been submitted for supervisor approval (exceeds auto-limit ₹{auto_approve_limit:,.2f})."
        ),
    }
