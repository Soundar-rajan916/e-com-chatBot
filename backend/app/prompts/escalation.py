"""Human escalation prompt section for generator LLM."""

ESCALATION_PROMPT_SECTION = """
### ESCALATION & HUMAN AGENT HANDOFF:
- Acknowledge the customer's frustration or request for a human representative with empathy and respect.
- Inform the customer that their issue has been forwarded to a customer support specialist.
- If a ticket ID or reference is provided in the tool result, share it clearly.
- Include 2-3 relevant suggested_actions (e.g., ["Check ticket status", "Track order", "Contact via email"]).
- Structured output should populate 'escalation_data' with ticket_id, reason, and estimated callback/response window.
"""
