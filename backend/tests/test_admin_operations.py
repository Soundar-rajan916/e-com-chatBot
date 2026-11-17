import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.models import Agent, Customer, Order, OrderItem, Product, Refund


@pytest.mark.asyncio
async def test_admin_orders_operations(client: AsyncClient, db_session: AsyncSession):
    # 1. Create admin agent and log in
    agent = Agent(
        email="ops_admin@example.com",
        name="Ops Admin",
        password_hash=hash_password("AdminPass123!"),
        role="admin",
        is_active=True,
    )
    db_session.add(agent)

    # 2. Create customer and product
    customer = Customer(
        name="Rajesh Kumar",
        phone="+919876543299",
        email="rajesh@example.com",
        preferred_language="en",
    )
    db_session.add(customer)

    prod = Product(
        sku="TEST-SKU-SNACK-01",
        name_en="Chettinad Mixture",
        name_ta="செட்டிநாடு மிக்சர்",
        category="Snacks",
        description_en="Crispy spiced mixture",
        description_ta="காரசாரமான மிக்சர்",
        price=Decimal("150.00"),
        stock_qty=10,
        is_active=True,
        content_hash="hash_ops_1",
        embedding=[0.01] * 384,
    )
    db_session.add(prod)
    await db_session.flush()

    # 3. Create Order 1 (for stage progression)
    order1 = Order(
        order_number="ORD-TEST-STAGE-01",
        customer_id=customer.id,
        total_amount=Decimal("300.00"),
        status="placed",
        placed_at=datetime.now(UTC),
        payment_method="cod",
        payment_status="pending",
    )
    db_session.add(order1)
    await db_session.flush()

    item1 = OrderItem(
        order_id=order1.id,
        product_name="Chettinad Mixture",
        quantity=2,
        unit_price=Decimal("150.00"),
    )
    db_session.add(item1)

    # 4. Create Order 2 (for cancellation and restocking test)
    # Deduct 3 units from product stock to simulate purchase
    prod.stock_qty = 7
    order2 = Order(
        order_number="ORD-TEST-CANCEL-02",
        customer_id=customer.id,
        total_amount=Decimal("450.00"),
        status="placed",
        placed_at=datetime.now(UTC),
        payment_method="cod",
        payment_status="pending",
    )
    db_session.add(order2)
    await db_session.flush()

    item2 = OrderItem(
        order_id=order2.id,
        product_name="Chettinad Mixture",
        quantity=3,
        unit_price=Decimal("150.00"),
    )
    db_session.add(item2)
    await db_session.commit()

    # Log in as agent
    headers = {"X-Requested-With": "admin-console"}
    login_res = await client.post(
        "/admin/auth/login",
        json={"email": "ops_admin@example.com", "password": "AdminPass123!"},
        headers=headers,
    )
    assert login_res.status_code == 200

    # 5. GET /admin/orders: verify both orders are returned
    list_res = await client.get("/admin/orders")
    assert list_res.status_code == 200
    orders_data = list_res.json()
    assert len(orders_data) >= 2
    order_nums = [o["order_number"] for o in orders_data]
    assert "ORD-TEST-STAGE-01" in order_nums
    assert "ORD-TEST-CANCEL-02" in order_nums

    # 6. Test stage progression on Order 1:
    # placed -> processing
    adv1 = await client.post("/admin/orders/ORD-TEST-STAGE-01/advance", headers=headers)
    assert adv1.status_code == 200
    assert adv1.json()["status"] == "processing"

    # processing -> shipped
    adv2 = await client.post("/admin/orders/ORD-TEST-STAGE-01/advance", headers=headers)
    assert adv2.status_code == 200
    assert adv2.json()["status"] == "shipped"

    # shipped -> delivered
    adv3 = await client.post("/admin/orders/ORD-TEST-STAGE-01/advance", headers=headers)
    assert adv3.status_code == 200
    data3 = adv3.json()
    assert data3["status"] == "delivered"
    assert data3["delivered_at"] is not None

    # advancing delivered order returns 400
    adv4 = await client.post("/admin/orders/ORD-TEST-STAGE-01/advance", headers=headers)
    assert adv4.status_code == 400

    # 7. Test cancelling Order 2:
    cancel_res = await client.post(
        "/admin/orders/ORD-TEST-CANCEL-02/cancel",
        json={"reason": "Customer called to cancel"},
        headers=headers,
    )
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["status"] == "cancelled"

    # Check that product stock was restocked: 7 + 3 = 10
    await db_session.refresh(prod)
    assert prod.stock_qty == 10


