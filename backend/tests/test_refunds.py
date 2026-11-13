import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Customer, Order, Refund
from app.services.payments import MockPaymentGateway
from app.services.tools import check_refund_eligibility, create_refund


@pytest.mark.asyncio
async def test_refund_exact_limit_and_one_rupee_above(db_session: AsyncSession):
    customer = Customer(name="Test User", phone="+919999999901", preferred_language="en")
    db_session.add(customer)
    await db_session.flush()

    now = datetime.now(UTC)

    # Order exactly at 2000.00
    order_exact = Order(
        order_number="ORD-EXACT",
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("2000.00"),
        placed_at=now - timedelta(days=2),
        delivered_at=now - timedelta(days=1),
    )
    # Order at 2001.00
    order_above = Order(
        order_number="ORD-ABOVE",
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("2001.00"),
        placed_at=now - timedelta(days=2),
        delivered_at=now - timedelta(days=1),
    )
    db_session.add_all([order_exact, order_above])
    await db_session.commit()

    gateway = MockPaymentGateway()

    # Process ORD-EXACT: should be auto-approved / processed with payout
    res_exact = await create_refund(
        session=db_session,
        customer_id=customer.id,
        order_number="ORD-EXACT",
        refund_reason="Size issue",
        auto_approve_limit=Decimal("2000.00"),
        payment_gateway=gateway,
    )
    assert res_exact["success"] is True
    assert res_exact["status"] == "processed"
    assert res_exact["requires_human"] is False
    assert res_exact["payout_info"] is not None
    assert res_exact["payout_info"]["status"] == "success"

    # Process ORD-ABOVE: should be pending_approval, no payout, requires_human=True
    res_above = await create_refund(
        session=db_session,
        customer_id=customer.id,
        order_number="ORD-ABOVE",
        refund_reason="Defective piece",
        auto_approve_limit=Decimal("2000.00"),
        payment_gateway=gateway,
    )
    assert res_above["success"] is True
    assert res_above["status"] == "pending_approval"
    assert res_above["requires_human"] is True
    assert res_above["payout_info"] is None


@pytest.mark.asyncio
async def test_refund_ineligibility_reasons(db_session: AsyncSession):
    customer = Customer(name="Test User 2", phone="+919999999902", preferred_language="en")
    db_session.add(customer)
    await db_session.flush()

    now = datetime.now(UTC)

    # 1. Non-delivered order
    order_shipped = Order(
        order_number="ORD-SHIPPED",
        customer_id=customer.id,
        status="shipped",
        total_amount=Decimal("1500.00"),
        placed_at=now - timedelta(days=3),
    )
    # 2. Delivered outside return window (10 days ago, window=7)
    order_expired = Order(
        order_number="ORD-EXPIRED",
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("1200.00"),
        placed_at=now - timedelta(days=12),
        delivered_at=now - timedelta(days=10),
    )
    # 3. Already refunded order
    order_refunded = Order(
        order_number="ORD-REFUNDED",
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("1000.00"),
        placed_at=now - timedelta(days=4),
        delivered_at=now - timedelta(days=2),
    )
    db_session.add_all([order_shipped, order_expired, order_refunded])
    await db_session.flush()

    existing_refund = Refund(
        order_id=order_refunded.id,
        customer_id=customer.id,
        amount=Decimal("1000.00"),
        status="processed",
        reason="Initial return",
    )
    db_session.add(existing_refund)
    await db_session.commit()

    # Check non-delivered
    check_shipped = await check_refund_eligibility(
        db_session, customer.id, "ORD-SHIPPED", return_window_days=7
    )
    assert check_shipped["eligible"] is False
    assert check_shipped["reason"] == "not_delivered"

    # Check expired window
    check_expired = await check_refund_eligibility(
        db_session, customer.id, "ORD-EXPIRED", return_window_days=7
    )
    assert check_expired["eligible"] is False
    assert check_expired["reason"] == "return_window_expired"

    # Check already refunded
    check_refunded = await check_refund_eligibility(
        db_session, customer.id, "ORD-REFUNDED", return_window_days=7
    )
    assert check_refunded["eligible"] is False
    assert check_refunded["reason"] == "already_refunded"


@pytest.mark.asyncio
async def test_concurrent_refund_race_condition(test_engine):
    """
    Test that concurrent requests attempting to refund the same order result in exactly one active refund.
    """
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as setup_session:
        customer = Customer(name="Race Test", phone=f"+91{uuid.uuid4().hex[:10]}", preferred_language="en")
        setup_session.add(customer)
        await setup_session.flush()

        now = datetime.now(UTC)
        order = Order(
            order_number=f"ORD-RACE-{uuid.uuid4().hex[:6]}",
            customer_id=customer.id,
            status="delivered",
            total_amount=Decimal("1200.00"),
            placed_at=now - timedelta(days=3),
            delivered_at=now - timedelta(days=1),
        )
        setup_session.add(order)
        await setup_session.commit()
        cust_id = customer.id
        ord_num = order.order_number
        ord_id = order.id

    async def attempt_refund():
        async with session_factory() as worker_session:
            return await create_refund(
                session=worker_session,
                customer_id=cust_id,
                order_number=ord_num,
                refund_reason="Concurrent race attempt",
                auto_approve_limit=Decimal("2000.00"),
            )

    # Launch 4 simultaneous refund creation attempts
    results = await asyncio.gather(
        attempt_refund(),
        attempt_refund(),
        attempt_refund(),
        attempt_refund(),
        return_exceptions=True,
    )

    success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success") is True)
    assert success_count == 1, f"Expected exactly 1 successful refund, got: {results}"

    async with session_factory() as verify_session:
        refunds_stmt = select(Refund).where(Refund.order_id == ord_id)
        refunds = list((await verify_session.execute(refunds_stmt)).scalars().all())
        assert len(refunds) == 1
