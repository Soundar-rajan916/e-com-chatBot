import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_customer, verify_customer_csrf
from app.config import get_settings
from app.db import get_session
from app.models import (
    Cart,
    CartItem,
    Customer,
    IdempotencyKey,
    Order,
    OrderItem,
    OrderStatusHistory,
    Product,
    Refund,
)
from app.schemas import (
    CancelOrderRequest,
    CheckoutRequest,
    OrderDetailResponse,
    OrderItemSummary,
    OrderListItemResponse,
    ReturnInfo,
    ReturnOrderRequest,
    ReturnOrderResponse,
)
from app.services.refunds import request_refund

logger = logging.getLogger("app.api.orders")
router = APIRouter(tags=["orders"])


def calculate_return_info(order: Order, active_refund: Refund | None) -> ReturnInfo:
    settings = get_settings()
    window_days = settings.RETURN_WINDOW_DAYS

    if active_refund is not None:
        return ReturnInfo(
            eligible=False,
            reason_ineligible=f"An active refund exists with status '{active_refund.status}'.",
            days_remaining=0,
            active_refund_status=active_refund.status,
            active_refund_id=active_refund.id,
        )

    if order.status != "delivered":
        return ReturnInfo(
            eligible=False,
            reason_ineligible=f"Only delivered orders are eligible for return (currently '{order.status}').",
            days_remaining=None,
        )

    if not order.delivered_at:
        return ReturnInfo(
            eligible=False,
            reason_ineligible="Delivery date is missing.",
            days_remaining=None,
        )

    now_utc = datetime.now(UTC)
    del_utc = (
        order.delivered_at.replace(tzinfo=UTC)
        if order.delivered_at.tzinfo is None
        else order.delivered_at.astimezone(UTC)
    )
    days_elapsed = (now_utc - del_utc).days
    days_left = max(0, window_days - days_elapsed)

    if days_elapsed > window_days:
        return ReturnInfo(
            eligible=False,
            reason_ineligible=f"Return window of {window_days} days has expired ({days_elapsed} days elapsed).",
            days_remaining=0,
        )

    return ReturnInfo(
        eligible=True,
        days_remaining=days_left,
    )


def build_order_detail_response(order: Order, active_refund: Refund | None) -> OrderDetailResponse:
    items_summary = [
        OrderItemSummary(
            id=item.id,
            product_id=item.id,
            product_title=item.product_name,
            title=item.product_name,
            quantity=item.quantity,
            unit_price_inr=item.unit_price,
            subtotal_inr=item.unit_price * item.quantity,
        )
        for item in order.items
    ]

    history_records = [
        {
            "id": h.id,
            "status": h.status,
            "at": h.at.isoformat() if h.at else None,
            "created_at": h.at.isoformat() if h.at else None,
            "note": h.note,
        }
        for h in (order.status_history or [])
    ]

    street_parts = [order.shipping_line1, order.shipping_line2]
    street = ", ".join([str(p) for p in street_parts if p])

    shipping_addr = {
        "full_name": order.shipping_name or "",
        "street": street,
        "city": order.shipping_city or "",
        "state": order.shipping_state or "",
        "pincode": order.shipping_pincode or "",
    }

    ret_info = calculate_return_info(order, active_refund)
    is_cancellable = order.status in ("placed", "confirmed", "processing", "pending")
    is_returnable = ret_info.eligible

    return OrderDetailResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        total_amount=order.total_amount,
        total_amount_inr=order.total_amount,
        placed_at=order.placed_at,
        created_at=order.placed_at.isoformat() if order.placed_at else None,
        estimated_delivery=order.estimated_delivery,
        delivered_at=order.delivered_at,
        tracking_note=order.tracking_note,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        shipping_name=order.shipping_name,
        shipping_phone=order.shipping_phone,
        shipping_line1=order.shipping_line1,
        shipping_line2=order.shipping_line2,
        shipping_city=order.shipping_city,
        shipping_state=order.shipping_state,
        shipping_pincode=order.shipping_pincode,
        shipping_address=shipping_addr,
        cancelled_at=order.cancelled_at,
        cancel_reason=order.cancel_reason,
        cancellation_reason=order.cancel_reason,
        is_cancellable=is_cancellable,
        is_returnable=is_returnable,
        items=items_summary,
        status_history=history_records,
        return_info=ret_info,
    )


