import os

import pytest

from app.config import get_settings
from app.services.generator import generate_response
from app.services.llm import GroqLLMClient
from app.services.router import classify_message

RUN_LIVE = os.getenv("RUN_LIVE_LLM", "0") == "1"


@pytest.mark.skipif(not RUN_LIVE, reason="Live LLM tests skipped unless RUN_LIVE_LLM=1")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "language,message",
    [
        ("en", "Where is my order ORD-10001?"),
        ("ta", "என் ஆர்டர் ORD-10001 எங்கே உள்ளது?"),
        ("tanglish", "yen order ORD-10001 eppo varum bro?"),
    ],
)
async def test_live_groq_order_status_three_languages(language: str, message: str):
    settings = get_settings()
    client = GroqLLMClient(settings)

    # Test Router classification
    router_out, _, _, _ = await classify_message(client, message, [])
    assert router_out.intent == "order_status"
    assert router_out.language == language
    assert router_out.order_number == "ORD-10001"

    # Test Generator
    dummy_tool_result = {
        "status": "found",
        "order_number": "ORD-10001",
        "order_status": "delivered",
        "total_amount": "1499.00",
        "delivered_at": "2026-11-09T14:30:00Z",
    }
    reply, gen_resp = await generate_response(client, message, language, dummy_tool_result, [])
    assert len(reply) > 5
    assert gen_resp.prompt_tokens > 0
    assert gen_resp.completion_tokens > 0
