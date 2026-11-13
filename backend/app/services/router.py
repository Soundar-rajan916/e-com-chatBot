import json
import logging
from typing import Any

from pydantic import ValidationError

from app.config import Settings, get_settings
from app.prompts import ROUTER_SYSTEM_PROMPT
from app.schemas import RouterOutput
from app.services.llm import GroqLLMClient, LLMResponse

logger = logging.getLogger("app.services.router")


async def classify_message(
    llm_client: GroqLLMClient,
    message: str,
    history: list[dict[str, str]],
    settings: Settings | None = None,
) -> tuple[RouterOutput, dict[str, Any], LLMResponse, str | None]:
    """
    Classify the incoming message's intent and language with fallback handling.

    Returns:
        (router_output, raw_dict, llm_response, error_message)
    """
    current_settings = settings or get_settings()
    model = current_settings.ROUTER_MODEL

    history_formatted = []
    for turn in history:
        history_formatted.append({"role": turn["role"], "content": turn["content"]})

    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        *history_formatted,
        {"role": "user", "content": message},
    ]

    last_error: str | None = None
    last_llm_response: LLMResponse | None = None
    raw_dict: dict[str, Any] = {}

    # Up to 2 attempts (initial + 1 retry on invalid JSON)
    for attempt in range(2):
        try:
            llm_response = await llm_client.chat_completion(
                messages=messages,
                model=model,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            last_llm_response = llm_response

            try:
                raw_dict = json.loads(llm_response.content)
            except json.JSONDecodeError as jde:
                last_error = f"Invalid JSON on attempt {attempt + 1}: {jde}"
                logger.warning(last_error)
                continue

            router_output = RouterOutput.model_validate(raw_dict)
            return router_output, raw_dict, llm_response, None

        except (ValidationError, Exception) as exc:
            last_error = f"Router classification error on attempt {attempt + 1}: {exc}"
            logger.warning(last_error)

    # Fallback if both attempts fail:
    fallback_output = RouterOutput(
        intent="escalate",
        language="en",
        order_number=None,
        refund_reason=None,
    )
    if last_llm_response is None:
        last_llm_response = LLMResponse(
            content="{}",
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            cost_inr=0,  # type: ignore[arg-type]
            latency_ms=0,
        )

    return fallback_output, raw_dict, last_llm_response, last_error