@router.post(
    "/checkout",
    response_model=OrderDetailResponse,
    dependencies=[Depends(verify_customer_csrf)],
)
async def checkout(
    req: CheckoutRequest,
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> OrderDetailResponse:
    now = datetime.now(UTC)

    # 1. Check idempotency key if provided
    if idempotency_key:
        clean_key = idempotency_key.strip()
        idem_stmt = (
            select(IdempotencyKey)
            .where(
                IdempotencyKey.customer_id == customer.id,
                IdempotencyKey.key == clean_key,
            )
            .options(
                selectinload(IdempotencyKey.order).selectinload(Order.items),
                selectinload(IdempotencyKey.order).selectinload(Order.status_history),
            )
        )
        idem_res = await session.execute(idem_stmt)
        idem = idem_res.scalar_one_or_none()
        if idem and idem.order:
            logger.info("Idempotent checkout hit for key %s, order %s", clean_key, idem.order.order_number)
            ref_stmt = select(Refund).where(Refund.order_id == idem.order.id)
            refund = (await session.execute(ref_stmt)).scalar_one_or_none()
            return build_order_detail_response(idem.order, refund)

    # 2. Load Cart
    cart_stmt = (
        select(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .where(Cart.customer_id == customer.id)
    )
    cart_res = await session.execute(cart_stmt)
    cart = cart_res.scalar_one_or_none()

    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your cart is empty.",
        )

    # 3. Row-lock products ordered by product_id ASC to prevent deadlocks
    product_ids = sorted([item.product_id for item in cart.items])
    lock_stmt = (
        select(Product)
        .where(Product.id.in_(product_ids))
        .order_by(Product.id.asc())
        .with_for_update()
    )
    products_res = await session.execute(lock_stmt)
    locked_products = {p.id: p for p in products_res.scalars().all()}

    # 4. Validate stock and active status
    cart_items_map = {item.product_id: item.quantity for item in cart.items}
    total_amount = Decimal("0.00")

    for p_id in product_ids:
        p = locked_products.get(p_id)
        qty = cart_items_map[p_id]
        if not p or not p.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product {p.name_en if p else 'Item'} is no longer available.",
            )
        if p.stock_qty < qty:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient stock for '{p.name_en}'. Only {p.stock_qty} left.",
            )
        total_amount += p.price * qty

    # 5. Process Payment (Mock)
    if req.payment_method == "demo_card":
        if req.demo_payment_result == "failure":
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Demo card payment was declined as requested.",
            )
        payment_status = "paid"
    else:
        payment_status = "pending"

    # 6. Decrement stock
    for p_id in product_ids:
        p = locked_products[p_id]
        p.stock_qty -= cart_items_map[p_id]

    # 7. Create Order & Items
    order_number = f"ORD-{now.year}-{int(now.timestamp()) % 10000:04d}-{uuid.uuid4().hex[:4].upper()}"
    estimated_del = now + timedelta(days=3)

    new_order = Order(
        order_number=order_number,
        customer_id=customer.id,
        status="placed",
        total_amount=total_amount,
        placed_at=now,
        estimated_delivery=estimated_del,
        shipping_name=req.shipping_address.name.strip(),
        shipping_phone=req.shipping_address.phone.strip(),
        shipping_line1=req.shipping_address.line1.strip(),
        shipping_line2=req.shipping_address.line2.strip() if req.shipping_address.line2 else None,
        shipping_city=req.shipping_address.city.strip(),
        shipping_state=req.shipping_address.state.strip(),
        shipping_pincode=req.shipping_address.pincode.strip(),
        payment_method=req.payment_method,
        payment_status=payment_status,
    )
    session.add(new_order)
    await session.flush()

    for item in cart.items:
        p = locked_products[item.product_id]
        order_item = OrderItem(
            order_id=new_order.id,
            product_name=p.name_en,
            quantity=item.quantity,
            unit_price=p.price,
        )
        session.add(order_item)

    # 8. Record Order Status History
    status_hist = OrderStatusHistory(
        order_id=new_order.id,
        status="placed",
        at=now,
        note=f"Order placed with payment method '{req.payment_method}' ({payment_status}).",
    )
    session.add(status_hist)

    # 9. Clear Cart
    await session.execute(delete(CartItem).where(CartItem.cart_id == cart.id))

    # 10. Store idempotency key if present
    if idempotency_key:
        clean_key = idempotency_key.strip()
        idem_record = IdempotencyKey(
            customer_id=customer.id,
            key=clean_key,
            order_id=new_order.id,
        )
        session.add(idem_record)

    await session.commit()

    # Re-fetch order with items and history for response
    full_stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history),
        )
        .where(Order.id == new_order.id)
    )
    order_loaded = (await session.execute(full_stmt)).scalar_one()
    return build_order_detail_response(order_loaded, None)


@router.get("/me/orders", response_model=list[OrderListItemResponse])
async def list_customer_orders(
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[OrderListItemResponse]:
    offset = (page - 1) * page_size
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.customer_id == customer.id)
        .order_by(Order.placed_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    orders = (await session.execute(stmt)).scalars().all()

    return [
        OrderListItemResponse(
            order_number=o.order_number,
            status=o.status,
            total_amount=o.total_amount,
            placed_at=o.placed_at,
            delivered_at=o.delivered_at,
            items_count=sum(item.quantity for item in o.items),
            payment_method=o.payment_method,
            payment_status=o.payment_status,
        )
        for o in orders
    ]


@router.get("/me/orders/{order_number}", response_model=OrderDetailResponse)
async def get_order_detail(
    order_number: str,
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderDetailResponse:
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history),
        )
        .where(Order.order_number == order_number, Order.customer_id == customer.id)
    )
    order = (await session.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found under your account.",
        )

    ref_stmt = select(Refund).where(Refund.order_id == order.id)
    refund = (await session.execute(ref_stmt)).scalar_one_or_none()

    return build_order_detail_response(order, refund)


