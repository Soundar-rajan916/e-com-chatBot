import asyncio
import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_factory, engine
from app.models import ChatMessage, ChatSession, Customer, Escalation, Order, OrderItem, Refund, Trace


async def seed_data(session: AsyncSession) -> None:
    # Check if already seeded
    res = await session.execute(select(Customer).limit(1))
    if res.scalar_one_or_none():
        print("Database already contains customer data. Cleaning and reseeding idempotently...")

        for model in [Trace, ChatMessage, ChatSession, Escalation, Refund, OrderItem, Order, Customer]:
            await session.execute(model.__table__.delete())
        await session.commit()

    now = datetime.now(UTC)

    # 1. Five Customers
    customers_data = [
        {"name": "Priya Sharma", "phone": "+919876543210", "preferred_language": "en"},
        {"name": "Karthik Raja", "phone": "+919876543211", "preferred_language": "ta"},
        {"name": "Ananya Sundaram", "phone": "+919876543212", "preferred_language": "tanglish"},
        {"name": "Suresh Kumar", "phone": "+919876543213", "preferred_language": "ta"},
        {"name": "Deepa Raman", "phone": "+919876543214", "preferred_language": "en"},
    ]

    customers = []
    for c_info in customers_data:
        c = Customer(
            id=uuid.uuid4(),
            name=c_info["name"],
            phone=c_info["phone"],
            preferred_language=c_info["preferred_language"],
        )
        session.add(c)
        customers.append(c)

    await session.flush()

    # 2. Orders and Items
    orders_data = [
        # Customer 1 (Priya)
        {
            "order_number": "ORD-10001",
            "customer": customers[0],
            "status": "delivered",
            "total_amount": Decimal("1499.00"),
            "placed_at": now - timedelta(days=5),
            "estimated_delivery": now - timedelta(days=2),
            "delivered_at": now - timedelta(days=2),
            "tracking_note": "Delivered to reception at 2:30 PM",
            "items": [("Cotton Kurti Set", 1, Decimal("1499.00"))],
        },
        {
            "order_number": "ORD-10002",
            "customer": customers[0],
            "status": "delivered",
            "total_amount": Decimal("3499.00"),
            "placed_at": now - timedelta(days=7),
            "estimated_delivery": now - timedelta(days=3),
            "delivered_at": now - timedelta(days=3),
            "tracking_note": "Handed to customer",
            "items": [("Wireless Noise-Cancelling Headphones", 1, Decimal("3499.00"))],
        },
        {
            "order_number": "ORD-10003",
            "customer": customers[0],
            "status": "delivered",
            "total_amount": Decimal("899.00"),
            "placed_at": now - timedelta(days=25),
            "estimated_delivery": now - timedelta(days=20),
            "delivered_at": now - timedelta(days=20),
            "tracking_note": "Delivered",
            "items": [("Ceramic Coffee Mug Set", 1, Decimal("899.00"))],
        },
        # Customer 2 (Karthik)
        {
            "order_number": "ORD-10004",
            "customer": customers[1],
            "status": "delivered",
            "total_amount": Decimal("1299.00"),
            "placed_at": now - timedelta(days=4),
            "estimated_delivery": now - timedelta(days=1),
            "delivered_at": now - timedelta(days=1),
            "tracking_note": "Delivered at front door",
            "items": [("Running Shoes Blue Size 9", 1, Decimal("1299.00"))],
            "has_refund": True,
            "refund_status": "processed",
            "refund_reason": "Item size too small, customer requested instant return",
        },
        {
            "order_number": "ORD-10005",
            "customer": customers[1],
            "status": "delivered",
            "total_amount": Decimal("4500.00"),
            "placed_at": now - timedelta(days=6),
            "estimated_delivery": now - timedelta(days=2),
            "delivered_at": now - timedelta(days=2),
            "tracking_note": "Delivered with signature",
            "items": [("Smart Fitness Watch Pro", 1, Decimal("4500.00"))],
        },
        {
            "order_number": "ORD-10006",
            "customer": customers[1],
            "status": "shipped",
            "total_amount": Decimal("2199.00"),
            "placed_at": now - timedelta(days=2),
            "estimated_delivery": now + timedelta(days=2),
            "delivered_at": None,
            "tracking_note": "Package in transit at Chennai Central Sort Facility",
            "items": [("Mechanical Gaming Keyboard", 1, Decimal("2199.00"))],
        },
        # Customer 3 (Ananya)
        {
            "order_number": "ORD-10007",
            "customer": customers[2],
            "status": "delivered",
            "total_amount": Decimal("850.00"),
            "placed_at": now - timedelta(days=3),
            "estimated_delivery": now - timedelta(days=1),
            "delivered_at": now - timedelta(days=1),
            "tracking_note": "Delivered to security gate",
            "items": [("Stainless Steel Water Bottle 1L", 1, Decimal("850.00"))],
        },
        {
            "order_number": "ORD-10008",
            "customer": customers[2],
            "status": "out_for_delivery",
            "total_amount": Decimal("1599.00"),
            "placed_at": now - timedelta(days=2),
            "estimated_delivery": now,
            "delivered_at": None,
            "tracking_note": "Out for delivery with courier partner Vignesh",
            "items": [("Bluetooth Portable Speaker", 1, Decimal("1599.00"))],
        },
        {
            "order_number": "ORD-10009",
            "customer": customers[2],
            "status": "cancelled",
            "total_amount": Decimal("1100.00"),
            "placed_at": now - timedelta(days=5),
            "estimated_delivery": None,
            "delivered_at": None,
            "tracking_note": "Order cancelled prior to dispatch",
            "items": [("Handcrafted Leather Wallet", 1, Decimal("1100.00"))],
        },
        # Customer 4 (Suresh)
        {
            "order_number": "ORD-10010",
            "customer": customers[3],
            "status": "placed",
            "total_amount": Decimal("2999.00"),
            "placed_at": now - timedelta(hours=5),
            "estimated_delivery": now + timedelta(days=4),
            "delivered_at": None,
            "tracking_note": "Order confirmed and verified; awaiting warehouse dispatch",
            "items": [("Air Fryer 4.2L", 1, Decimal("2999.00"))],
        },
        {
            "order_number": "ORD-10011",
            "customer": customers[3],
            "status": "delivered",
            "total_amount": Decimal("1800.00"),
            "placed_at": now - timedelta(days=18),
            "estimated_delivery": now - timedelta(days=14),
            "delivered_at": now - timedelta(days=14),
            "tracking_note": "Delivered",
            "items": [("Men Formal Blazer", 1, Decimal("1800.00"))],
        },
        # Customer 5 (Deepa)
        {
            "order_number": "ORD-10012",
            "customer": customers[4],
            "status": "delivered",
            "total_amount": Decimal("2000.00"),
            "placed_at": now - timedelta(days=5),
            "estimated_delivery": now - timedelta(days=3),
            "delivered_at": now - timedelta(days=3),
            "tracking_note": "Delivered to resident",
            "items": [("Silk Sarees Handloom", 1, Decimal("2000.00"))],
        },
    ]

    orders = []
    for o_info in orders_data:
        order = Order(
            id=uuid.uuid4(),
            order_number=o_info["order_number"],
            customer_id=o_info["customer"].id,
            status=o_info["status"],
            total_amount=o_info["total_amount"],
            placed_at=o_info["placed_at"],
            estimated_delivery=o_info["estimated_delivery"],
            delivered_at=o_info["delivered_at"],
            tracking_note=o_info["tracking_note"],
        )
        session.add(order)
        orders.append(order)

        for item_name, qty, price in o_info["items"]:
            item = OrderItem(
                id=uuid.uuid4(),
                order_id=order.id,
                product_name=item_name,
                quantity=qty,
                unit_price=price,
            )
            session.add(item)

        if o_info.get("has_refund"):
            refund = Refund(
                id=uuid.uuid4(),
                order_id=order.id,
                customer_id=o_info["customer"].id,
                amount=o_info["total_amount"],
                status=o_info["refund_status"],
                reason=o_info["refund_reason"],
                decided_by="auto_rule_threshold",
            )
            session.add(refund)

    await session.commit()

    print("\n" + "=" * 60)
    print("DEMO SEED COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("\nDEMO CUSTOMERS:")
    for c in customers:
        print(f"  • ID: {c.id}")
        print(f"    Name: {c.name} | Phone: {c.phone} | Lang: {c.preferred_language}")

    print("\nDEMO ORDERS:")
    for o in orders:
        print(
            f"  • Order: {o.order_number:<10} Status: {o.status:<18} Amount: ₹{o.total_amount:<8} (Customer ID: {o.customer_id})"
        )
    print("=" * 60 + "\n")


async def main():
    async with async_session_factory() as session:
        await seed_data(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
