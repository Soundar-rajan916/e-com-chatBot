"""Product question prompt section for generator LLM."""

PRODUCT_PROMPT_SECTION = """
### PRODUCT QUESTIONS & SEARCH:
- Present matching products from the tool result clearly with their exact title, category, price in INR (e.g. ₹1,499), and in-stock status.
- If a product has stock_qty == 0 or is marked out of stock, explicitly inform the customer that it is currently out of stock.
- If no matching products were found, politely state this and suggest checking different keywords or broader categories.
- Include 2-3 relevant suggested_actions (e.g., ["Filter by price", "View top rated", "Ask for recommendations"]).
- Structured output should populate 'product_data' with the list of matching products (id, title, price_inr, in_stock, category).
"""
