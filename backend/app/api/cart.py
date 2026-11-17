import logging
import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_customer, verify_customer_csrf
from app.db import get_session
from app.models import Cart, CartItem, Customer, Product
from app.schemas import (
    CartItemAddRequest,
    CartItemResponse,
    CartItemUpdateRequest,
    CartProblem,
    CartResponse,
)

logger = logging.getLogger("app.api.cart")
router = APIRouter(prefix="/cart", tags=["cart"])


async def get_or_create_customer_cart(
    session: AsyncSession,
    customer_id: uuid.UUID,
) -> Cart:
    stmt = (
        select(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .where(Cart.customer_id == customer_id)
    )
    result = await session.execute(stmt)
    cart = result.scalar_one_or_none()
    if cart is None:
        cart = Cart(customer_id=customer_id)
        session.add(cart)
        await session.commit()
        await session.refresh(cart)
        stmt = (
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .where(Cart.id == cart.id)
        )
        cart = (await session.execute(stmt)).scalar_one()
    return cart


def build_cart_response(cart: Cart) -> CartResponse:
    item_responses: list[CartItemResponse] = []
    problems: list[CartProblem] = []
    subtotal = Decimal("0.00")
    total_items = 0

    for item in cart.items:
        p = item.product
        if not p or not p.is_active:
            problems.append(
                CartProblem(
                    code="inactive_product",
                    product_id=item.product_id,
                    message="This product is currently unavailable.",
                )
            )
            is_avail = False
        elif p.stock_qty <= 0:
            problems.append(
                CartProblem(
                    code="out_of_stock",
                    product_id=item.product_id,
                    message=f"'{p.name_en}' is currently out of stock.",
                )
            )
            is_avail = False
        else:
            is_avail = True
            if item.quantity > p.stock_qty:
                problems.append(
                    CartProblem(
                        code="quantity_exceeded",
                        product_id=item.product_id,
                        message=f"Only {p.stock_qty} units available for '{p.name_en}'.",
                    )
                )

        item_subtotal = p.price * item.quantity if p else Decimal("0.00")
        if is_avail:
            subtotal += item_subtotal
            total_items += item.quantity

        item_responses.append(
            CartItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_sku=p.sku if p else "",
                sku=p.sku if p else "",
                product_name_en=p.name_en if p else "Unavailable",
                title=p.name_en if p else "Unavailable",
                product_name_ta=p.name_ta if p else "கிடைக்கவில்லை",
                title_ta=p.name_ta if p else "கிடைக்கவில்லை",
                unit_price=p.price if p else Decimal("0.00"),
                price_inr=p.price if p else Decimal("0.00"),
                quantity=item.quantity,
                subtotal=item_subtotal,
                subtotal_inr=item_subtotal,
                stock_qty=p.stock_qty if p else 0,
                stock_available=p.stock_qty if p else 0,
                is_available=is_avail,
                in_stock=is_avail,
                image_url=f"/api/products/{item.product_id}/image.svg",
            )
        )

    tax = Decimal("0.00")
    shipping = Decimal("0.00")
    total = subtotal + tax + shipping

    return CartResponse(
        items=item_responses,
        total_items=total_items,
        subtotal=subtotal,
        subtotal_inr=subtotal,
        tax=tax,
        shipping=shipping,
        shipping_fee_inr=shipping,
        total=total,
        total_inr=total,
        is_checkout_ready=len(problems) == 0 and total_items > 0,
        problems=problems,
    )


@router.get("", response_model=CartResponse)
async def get_cart(
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CartResponse:
    cart = await get_or_create_customer_cart(session, customer.id)
    return build_cart_response(cart)


@router.post(
    "/items",
    response_model=CartResponse,
    dependencies=[Depends(verify_customer_csrf)],
)
async def add_item_to_cart(
    req: CartItemAddRequest,
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CartResponse:
    # Verify product
    p_stmt = select(Product).where(Product.id == req.product_id)
    p_res = await session.execute(p_stmt)
    product = p_res.scalar_one_or_none()
    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or unavailable.",
        )
    if product.stock_qty <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is out of stock.",
        )

    cart = await get_or_create_customer_cart(session, customer.id)

    # Check if item exists in cart
    existing_item = next((i for i in cart.items if i.product_id == req.product_id), None)
    if existing_item:
        new_qty = min(existing_item.quantity + req.quantity, 10, product.stock_qty)
        existing_item.quantity = new_qty
    else:
        new_qty = min(req.quantity, 10, product.stock_qty)
        new_item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            product=product,
            quantity=new_qty,
        )
        session.add(new_item)
        cart.items.append(new_item)

    await session.commit()
    return build_cart_response(cart)


@router.patch(
    "/items/{product_id}",
    response_model=CartResponse,
    dependencies=[Depends(verify_customer_csrf)],
)
async def update_cart_item(
    product_id: uuid.UUID,
    req: CartItemUpdateRequest,
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CartResponse:
    cart = await get_or_create_customer_cart(session, customer.id)
    item = next((i for i in cart.items if i.product_id == product_id), None)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in cart.",
        )

    if req.quantity <= 0:
        await session.delete(item)
        cart.items.remove(item)
    else:
        item.quantity = min(req.quantity, 10)

    await session.commit()
    return build_cart_response(cart)


@router.delete(
    "/items/{product_id}",
    response_model=CartResponse,
    dependencies=[Depends(verify_customer_csrf)],
)
async def remove_cart_item(
    product_id: uuid.UUID,
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CartResponse:
    cart = await get_or_create_customer_cart(session, customer.id)
    item = next((i for i in cart.items if i.product_id == product_id), None)
    if item:
        await session.delete(item)
        cart.items.remove(item)
        await session.commit()

    return build_cart_response(cart)


@router.delete(
    "",
    response_model=CartResponse,
    dependencies=[Depends(verify_customer_csrf)],
)
async def clear_cart(
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CartResponse:
    cart = await get_or_create_customer_cart(session, customer.id)
    stmt = delete(CartItem).where(CartItem.cart_id == cart.id)
    await session.execute(stmt)
    cart.items.clear()
    await session.commit()

    return build_cart_response(cart)
