import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_agent, verify_csrf
from app.db import get_session
from app.models import (
    Agent,
    Customer,
    Escalation,
    EscalationEvent,
    Order,
    OrderStatusHistory,
    Product,
    Refund,
)
from app.schemas import (
    AdminOrderListItem,
    AdminRefundListItem,
    AdminRefundRejectRequest,
    CancelOrderRequest,
)
from app.services.payments import MockPaymentGateway

logger = logging.getLogger("app.api.admin_operations")
router = APIRouter(prefix="/admin", tags=["admin-operations"])


def build_admin_order_item(order: Order) -> AdminOrderListItem:
    customer_name = order.customer.name if order.customer else (order.shipping_name or "Guest")
    customer_phone = order.customer.phone if order.customer else (order.shipping_phone or "")
    customer_email = order.customer.email if order.customer else ""

    items_list = list(order.items or [])
    items_count = sum(item.quantity for item in items_list)
    items_summary = (
        ", ".join([f"{item.quantity}x {item.product_name}" for item in items_list])
        if items_list
        else "No items"
    )

    return AdminOrderListItem(
        id=order.id,
        order_number=order.order_number,
        customer_id=order.customer_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        status=order.status,
        total_amount=order.total_amount,
        total_amount_inr=order.total_amount,
        placed_at=order.placed_at,
        delivered_at=order.delivered_at,
        items_count=items_count,
        items_summary=items_summary,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
    )


def build_admin_refund_item(refund: Refund) -> AdminRefundListItem:
    order_num = refund.order.order_number if refund.order else "Unknown"
    cust_name = refund.customer.name if refund.customer else "Unknown"

    return AdminRefundListItem(
        id=refund.id,
        order_id=refund.order_id,
        order_number=order_num,
        customer_id=refund.customer_id,
        customer_name=cust_name,
        amount=refund.amount,
        amount_inr=refund.amount,
        reason=refund.reason,
        status=refund.status,
        created_at=refund.created_at,
        decided_by=refund.decided_by,
    )


# ============================================================================
# Admin Orders Management
# ============================================================================


@router.get("/orders", response_model=list[AdminOrderListItem])
async def list_admin_orders(
    agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AdminOrderListItem]:
    """
    List all orders in the store with customer and item details.
    Supports filtering by stage status and searching by order number, customer name, email, or phone.
    """
    stmt = (
        select(Order)
        .join(Order.customer)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items),
        )
    )

    if status_filter:
        clean_status = status_filter.strip().lower()
        stmt = stmt.where(Order.status == clean_status)

    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Order.order_number.ilike(term),
                Customer.name.ilike(term),
                Customer.email.ilike(term),
                Customer.phone.ilike(term),
            )
        )

    stmt = stmt.order_by(Order.placed_at.desc()).offset(offset).limit(limit)
    res = await session.execute(stmt)
    orders = res.scalars().all()

    return [build_admin_order_item(order) for order in orders]


@router.post(
    "/orders/{order_number}/advance",
    response_model=AdminOrderListItem,
    dependencies=[Depends(verify_csrf)],
)
async def advance_admin_order(
    order_number: str,
    agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminOrderListItem:
    """
    Advance order through fulfillment stages:
    placed -> processing -> shipped -> delivered.
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items),
        )
        .where(Order.order_number == order_number)
        .with_for_update()
    )
    res = await session.execute(stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_number}' not found.",
        )

    current_status = (order.status or "").lower()
    now = datetime.now(UTC)

    if current_status == "placed":
        next_status = "processing"
    elif current_status == "processing":
        next_status = "shipped"
    elif current_status == "shipped":
        next_status = "delivered"
        order.delivered_at = now
    elif current_status in ("delivered", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order '{order_number}' is already in terminal state '{current_status}'.",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot advance order from unrecognized status '{order.status}'.",
        )

    order.status = next_status

    hist = OrderStatusHistory(
        order_id=order.id,
        status=next_status,
        at=now,
        note=f"Order stage advanced to {next_status} by admin {agent.email}",
    )
    session.add(hist)

    await session.commit()
    await session.refresh(order)

    logger.info(
        "Order %s advanced: %s -> %s by admin %s",
        order_number,
        current_status,
        next_status,
        agent.email,
    )
    return build_admin_order_item(order)


@router.post(
    "/orders/{order_number}/cancel",
    response_model=AdminOrderListItem,
    dependencies=[Depends(verify_csrf)],
)
async def cancel_admin_order(
    order_number: str,
    agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
    req: CancelOrderRequest | None = None,
) -> AdminOrderListItem:
    """
    Cancel an order from placed or processing stage, restocking product inventory.
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.customer),
            selectinload(Order.items),
        )
        .where(Order.order_number == order_number)
        .with_for_update()
    )
    res = await session.execute(stmt)
    order = res.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_number}' not found.",
        )

    current_status = (order.status or "").lower()
    if current_status not in ("placed", "processing", "pending"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order cannot be cancelled in '{order.status}' status.",
        )

    now = datetime.now(UTC)
    cancel_reason = (req.reason if req and req.reason else None) or f"Cancelled by administrator {agent.email}"

    order.status = "cancelled"
    order.cancelled_at = now
    order.cancel_reason = cancel_reason

    # Restock product stock
    for item in order.items:
        p_stmt = select(Product).where(Product.name_en == item.product_name).with_for_update()
        product = (await session.execute(p_stmt)).scalar_one_or_none()
        if product:
            product.stock_qty += item.quantity

    hist = OrderStatusHistory(
        order_id=order.id,
        status="cancelled",
        at=now,
        note=cancel_reason,
    )
    session.add(hist)

    await session.commit()
    await session.refresh(order)

    logger.info("Order %s cancelled by admin %s (reason: %s)", order_number, agent.email, cancel_reason)
    return build_admin_order_item(order)