@router.post(
    "/me/orders/{order_number}/cancel",
    response_model=OrderDetailResponse,
    dependencies=[Depends(verify_customer_csrf)],
)
async def cancel_order(
    order_number: str,
    req: CancelOrderRequest,
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderDetailResponse:
    stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.status_history))
        .where(Order.order_number == order_number, Order.customer_id == customer.id)
        .with_for_update()
    )
    order = (await session.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found under your account.",
        )

    if order.status not in ("placed", "processing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order cannot be cancelled in '{order.status}' status.",
        )

    now = datetime.now(UTC)
    reason_text = req.reason or "Customer cancelled order"
    order.status = "cancelled"
    order.cancelled_at = now
    order.cancel_reason = reason_text

    # Restock products
    for item in order.items:
        p_stmt = select(Product).where(Product.name_en == item.product_name).with_for_update()
        product = (await session.execute(p_stmt)).scalar_one_or_none()
        if product:
            product.stock_qty += item.quantity

    # Add status history
    hist = OrderStatusHistory(
        order_id=order.id,
        status="cancelled",
        at=now,
        note=f"Order cancelled by customer: {reason_text}",
    )
    session.add(hist)
    await session.commit()

    ref_stmt = select(Refund).where(Refund.order_id == order.id)
    refund = (await session.execute(ref_stmt)).scalar_one_or_none()
    return build_order_detail_response(order, refund)


@router.post(
    "/me/orders/{order_number}/return",
    response_model=ReturnOrderResponse,
    dependencies=[Depends(verify_customer_csrf)],
)
async def return_order(
    order_number: str,
    req: ReturnOrderRequest,
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReturnOrderResponse:
    res = await request_refund(
        session=session,
        customer_id=customer.id,
        order_number=order_number,
        reason=req.reason.strip(),
        source="store_web_return",
    )
    if not res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.get("message", "Return request failed."),
        )

    return ReturnOrderResponse(
        order_number=order_number,
        refund_id=uuid.UUID(res["refund_id"]),
        status=res["status"],
        auto_approved=res["auto_approved"],
        amount=Decimal(str(res["amount"])),
        message=res["message"],
    )


# ============================================================================
# Dev Testing Order Advance Endpoints (APP_ENV in "dev", "test")
# ============================================================================


@router.post(
    "/dev/orders/{order_number}/advance",
    response_model=OrderDetailResponse,
)
async def dev_advance_order(
    order_number: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrderDetailResponse:
    settings = get_settings()
    if settings.APP_ENV not in ("dev", "test"):
        raise HTTPException(status_code=403, detail="Dev endpoints disabled in production.")

    stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.status_history))
        .where(Order.order_number == order_number)
        .with_for_update()
    )
    order = (await session.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    transitions = {
        "placed": "processing",
        "processing": "shipped",
        "shipped": "delivered",
    }
    next_status = transitions.get(order.status)
    if not next_status:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot advance order from '{order.status}' status.",
        )

    now = datetime.now(UTC)
    order.status = next_status
    if next_status == "delivered":
        order.delivered_at = now

    hist = OrderStatusHistory(
        order_id=order.id,
        status=next_status,
        at=now,
        note=f"[Dev] Order status advanced to {next_status}",
    )
    session.add(hist)
    await session.commit()

    ref_stmt = select(Refund).where(Refund.order_id == order.id)
    refund = (await session.execute(ref_stmt)).scalar_one_or_none()
    return build_order_detail_response(order, refund)


@router.post(
    "/dev/orders/{order_number}/set-delivered-days-ago",
    response_model=OrderDetailResponse,
)
async def dev_set_delivered_days_ago(
    order_number: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    days_ago: int = Query(..., ge=0),
) -> OrderDetailResponse:
    settings = get_settings()
    if settings.APP_ENV not in ("dev", "test"):
        raise HTTPException(status_code=403, detail="Dev endpoints disabled in production.")

    stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.status_history))
        .where(Order.order_number == order_number)
        .with_for_update()
    )
    order = (await session.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    now = datetime.now(UTC)
    del_date = now - timedelta(days=days_ago)
    order.status = "delivered"
    order.delivered_at = del_date

    hist = OrderStatusHistory(
        order_id=order.id,
        status="delivered",
        at=now,
        note=f"[Dev] Set delivered date to {days_ago} days ago ({del_date.strftime('%Y-%m-%d')})",
    )
    session.add(hist)
    await session.commit()

    ref_stmt = select(Refund).where(Refund.order_id == order.id)
    refund = (await session.execute(ref_stmt)).scalar_one_or_none()
    return build_order_detail_response(order, refund)
