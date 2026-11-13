import json

import pytest

from app.prompts import (
    build_generator_prompt,
)
from app.schemas import (
    OrderItemSummary,
    OrderStatusData,
    OrderSummary,
    ProductCard,
    ProductListData,
    RefundData,
    StructuredGeneratorOutput,
)
from app.services.generator import generate_response
from tests.conftest import FakeGroqClient


def test_build_generator_prompt_modular_sections():
    # Targeted prompts
    p_order = build_generator_prompt("en", "order_status")
    assert "ORDER STATUS & ORDER LISTING" in p_order
    assert "REFUND & RETURN" not in p_order

    p_refund = build_generator_prompt("ta", "refund_request")
    assert "REFUND & RETURN" in p_refund
    assert "language: ta" in p_refund

    # Full prompt fallback
    p_all = build_generator_prompt("tanglish")
    assert "ORDER STATUS & ORDER LISTING" in p_all
    assert "REFUND & RETURN" in p_all
    assert "POLICY QUESTIONS" in p_all
    assert "PRODUCT QUESTIONS" in p_all
    assert "ESCALATION" in p_all
    assert "SMALLTALK" in p_all


def test_structured_schemas_validation():
    # 1. Order status data
    item = OrderItemSummary(product_title="Silk Saree", quantity=2, unit_price_inr=1500)
    order = OrderSummary(
        order_number="ORD-10001",
        status="delivered",
        total_amount_inr=3000,
        items=[item],
    )
    status_data = OrderStatusData(single_order=order)
    assert status_data.single_order.order_number == "ORD-10001"

    # 2. Refund data
    refund = RefundData(
        order_number="ORD-10001",
        refund_id="REF-1234",
        status="auto_approved",
        amount_inr=1499,
        auto_approved=True,
    )
    assert refund.auto_approved is True

    # 3. Product data
    p = ProductCard(id="prod-1", title="Wireless Earbuds", price_inr=1999, in_stock=True)
    plist = ProductListData(products=[p], total_found=1, search_query="earbuds")
    assert len(plist.products) == 1

    # 4. StructuredGeneratorOutput
    out = StructuredGeneratorOutput(
        headline="Delivered",
        reply="Your order has arrived.",
        suggested_actions=["Track another order", "Need refund"],
        data={"order_number": "ORD-10001"},
    )
    assert out.headline == "Delivered"
    assert len(out.suggested_actions) == 2


@pytest.mark.asyncio
async def test_generate_response_parses_json_into_structured_output():
    fake_client = FakeGroqClient()
    mock_payload = {
        "headline": "Order ORD-10001 Delivered",
        "reply": "Your order ORD-10001 was delivered successfully to reception.",
        "suggested_actions": ["Request refund", "Check another order"],
        "data": {"order_number": "ORD-10001", "status": "delivered"},
    }
    fake_client.enqueue_generator(json.dumps(mock_payload))

    structured_out, resp = await generate_response(
        llm_client=fake_client,
        user_message="where is my order",
        language="en",
        tool_result={"status": "order_status", "order_number": "ORD-10001"},
        history=[],
        intent="order_status",
    )

    assert structured_out.headline == "Order ORD-10001 Delivered"
    assert structured_out.reply == "Your order ORD-10001 was delivered successfully to reception."
    assert "Request refund" in structured_out.suggested_actions
    assert structured_out.data.get("status") == "delivered"


@pytest.mark.asyncio
async def test_generate_response_handles_malformed_json_gracefully():
    fake_client = FakeGroqClient()
    raw_plain_text = "Here are your order details without valid JSON."
    fake_client.enqueue_generator(raw_plain_text)

    structured_out, resp = await generate_response(
        llm_client=fake_client,
        user_message="order status",
        language="en",
        tool_result={"order_number": "ORD-10001"},
        history=[],
    )

    assert structured_out.headline is None
    assert structured_out.reply == raw_plain_text
    assert structured_out.suggested_actions == []
    assert structured_out.data == {"order_number": "ORD-10001"}
