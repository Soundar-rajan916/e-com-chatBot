"""Order status and order listing prompt instructions and structured schemas."""

ORDER_STATUS_PROMPT_SECTION = """
FOR ORDER STATUS & ORDER LISTING:
1. If the tool result contains "found_orders" (multiple orders):
   - In "reply": ALWAYS format the customer's orders as a clean Markdown table with headers:
     | Order # | Item(s) | Total (₹) | Placed On | Delivered On | Status | Refund Status |
     Do NOT use 4-space indentation, blockquotes, or code blocks. List the most recent orders at the top. Ask which order they would like help with.
   - In "headline": "Your Recent Orders"
   - In "suggested_actions": Provide quick-reply chips for the order numbers (e.g. ["Details for ORD-10001", "Return ORD-10001"]).
   - In "data": Set "view_type": "order_list" and "orders": array of order objects with fields [order_number, status, total_amount, placed_at, delivered_at, refund_status, items].

2. If the tool result contains a single found order:
   - In "reply": Clearly state order status, placement date, delivery date/estimate, courier tracking note, total amount, and items.
   - If "refund_status" is present in tool result, explicitly inform the customer about both delivery status and refund status (e.g. "Delivered, and a refund of ₹... has been processed / is pending").
   - In "headline": "Order <order_number> Status"
   - In "suggested_actions": Provide relevant follow-ups (e.g. ["Request Refund for <order_number>", "Check Return Policy", "Browse More Products"]).
   - In "data": Set "view_type": "single_order" and include the order details.

3. If "status" is "missing_order_number":
   - In "reply": Politely ask the customer to share their order number.
   - In "headline": "Order Number Required"
   - In "suggested_actions": ["What are my orders", "Return Policy"]
   - In "data": Set "view_type": "missing_number".

4. If "status" is "not_found":
   - In "reply": Politely inform the customer that the order could not be found under their account.
   - In "headline": "Order Not Found"
   - In "suggested_actions": ["List my orders", "Speak with Human Agent"]
   - In "data": Set "view_type": "not_found".
"""
