import asyncio
import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.config import get_settings
from app.db import async_session_factory, engine
from app.models import (
    Agent,
    AgentSession,
    ChatMessage,
    ChatSession,
    Customer,
    Escalation,
    EscalationEvent,
    EscalationNote,
    Order,
    OrderItem,
    Refund,
    Trace,
)


async def seed_data(session: AsyncSession) -> None:
    settings = get_settings()

    # Clean existing data in dependency order
    for model in [
        EscalationNote,
        EscalationEvent,
        Escalation,
        Trace,
        ChatMessage,
        ChatSession,
        Refund,
        OrderItem,
        Order,
        AgentSession,
        Agent,
        Customer,
    ]:
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
            "has_refund": True,
            "refund_status": "processed",
            "refund_reason": "already_refunded",
        },
        {
            "order_number": "ORD-10002",
            "customer": customers[0],
            "status": "delivered",
            "total_amount": Decimal("3499.00"),
            "placed_at": now - timedelta(days=7),
            "estimated_delivery": now - timedelta(days=3),
            "delivered_at": now - timedelta(days=3),
            "tracking_note": "Delivered to security gate",
            "items": [("Wireless Noise-Cancelling Headphones", 1, Decimal("3499.00"))],
            "has_refund": True,
            "refund_status": "pending_approval",
            "refund_reason": "Defective item sound distortion - amount exceeds 2000 INR limit",
        },
        {
            "order_number": "ORD-10003",
            "customer": customers[0],
            "status": "delivered",
            "total_amount": Decimal("899.00"),
            "placed_at": now - timedelta(days=25),
            "estimated_delivery": now - timedelta(days=20),
            "delivered_at": now - timedelta(days=20),
            "tracking_note": "Delivered to customer",
            "items": [("Ceramic Coffee Mug Set", 1, Decimal("899.00"))],
            "has_refund": False,
        },
        # Customer 2 (Karthik)
        {
            "order_number": "ORD-10004",
            "customer": customers[1],
            "status": "delivered",
            "total_amount": Decimal("1299.00"),
            "placed_at": now - timedelta(days=3),
            "estimated_delivery": now - timedelta(days=1),
            "delivered_at": now - timedelta(days=1),
            "tracking_note": "வீட்டு வாசலில் ஒப்படைக்கப்பட்டது (Left at doorstep)",
            "items": [("Pure Linen Casual Shirt", 1, Decimal("1299.00"))],
            "has_refund": False,
        },
        {
            "order_number": "ORD-10005",
            "customer": customers[1],
            "status": "delivered",
            "total_amount": Decimal("4500.00"),
            "placed_at": now - timedelta(days=4),
            "estimated_delivery": now - timedelta(days=1),
            "delivered_at": now - timedelta(days=1),
            "tracking_note": "Signed by Karthik",
            "items": [("Smart Fitness Watch", 1, Decimal("4500.00"))],
            "has_refund": True,
            "refund_status": "pending_approval",
            "refund_reason": "High-value return request - fitness watch screen malfunction (₹4,500)",
        },
        {
            "order_number": "ORD-10006",
            "customer": customers[1],
            "status": "shipped",
            "total_amount": Decimal("2199.00"),
            "placed_at": now - timedelta(days=2),
            "estimated_delivery": now + timedelta(days=2),
            "delivered_at": None,
            "tracking_note": "In transit from Chennai Hub via BlueDart",
            "items": [("Bluetooth Party Speaker", 1, Decimal("2199.00"))],
            "has_refund": False,
        },
        # Customer 3 (Ananya)
        {
            "order_number": "ORD-10007",
            "customer": customers[2],
            "status": "delivered",
            "total_amount": Decimal("850.00"),
            "placed_at": now - timedelta(days=2),
            "estimated_delivery": now - timedelta(days=1),
            "delivered_at": now - timedelta(days=1),
            "tracking_note": "Delivered to neighbor Mrs. Vani",
            "items": [("Silver Oxidised Jhumkas", 1, Decimal("850.00"))],
            "has_refund": False,
        },
        {
            "order_number": "ORD-10008",
            "customer": customers[2],
            "status": "out_for_delivery",
            "total_amount": Decimal("1599.00"),
            "placed_at": now - timedelta(days=3),
            "estimated_delivery": now,
            "delivered_at": None,
            "tracking_note": "With courier agent Murugan (Ph: 9840123456)",
            "items": [("Stainless Steel Air Fryer Basket", 1, Decimal("1599.00"))],
            "has_refund": False,
        },
        {
            "order_number": "ORD-10009",
            "customer": customers[2],
            "status": "cancelled",
            "total_amount": Decimal("1100.00"),
            "placed_at": now - timedelta(days=6),
            "estimated_delivery": now - timedelta(days=3),
            "delivered_at": None,
            "tracking_note": "Cancelled by user before dispatch",
            "items": [("Handcrafted Clay Water Bottle", 2, Decimal("550.00"))],
            "has_refund": False,
        },
        # Customer 4 (Suresh)
        {
            "order_number": "ORD-10010",
            "customer": customers[3],
            "status": "placed",
            "total_amount": Decimal("2999.00"),
            "placed_at": now - timedelta(hours=4),
            "estimated_delivery": now + timedelta(days=3),
            "delivered_at": None,
            "tracking_note": "Order packed and waiting for courier pickup",
            "items": [("Traditional Brass Pooja Set", 1, Decimal("2999.00"))],
            "has_refund": False,
        },
        {
            "order_number": "ORD-10011",
            "customer": customers[3],
            "status": "delivered",
            "total_amount": Decimal("1800.00"),
            "placed_at": now - timedelta(days=30),
            "estimated_delivery": now - timedelta(days=26),
            "delivered_at": now - timedelta(days=26),
            "tracking_note": "Delivered",
            "items": [("Men Embroidered Kurta Pajama", 1, Decimal("1800.00"))],
            "has_refund": False,
        },
        # Customer 5 (Deepa)
        {
            "order_number": "ORD-10012",
            "customer": customers[4],
            "status": "delivered",
            "total_amount": Decimal("2001.00"),
            "placed_at": now - timedelta(days=5),
            "estimated_delivery": now - timedelta(days=3),
            "delivered_at": now - timedelta(days=3),
            "tracking_note": "Delivered to resident",
            "items": [("Silk Sarees Handloom", 1, Decimal("2001.00"))],
            "has_refund": False,
        },
    ]

    orders = []
    pending_refund_escalations = []

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
                decided_by="auto_rule_threshold" if o_info["refund_status"] == "processed" else None,
            )
            session.add(refund)

            if o_info["refund_status"] == "pending_approval":
                # Create demo session & high-priority escalation for this pending refund
                chat_sess = ChatSession(
                    id=uuid.uuid4(),
                    customer_id=o_info["customer"].id,
                    channel="web",
                    created_at=o_info["placed_at"],
                )
                session.add(chat_sess)

                # Customer message in transcript
                cust_msg = ChatMessage(
                    id=uuid.uuid4(),
                    session_id=chat_sess.id,
                    role="user",
                    content=f"I want a refund for {order.order_number}. It is defective.",
                    created_at=now - timedelta(hours=2),
                )
                bot_msg = ChatMessage(
                    id=uuid.uuid4(),
                    session_id=chat_sess.id,
                    role="assistant",
                    content=(
                        f"Your refund request for order {order.order_number} (₹{order.total_amount}) requires "
                        "supervisor review because it exceeds ₹2,000."
                    ),
                    created_at=now - timedelta(hours=2) + timedelta(seconds=2),
                )
                session.add_all([cust_msg, bot_msg])

                esc = Escalation(
                    id=uuid.uuid4(),
                    session_id=chat_sess.id,
                    customer_id=o_info["customer"].id,
                    reason=f"Refund approval required for {order.order_number} (₹{order.total_amount})",
                    reason_type="refund_pending_approval",
                    status="open",
                    priority="high",
                    refund_id=refund.id,
                    version=1,
                    created_at=now - timedelta(hours=2),
                    updated_at=now - timedelta(hours=2),
                )
                session.add(esc)

                event = EscalationEvent(
                    id=uuid.uuid4(),
                    escalation_id=esc.id,
                    actor_type="system",
                    actor_id=None,
                    action="created",
                    detail={"reason_type": "refund_pending_approval", "order_number": order.order_number},
                    created_at=now - timedelta(hours=2),
                )
                session.add(event)
                pending_refund_escalations.append(esc)

    # 3. Create demo admin and demo agent if in dev mode
    demo_admins = []
    if settings.APP_ENV == "dev":
        admin_agent = Agent(
            id=uuid.uuid4(),
            email="admin@example.com",
            name="Admin Executive",
            password_hash=hash_password("AdminPass123!"),
            role="admin",
            is_active=True,
        )
        support_agent = Agent(
            id=uuid.uuid4(),
            email="agent@example.com",
            name="Regional Support Agent",
            password_hash=hash_password("AgentPass123!"),
            role="agent",
            is_active=True,
        )
        session.add_all([admin_agent, support_agent])
        demo_admins.extend([admin_agent, support_agent])
        await session.flush()

        # 4. Seed diverse cases covering every reason_type, overdue SLA, in_progress with replies, and resolved
        # Case A: Overdue Open Case (router_fallback) - created 35 min ago
        sess_overdue = ChatSession(id=uuid.uuid4(), customer_id=customers[2].id, channel="web", created_at=now - timedelta(minutes=35))
        session.add(sess_overdue)
        m_overdue = ChatMessage(session_id=sess_overdue.id, role="user", content="delivery address change panna mudiyuma?", created_at=now - timedelta(minutes=35))
        session.add(m_overdue)
        esc_overdue = Escalation(
            id=uuid.uuid4(),
            session_id=sess_overdue.id,
            customer_id=customers[2].id,
            reason="Router fallback: ambiguous address modification intent",
            reason_type="router_fallback",
            status="open",
            priority="normal",
            version=1,
            created_at=now - timedelta(minutes=35),
            updated_at=now - timedelta(minutes=35),
        )
        session.add(esc_overdue)
        session.add(EscalationEvent(
            escalation_id=esc_overdue.id,
            actor_type="system",
            actor_id=None,
            action="created",
            detail={"reason_type": "router_fallback", "sla_minutes": 15},
            created_at=now - timedelta(minutes=35),
        ))

        # Case B: In-Progress Case with Agent Replies (llm_failure) - assigned to support_agent
        sess_inprog = ChatSession(id=uuid.uuid4(), customer_id=customers[3].id, channel="web", created_at=now - timedelta(minutes=25))
        session.add(sess_inprog)
        m_inprog_u = ChatMessage(session_id=sess_inprog.id, role="user", content="My payment went through twice for ORD-10011", created_at=now - timedelta(minutes=25))
        m_inprog_a = ChatMessage(session_id=sess_inprog.id, role="agent", agent_id=support_agent.id, content="Vanakkam Suresh, checking bank gateway logs for the duplicate charge now.", created_at=now - timedelta(minutes=10))
        session.add_all([m_inprog_u, m_inprog_a])
        esc_inprog = Escalation(
            id=uuid.uuid4(),
            session_id=sess_inprog.id,
            customer_id=customers[3].id,
            reason="LLM failure fallback: double charge inquiry",
            reason_type="llm_failure",
            status="in_progress",
            priority="normal",
            assigned_to=support_agent.id,
            first_response_at=now - timedelta(minutes=10),
            version=2,
            created_at=now - timedelta(minutes=25),
            updated_at=now - timedelta(minutes=10),
        )
        session.add(esc_inprog)
        session.add(EscalationEvent(
            escalation_id=esc_inprog.id,
            actor_type="system",
            actor_id=None,
            action="created",
            detail={"reason_type": "llm_failure"},
            created_at=now - timedelta(minutes=25),
        ))
        session.add(EscalationEvent(
            escalation_id=esc_inprog.id,
            actor_type="agent",
            actor_id=support_agent.id,
            action="assigned",
            detail={"assigned_to": str(support_agent.id)},
            created_at=now - timedelta(minutes=20),
        ))
        session.add(EscalationEvent(
            escalation_id=esc_inprog.id,
            actor_type="agent",
            actor_id=support_agent.id,
            action="replied",
            detail={"message_id": str(m_inprog_a.id)},
            created_at=now - timedelta(minutes=10),
        ))

        # Case C: Resolved Case (user_requested)
        sess_resolved = ChatSession(id=uuid.uuid4(), customer_id=customers[0].id, channel="web", created_at=now - timedelta(hours=1))
        session.add(sess_resolved)
        m_res_u = ChatMessage(session_id=sess_resolved.id, role="user", content="I want to speak with a human support agent.", created_at=now - timedelta(hours=1))
        m_res_a = ChatMessage(session_id=sess_resolved.id, role="agent", agent_id=admin_agent.id, content="Hi Priya, I have updated your delivery slot to evening 5-7 PM.", created_at=now - timedelta(minutes=45))
        session.add_all([m_res_u, m_res_a])
        esc_resolved = Escalation(
            id=uuid.uuid4(),
            session_id=sess_resolved.id,
            customer_id=customers[0].id,
            reason="Customer requested human executive handoff",
            reason_type="user_requested",
            status="resolved",
            priority="low",
            assigned_to=admin_agent.id,
            first_response_at=now - timedelta(minutes=45),
            resolved_at=now - timedelta(minutes=30),
            resolution_note="Delivery time window rescheduled to 5 PM - 7 PM as requested.",
            version=3,
            created_at=now - timedelta(hours=1),
            updated_at=now - timedelta(minutes=30),
        )
        session.add(esc_resolved)
        session.add(EscalationEvent(
            escalation_id=esc_resolved.id,
            actor_type="agent",
            actor_id=admin_agent.id,
            action="resolved",
            detail={"resolution_note": "Delivery time window rescheduled to 5 PM - 7 PM as requested."},
            created_at=now - timedelta(minutes=30),
        ))

        # Case D: Fresh User Requested Open Case
        sess_user_req = ChatSession(id=uuid.uuid4(), customer_id=customers[1].id, channel="web", created_at=now - timedelta(minutes=6))
        session.add(sess_user_req)
        m_user_req = ChatMessage(session_id=sess_user_req.id, role="user", content="Please connect me to human support agent", created_at=now - timedelta(minutes=6))
        session.add(m_user_req)
        esc_user_req = Escalation(
            id=uuid.uuid4(),
            session_id=sess_user_req.id,
            customer_id=customers[1].id,
            reason="Customer requested live human support",
            reason_type="user_requested",
            status="open",
            priority="normal",
            version=1,
            created_at=now - timedelta(minutes=6),
            updated_at=now - timedelta(minutes=6),
        )
        session.add(esc_user_req)
        session.add(EscalationEvent(
            escalation_id=esc_user_req.id,
            actor_type="system",
            actor_id=None,
            action="created",
            detail={"reason_type": "user_requested"},
            created_at=now - timedelta(minutes=6),
        ))

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

    if demo_admins:
        print("\nDEMO ADMIN & AGENT CREDENTIALS (dev environment only):")
        print("  • Email: admin@example.com")
        print("    Password: AdminPass123!  | Role: admin")
        print("  • Email: agent@example.com")
        print("    Password: AgentPass123!  | Role: agent")

    if pending_refund_escalations:
        print(f"\nSEEDED ACTIVE ESCALATIONS: {len(pending_refund_escalations)} high-priority case(s)")
        for esc in pending_refund_escalations:
            print(f"  • ID: {esc.id} | Reason: {esc.reason_type} | Priority: {esc.priority}")

    print("=" * 60 + "\n")


async def main():
    async with async_session_factory() as session:
        await seed_data(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