# ============================================================================
# Admin Streamlined Refunds Management
# ============================================================================


@router.get("/refunds", response_model=list[AdminRefundListItem])
async def list_admin_refunds(
    agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AdminRefundListItem]:
    """
    List refunds in the store.
    Shows return amount, return reason, order number, customer name, and status.
    """
    stmt = (
        select(Refund)
        .join(Refund.order)
        .join(Refund.customer)
        .options(
            selectinload(Refund.order),
            selectinload(Refund.customer),
        )
    )

    if status_filter:
        clean_status = status_filter.strip().lower()
        stmt = stmt.where(Refund.status == clean_status)

    stmt = stmt.order_by(Refund.created_at.desc()).offset(offset).limit(limit)
    res = await session.execute(stmt)
    refunds = res.scalars().all()

    return [build_admin_refund_item(refund) for refund in refunds]


@router.post(
    "/refunds/{refund_id}/approve",
    response_model=AdminRefundListItem,
    dependencies=[Depends(verify_csrf)],
)
async def approve_admin_refund(
    refund_id: uuid.UUID,
    agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminRefundListItem:
    """
    Approve refund directly with row lock, mock payment payout, and order status update.
    """
    refund_stmt = (
        select(Refund)
        .options(
            selectinload(Refund.order),
            selectinload(Refund.customer),
        )
        .where(Refund.id == refund_id)
        .with_for_update()
    )
    refund = (await session.execute(refund_stmt)).scalar_one_or_none()

    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Refund '{refund_id}' not found.",
        )

    if refund.status != "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Refund is already '{refund.status}'. It cannot be approved again.",
        )

    # Process gateway payout
    gateway = MockPaymentGateway()
    try:
        payout_res = await gateway.payout(refund.customer_id, refund.order_id, refund.amount)
        if not payout_res or payout_res.get("status") != "success":
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Payment gateway payout failed. Refund remains pending approval.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        logger.error("Payout exception: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment gateway payout error: {str(exc)}",
        )

    refund.status = "processed"
    refund.decided_by = f"agent:{agent.email}"

    if refund.order:
        refund.order.payment_status = "refunded"
        hist = OrderStatusHistory(
            order_id=refund.order.id,
            status="refunded",
            at=datetime.now(UTC),
            note=f"Refund of ₹{refund.amount:,.2f} approved by admin {agent.email}",
        )
        session.add(hist)

    # If linked to an escalation, record an event
    esc_stmt = select(Escalation).where(Escalation.refund_id == refund.id).with_for_update()
    esc = (await session.execute(esc_stmt)).scalar_one_or_none()
    if esc:
        esc.status = "resolved"
        event = EscalationEvent(
            escalation_id=esc.id,
            actor_type="agent",
            actor_id=agent.id,
            action="refund_approved",
            detail={"amount": str(refund.amount), "refund_id": str(refund.id)},
        )
        session.add(event)

    await session.commit()
    await session.refresh(refund)

    logger.info(
        "Refund %s (order %s, amount ₹%s) approved by admin %s",
        refund.id,
        refund.order.order_number if refund.order else "n/a",
        refund.amount,
        agent.email,
    )
    return build_admin_refund_item(refund)


@router.post(
    "/refunds/{refund_id}/reject",
    response_model=AdminRefundListItem,
    dependencies=[Depends(verify_csrf)],
)
async def reject_admin_refund(
    refund_id: uuid.UUID,
    req: AdminRefundRejectRequest,
    agent: Annotated[Agent, Depends(get_current_agent)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminRefundListItem:
    """
    Reject refund directly with reason and record status history.
    """
    refund_stmt = (
        select(Refund)
        .options(
            selectinload(Refund.order),
            selectinload(Refund.customer),
        )
        .where(Refund.id == refund_id)
        .with_for_update()
    )
    refund = (await session.execute(refund_stmt)).scalar_one_or_none()

    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Refund '{refund_id}' not found.",
        )

    if refund.status != "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Refund is already '{refund.status}'. It cannot be rejected.",
        )

    refund.status = "rejected"
    refund.decided_by = f"agent:{agent.email}"

    if refund.order:
        hist = OrderStatusHistory(
            order_id=refund.order.id,
            status=refund.order.status,
            at=datetime.now(UTC),
            note=f"Refund rejected by admin {agent.email}: {req.reason}",
        )
        session.add(hist)

    # If linked to an escalation, record an event
    esc_stmt = select(Escalation).where(Escalation.refund_id == refund.id).with_for_update()
    esc = (await session.execute(esc_stmt)).scalar_one_or_none()
    if esc:
        event = EscalationEvent(
            escalation_id=esc.id,
            actor_type="agent",
            actor_id=agent.id,
            action="refund_rejected",
            detail={"reason": req.reason, "refund_id": str(refund.id)},
        )
        session.add(event)

    await session.commit()
    await session.refresh(refund)

    logger.info(
        "Refund %s (order %s, amount ₹%s) rejected by admin %s (reason: %s)",
        refund.id,
        refund.order.order_number if refund.order else "n/a",
        refund.amount,
        agent.email,
        req.reason,
    )
    return build_admin_refund_item(refund)
