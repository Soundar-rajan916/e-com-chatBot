import json
import logging
from typing import Any

from app.config import Settings, get_settings
from app.prompts import build_generator_prompt
from app.schemas import StructuredGeneratorOutput
from app.services.llm import GroqLLMClient, LLMResponse

logger = logging.getLogger("app.services.generator")


async def generate_response(
    llm_client: GroqLLMClient,
    user_message: str,
    language: str,
    tool_result: dict[str, Any],
    history: list[dict[str, str]],
    intent: str | None = None,
    settings: Settings | None = None,
) -> tuple[StructuredGeneratorOutput, LLMResponse]:
    """
    Generate customer-facing response using the generator model.
    Enforces factual grounding on tool_result, matching of target language,
    and returns a validated StructuredGeneratorOutput with suggested_actions.
    """
    current_settings = settings or get_settings()
    model = current_settings.GENERATOR_MODEL

    system_prompt = build_generator_prompt(language=language, intent=intent)

    history_formatted = []
    for turn in history:
        history_formatted.append({"role": turn["role"], "content": turn["content"]})

    # Prepare structured context for the assistant
    tool_context = json.dumps(tool_result, ensure_ascii=False, indent=2)
    user_content = (
        f"<customer_message>\n{user_message}\n</customer_message>\n\n"
        f"<structured_tool_result>\n{tool_context}\n</structured_tool_result>\n\n"
        f"Respond to the customer message strictly following the required JSON schema in {language}."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        *history_formatted,
        {"role": "user", "content": user_content},
    ]

    llm_response = await llm_client.chat_completion(
        messages=messages,
        model=model,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    raw_text = llm_response.content.strip()

    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            reply = parsed.get("reply") or parsed.get("message") or parsed.get("text") or raw_text
            headline = parsed.get("headline")
            raw_actions = parsed.get("suggested_actions")
            suggested_actions = [str(a) for a in raw_actions] if isinstance(raw_actions, list) else []
            data = parsed.get("data") if isinstance(parsed.get("data"), dict) else tool_result

            structured_output = StructuredGeneratorOutput(
                headline=headline,
                reply=str(reply).strip(),
                suggested_actions=suggested_actions,
                data=data,
            )
        else:
            structured_output = StructuredGeneratorOutput(
                headline=None,
                reply=str(parsed).strip(),
                suggested_actions=[],
                data=tool_result,
            )
    except Exception as exc:
        logger.warning("Could not parse generator output as JSON (%s). Falling back to raw text.", exc)
        structured_output = StructuredGeneratorOutput(
            headline=None,
            reply=raw_text,
            suggested_actions=[],
            data=tool_result,
        )

    return structured_output, llm_response
