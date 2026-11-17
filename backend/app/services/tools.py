from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Escalation, EscalationEvent, Order, Refund
from app.services.payments import MockPaymentGateway


async def get_order_status(
    session: AsyncSession,
    customer_id: UUID,
    order_number: str,
) -> dict[str, Any]:
    """
    Retrieve order status strictly enforcing customer ownership.
    Returns identical 'not_found' payload whether order doesn't exist or belongs to someone else.
    """
    stmt = select(Order).where(Order.order_number == order_number).options(selectinload(Order.items))
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None or order.customer_id != customer_id:
        return {
            "status": "not_found",
            "order_number": order_number,
            "message": "Order not found under your account.",
        }

    refund_stmt = select(Refund).where(Refund.order_id == order.id)
    refund = (await session.execute(refund_stmt)).scalar_one_or_none()

    return {
        "status": "found",
        "order_number": order.order_number,
        "order_status": order.status,
        "refund_status": refund.status if refund else None,
        "refund_id": str(refund.id) if refund else None,
        "total_amount": str(order.total_amount),
        "placed_at": order.placed_at.isoformat() if order.placed_at else None,
        "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "tracking_note": order.tracking_note,
        "items": [
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
            }
            for item in order.items
        ],
    }


async def list_customer_orders(
    session: AsyncSession,
    customer_id: UUID,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Retrieve recent orders belonging strictly to the customer.
    Includes item summary and active refund status if present.
    """
    stmt = (
        select(Order)
        .where(Order.customer_id == customer_id)
        .options(selectinload(Order.items))
        .order_by(Order.placed_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    orders = list(result.scalars().all())

    if not orders:
        return {
            "status": "missing_order_number",
            "orders": [],
            "message": "Order number was not specified and you have no orders under your account.",
        }

    orders_payload = []
    for order in orders:
        refund_stmt = select(Refund).where(Refund.order_id == order.id)
        refund = (await session.execute(refund_stmt)).scalar_one_or_none()
        orders_payload.append(
            {
                "order_number": order.order_number,
                "order_status": order.status,
                "total_amount": str(order.total_amount),
                "placed_at": order.placed_at.strftime("%d %b %Y") if order.placed_at else None,
                "delivered_at": order.delivered_at.strftime("%d %b %Y") if order.delivered_at else None,
                "refund_status": refund.status if refund else None,
                "items": [item.product_name for item in order.items],
            }
        )

    return {
        "status": "found_orders",
        "orders_count": len(orders_payload),
        "orders": orders_payload,
    }


async def check_refund_eligibility(
    session: AsyncSession,
    customer_id: UUID,
    order_number: str,
    return_window_days: int = 7,
) -> dict[str, Any]:
    """
    Determine if an order is eligible for a refund according to deterministic business rules:
    1. Order belongs to customer.
    2. Order status is delivered.
    3. Delivered within RETURN_WINDOW_DAYS.
    4. No active refund exists.
    """
    stmt = select(Order).where(Order.order_number == order_number)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None or order.customer_id != customer_id:
        return {
            "eligible": False,
            "reason": "not_found",
            "order_number": order_number,
            "message": "Order not found under your account.",
        }

    if order.status != "delivered":
        return {
            "eligible": False,
            "reason": "not_delivered",
            "order_number": order_number,
            "order_status": order.status,
            "message": f"Order is '{order.status}'. Only delivered orders can be refunded.",
        }

    if not order.delivered_at:
        return {
            "eligible": False,
            "reason": "missing_delivery_date",
            "order_number": order_number,
            "message": "Delivery timestamp missing for order.",
        }

    now_utc = datetime.now(UTC)
    delivered_utc = (
        order.delivered_at.replace(tzinfo=UTC)
        if order.delivered_at.tzinfo is None
        else order.delivered_at.astimezone(UTC)
    )
    days_elapsed = (now_utc - delivered_utc).days

    if days_elapsed > return_window_days:
        return {
            "eligible": False,
            "reason": "return_window_expired",
            "order_number": order_number,
            "days_elapsed": days_elapsed,
            "window_days": return_window_days,
            "message": f"Return window of {return_window_days} days expired ({days_elapsed} days elapsed).",
        }

    # Check for active refund
    refund_stmt = select(Refund).where(
        Refund.order_id == order.id,
        Refund.status.in_(["processed", "pending_approval", "approved"]),
    )
    active_refund = (await session.execute(refund_stmt)).scalar_one_or_none()
    if active_refund is not None:
        return {
            "eligible": False,
            "reason": "already_refunded",
            "order_number": order_number,
            "refund_id": str(active_refund.id),
            "refund_status": active_refund.status,
            "message": f"An active refund already exists with status '{active_refund.status}'.",
        }

    return {
        "eligible": True,
        "order_id": str(order.id),
        "order_number": order.order_number,
        "amount": str(order.total_amount),
        "total_amount": order.total_amount,
    }


async def create_refund(
    session: AsyncSession,
    customer_id: UUID,
    order_number: str,
    refund_reason: str | None,
    auto_approve_limit: Decimal,
    session_id: UUID | None = None,
    payment_gateway: MockPaymentGateway | None = None,
) -> dict[str, Any]:
    """
    Execute refund creation using the unified request_refund service.
    """
    from app.services.refunds import request_refund

    reason = refund_reason or "Customer requested refund"
    result = await request_refund(
        session=session,
        customer_id=customer_id,
        order_number=order_number,
        reason=reason,
        source="chat_tool",
        session_id=session_id,
        payment_gateway=payment_gateway,
    )
    # Format amount as string for backward-compatibility with existing chat tool schemas
    if "amount" in result and isinstance(result["amount"], Decimal):
        result["amount"] = str(result["amount"])
    return result
