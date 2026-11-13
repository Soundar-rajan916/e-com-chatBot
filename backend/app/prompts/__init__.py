"""Modular prompt directory for router, generator, and fallback templates."""

from app.prompts.escalation import ESCALATION_PROMPT_SECTION
from app.prompts.fallback import FALLBACK_REPLY_EN_TA
from app.prompts.generator_base import GENERATOR_BASE_SYSTEM_PROMPT
from app.prompts.order_status import ORDER_STATUS_PROMPT_SECTION
from app.prompts.policy import POLICY_PROMPT_SECTION
from app.prompts.product import PRODUCT_PROMPT_SECTION
from app.prompts.refund import REFUND_PROMPT_SECTION
from app.prompts.router import ROUTER_SYSTEM_PROMPT
from app.prompts.smalltalk import SMALLTALK_PROMPT_SECTION

INTENT_SECTIONS = {
    "order_status": ORDER_STATUS_PROMPT_SECTION,
    "refund_request": REFUND_PROMPT_SECTION,
    "policy_question": POLICY_PROMPT_SECTION,
    "product_question": PRODUCT_PROMPT_SECTION,
    "escalate": ESCALATION_PROMPT_SECTION,
    "smalltalk": SMALLTALK_PROMPT_SECTION,
}

GENERATOR_SYSTEM_PROMPT = (
    GENERATOR_BASE_SYSTEM_PROMPT
    + "\n"
    + ORDER_STATUS_PROMPT_SECTION
    + "\n"
    + REFUND_PROMPT_SECTION
    + "\n"
    + POLICY_PROMPT_SECTION
    + "\n"
    + PRODUCT_PROMPT_SECTION
    + "\n"
    + ESCALATION_PROMPT_SECTION
    + "\n"
    + SMALLTALK_PROMPT_SECTION
)


def build_generator_prompt(language: str, intent: str | None = None) -> str:
    """Constructs a targeted or full generator system prompt."""
    base = GENERATOR_BASE_SYSTEM_PROMPT.format(language=language)
    if intent and intent in INTENT_SECTIONS:
        return f"{base}\n\n{INTENT_SECTIONS[intent]}"
    all_sections = "\n".join(INTENT_SECTIONS.values())
    return f"{base}\n\n{all_sections}"


__all__ = [
    "ROUTER_SYSTEM_PROMPT",
    "GENERATOR_BASE_SYSTEM_PROMPT",
    "GENERATOR_SYSTEM_PROMPT",
    "FALLBACK_REPLY_EN_TA",
    "ORDER_STATUS_PROMPT_SECTION",
    "REFUND_PROMPT_SECTION",
    "POLICY_PROMPT_SECTION",
    "PRODUCT_PROMPT_SECTION",
    "ESCALATION_PROMPT_SECTION",
    "SMALLTALK_PROMPT_SECTION",
    "build_generator_prompt",
]
