from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, Escalation, Order, Trace
from app.prompts import FALLBACK_REPLY_EN_TA
from app.services.pipeline import handle_message
from app.services.tools import get_order_status
from tests.conftest import FakeGroqClient


@pytest.mark.asyncio
async def test_order_belonging_to_another_customer_leaks_nothing(db_session: AsyncSession):
    c1 = Customer(name="Customer 1", phone="+919999999011", preferred_language="en")
    c2 = Customer(name="Customer 2", phone="+919999999012", preferred_language="en")
    db_session.add_all([c1, c2])
    await db_session.flush()

    order = Order(
        order_number="ORD-PRIVATE-99",
        customer_id=c1.id,
        status="delivered",
        total_amount=Decimal("1500.00"),
        placed_at=datetime.now(UTC),
    )
    db_session.add(order)
    await db_session.commit()

    # C2 queries C1's order
    res_other = await get_order_status(db_session, c2.id, "ORD-PRIVATE-99")
    # Nonexistent order query
    res_nonexistent = await get_order_status(db_session, c2.id, "ORD-DOES-NOT-EXIST")

    assert res_other["status"] == "not_found"
    assert res_nonexistent["status"] == "not_found"
    assert res_other["message"] == res_nonexistent["message"]


@pytest.mark.asyncio
async def test_router_invalid_json_triggers_retry_then_fallback(db_session: AsyncSession):
    customer = Customer(name="Retry User", phone="+919999999013", preferred_language="en")
    db_session.add(customer)
    await db_session.commit()

    fake_groq = FakeGroqClient()
    # Attempt 1: Invalid JSON
    fake_groq.enqueue_router("THIS IS NOT VALID JSON")
    # Attempt 2: Still invalid JSON
    fake_groq.enqueue_router("{broken json:}")
    fake_groq.enqueue_generator("I will connect you to a human executive.")

    response = await handle_message(
        session=db_session,
        customer_id=customer.id,
        session_id=None,
        text="I need help with my account",
        llm_client=fake_groq,
    )

    assert response.intent == "escalate"
    assert response.requires_human is True

    # Check trace was written with error
    trace = await db_session.get(Trace, response.trace_id)
    assert trace is not None
    assert trace.intent == "escalate"
    assert "Invalid JSON" in (trace.error or "") or "Router classification error" in (trace.error or "")


@pytest.mark.asyncio
async def test_llm_total_failure_safe_fallback(db_session: AsyncSession):
    customer = Customer(name="Fail User", phone="+919999999014", preferred_language="en")
    db_session.add(customer)
    await db_session.commit()

    fake_groq = FakeGroqClient()
    fake_groq.fail_all = True

    response = await handle_message(
        session=db_session,
        customer_id=customer.id,
        session_id=None,
        text="Order status check",
        llm_client=fake_groq,
    )

    assert response.reply == FALLBACK_REPLY_EN_TA
    assert response.requires_human is True

    # Check escalation was created
    esc_stmt = select(Escalation).where(Escalation.session_id == response.session_id)
    escalation = (await db_session.execute(esc_stmt)).scalar_one_or_none()
    assert escalation is not None
    assert "escalation" in escalation.reason.lower() or "llm failure" in escalation.reason.lower()

    # Check trace was written
    trace = await db_session.get(Trace, response.trace_id)
    assert trace is not None
    assert trace.error is not None
    assert "Generator fatal error" in trace.error


@pytest.mark.asyncio
async def test_missing_order_number_clarifying_question(db_session: AsyncSession):
    customer = Customer(name="Clarify User", phone="+919999999015", preferred_language="en")
    db_session.add(customer)
    await db_session.commit()

    fake_groq = FakeGroqClient()
    fake_groq.enqueue_router(
        '{"intent": "order_status", "language": "en", "order_number": null, "refund_reason": null}'
    )
    fake_groq.enqueue_generator("Could you please provide your order number?")

    response = await handle_message(
        session=db_session,
        customer_id=customer.id,
        session_id=None,
        text="Where is my order?",
        llm_client=fake_groq,
    )

    assert response.intent == "order_status"
    assert "order number" in response.reply.lower()

    trace = await db_session.get(Trace, response.trace_id)
    assert trace is not None
    # Verify tool calls indicate missing_order_number and no DB query executed
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0]["output"]["status"] == "missing_order_number"


@pytest.mark.asyncio
async def test_list_customer_orders_when_no_order_number_provided(db_session: AsyncSession):
    customer = Customer(name="List User", phone="+919999999018", preferred_language="en")
    db_session.add(customer)
    await db_session.flush()

    order = Order(
        order_number="ORD-TEST-LIST-01",
        customer_id=customer.id,
        status="delivered",
        total_amount=Decimal("1200.00"),
        placed_at=datetime.now(UTC),
    )
    db_session.add(order)
    await db_session.commit()

    fake_groq = FakeGroqClient()
    fake_groq.enqueue_router(
        '{"intent": "order_status", "language": "en", "order_number": null, "refund_reason": null}'
    )
    fake_groq.enqueue_generator("Here are your recent orders: ORD-TEST-LIST-01")

    response = await handle_message(
        session=db_session,
        customer_id=customer.id,
        session_id=None,
        text="what are my orders",
        llm_client=fake_groq,
    )

    assert response.intent == "order_status"
    assert "ORD-TEST-LIST-01" in response.reply

    trace = await db_session.get(Trace, response.trace_id)
    assert trace is not None
    assert trace.tool_calls[0]["tool"] == "list_customer_orders"
    assert trace.tool_calls[0]["output"]["status"] == "found_orders"


@pytest.mark.asyncio
async def test_trace_recorded_with_tokens_and_cost(db_session: AsyncSession):
    customer = Customer(name="Trace User", phone="+919999999016", preferred_language="en")
    db_session.add(customer)
    await db_session.commit()

    fake_groq = FakeGroqClient()
    fake_groq.enqueue_router(
        '{"intent": "smalltalk", "language": "en", "order_number": null, "refund_reason": null}'
    )
    fake_groq.enqueue_generator("Hello! How can I help you today?")

    response = await handle_message(
        session=db_session,
        customer_id=customer.id,
        session_id=None,
        text="Hello",
        llm_client=fake_groq,
    )

    trace = await db_session.get(Trace, response.trace_id)
    assert trace is not None
    assert trace.prompt_tokens > 0
    assert trace.completion_tokens > 0
    assert trace.cost_inr > Decimal("0.0000")
    assert trace.latency_ms >= 0


@pytest.mark.asyncio
async def test_router_language_passthrough_to_generator(db_session: AsyncSession):
    customer = Customer(name="Lang User", phone="+919999999017", preferred_language="ta")
    db_session.add(customer)
    await db_session.commit()

    for lang, user_text in [("ta", "வணக்கம்"), ("tanglish", "vanakkam bro"), ("en", "hello")]:
        fake_groq = FakeGroqClient()
        fake_groq.enqueue_router(
            f'{{"intent": "smalltalk", "language": "{lang}", "order_number": null, "refund_reason": null}}'
        )
        fake_groq.enqueue_generator(f"Reply in {lang}")

        res = await handle_message(
            session=db_session,
            customer_id=customer.id,
            session_id=None,
            text=user_text,
            llm_client=fake_groq,
        )

        assert res.language == lang
        # Verify generator call was invoked with system prompt mentioning that language
        gen_call = fake_groq.call_history[-1]
        assert f"Detected customer language: {lang}" in gen_call["messages"][0]["content"]
