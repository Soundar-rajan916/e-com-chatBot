"""Policy inquiry prompt instructions and structured schemas."""

POLICY_PROMPT_SECTION = """
FOR POLICY QUESTIONS:
1. Answer directly and factually using ONLY the retrieved policy sections in the tool result.
2. Quote exact figures from the policy (e.g. 7-day return window, ₹2,000 instant refund limit, 5 to 7 business days timeline, standard delivery 3-5 days, express 1-2 days).
3. If no relevant policy is found in the tool result, politely state that you could not find the policy details and offer escalation.
4. Output structure:
   - In "headline": "Store Policy: <Topic>" (e.g. "Return Policy", "Shipping & Delivery")
   - In "reply": The detailed, clear explanation in the target language.
   - In "suggested_actions": Relevant suggestions (e.g. ["Return Window Details", "Payment Options", "Track My Order"]).
   - In "data": Set "topics": list of detected topics, "key_points": list of brief bullet points.
"""
