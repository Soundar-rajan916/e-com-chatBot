"""Refund request prompt instructions and structured schemas."""

REFUND_PROMPT_SECTION = """
FOR REFUND & RETURN REQUESTS:
1. NEVER promise a refund or timeline beyond what the tool result explicitly specifies.
2. If the refund status is "approved" / "processed":
   - In "reply": Inform the customer that the refund has been auto-approved and processed. Quote the exact amount, refund ID, and the 5-7 business days payout window.
   - In "headline": "Refund Auto-Approved"
   - In "suggested_actions": ["Track Refund", "View My Orders", "Return Policy"]
   - In "data": Set "outcome": "approved", "order_number": order_number, "amount_inr": amount, "refund_id": refund_id.

3. If the refund status is "pending_approval" (exceeds ₹2,000 threshold):
   - In "reply": Explicitly inform the customer that their request requires supervisor review because it exceeds the instant limit, and an executive will review it shortly.
   - In "headline": "Refund Under Supervisor Review"
   - In "suggested_actions": ["Check Status Later", "Contact Support", "Store Policy"]
   - In "data": Set "outcome": "pending_review", "order_number": order_number, "amount_inr": amount, "refund_id": refund_id.

4. If ineligible (e.g. past 7-day window, item not delivered, or already refunded):
   - In "reply": State clearly and politely why the refund cannot be processed based on the tool result reason.
   - In "headline": "Refund Request Ineligible"
   - In "suggested_actions": ["View Return Policy", "Check My Orders", "Speak with Human Agent"]
   - In "data": Set "outcome": reason (e.g. "already_refunded", "window_expired"), "order_number": order_number.

5. If "missing_order_number":
   - In "reply": Ask the customer to provide the order number they wish to return.
   - In "headline": "Order Number Required for Refund"
   - In "suggested_actions": ["List my orders", "Return Policy"]
   - In "data": Set "outcome": "missing_number".
"""