@pytest.mark.asyncio
async def test_admin_refunds_operations(client: AsyncClient, db_session: AsyncSession):
    # Setup admin
    agent = Agent(
        email="refunds_admin@example.com",
        name="Refunds Admin",
        password_hash=hash_password("AdminPass123!"),
        role="admin",
        is_active=True,
    )
    db_session.add(agent)

    customer = Customer(
        name="Meena Sundaram",
        phone="+919876543288",
        email="meena@example.com",
        preferred_language="en",
    )
    db_session.add(customer)
    await db_session.flush()

    order = Order(
        order_number="ORD-REFUND-001",
        customer_id=customer.id,
        total_amount=Decimal("2500.00"),
        status="delivered",
        placed_at=datetime.now(UTC),
        payment_method="demo_card",
        payment_status="paid",
    )
    db_session.add(order)
    await db_session.flush()

    # Refund 1: to be approved
    refund1 = Refund(
        order_id=order.id,
        customer_id=customer.id,
        amount=Decimal("2500.00"),
        status="pending_approval",
        reason="Item was broken on arrival",
    )
    db_session.add(refund1)

    # Refund 2: to be rejected
    order2 = Order(
        order_number="ORD-REFUND-002",
        customer_id=customer.id,
        total_amount=Decimal("800.00"),
        status="delivered",
        placed_at=datetime.now(UTC),
        payment_method="cod",
        payment_status="paid",
    )
    db_session.add(order2)
    await db_session.flush()

    refund2 = Refund(
        order_id=order2.id,
        customer_id=customer.id,
        amount=Decimal("800.00"),
        status="pending_approval",
        reason="Does not fit preferences",
    )
    db_session.add(refund2)
    await db_session.commit()

    # Log in as agent
    headers = {"X-Requested-With": "admin-console"}
    await client.post(
        "/admin/auth/login",
        json={"email": "refunds_admin@example.com", "password": "AdminPass123!"},
        headers=headers,
    )

    # 1. GET /admin/refunds
    r_list = await client.get("/admin/refunds")
    assert r_list.status_code == 200
    refunds = r_list.json()
    assert len(refunds) >= 2

    # Check that return amount and return reason are accurately returned
    target1 = next(r for r in refunds if r["id"] == str(refund1.id))
    assert Decimal(str(target1["amount"])) == Decimal("2500.00")
    assert target1["reason"] == "Item was broken on arrival"
    assert target1["order_number"] == "ORD-REFUND-001"

    # 2. POST /admin/refunds/{id}/approve
    appr_res = await client.post(f"/admin/refunds/{refund1.id}/approve", headers=headers)
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["status"] == "processed"
    assert "refunds_admin@example.com" in appr_data["decided_by"]

    # Re-approving already decided refund returns 409
    appr_again = await client.post(f"/admin/refunds/{refund1.id}/approve", headers=headers)
    assert appr_again.status_code == 409

    # 3. POST /admin/refunds/{id}/reject
    rej_res = await client.post(
        f"/admin/refunds/{refund2.id}/reject",
        json={"reason": "Return request was submitted past return window."},
        headers=headers,
    )
    assert rej_res.status_code == 200
    rej_data = rej_res.json()
    assert rej_data["status"] == "rejected"
    assert "refunds_admin@example.com" in rej_data["decided_by"]
