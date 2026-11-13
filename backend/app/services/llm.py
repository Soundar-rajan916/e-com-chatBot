import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger("app.services.llm")


@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_inr: Decimal
    latency_ms: int
    raw_response: dict[str, Any] | None = None


class GroqLLMClient:
    """Async client wrapper for Groq's OpenAI-compatible HTTP chat completions endpoint."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.base_url = self.settings.GROQ_BASE_URL.rstrip("/")
        self.api_key = self.settings.GROQ_API_KEY
        self.timeout = self.settings.LLM_TIMEOUT_SECONDS
        self.max_retries = self.settings.LLM_MAX_RETRIES

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
        """Calculate the total call cost in INR based on token usage and model pricing."""
        if model == self.settings.ROUTER_MODEL:
            price_in = self.settings.PRICE_PER_1M_INPUT_TOKENS_USD_ROUTER
            price_out = self.settings.PRICE_PER_1M_OUTPUT_TOKENS_USD_ROUTER
        else:
            price_in = self.settings.PRICE_PER_1M_INPUT_TOKENS_USD_GENERATOR
            price_out = self.settings.PRICE_PER_1M_OUTPUT_TOKENS_USD_GENERATOR

        cost_usd = (Decimal(prompt_tokens) / Decimal(1_000_000) * price_in) + (
            Decimal(completion_tokens) / Decimal(1_000_000) * price_out
        )
        cost_inr = cost_usd * self.settings.USD_INR_RATE
        return Decimal(str(round(cost_inr, 4)))

    def _simulate_dev_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        response_format: dict[str, str] | None,
    ) -> LLMResponse:
        """Local simulated completion when GROQ_API_KEY is placeholder or invalid."""
        import json
        import re

        last_content = messages[-1].get("content", "")

        is_router = (
            model == self.settings.ROUTER_MODEL
            or "intent and language classifier" in messages[0].get("content", "").lower()
        )

        # 1. Router simulation
        if is_router:
            user_msg = last_content
            # Language detection
            is_ta = bool(re.search(r"[\u0B80-\u0BFF]", user_msg))
            tanglish_markers = [
                "irukka", "venum", "eppo", "vanakkam", "bro", "panringa",
                "illai", "kulla", "naal", "mudiyuma", "romba", "kooda", "enna", "sollunga"
            ]
            is_tanglish = any(w in user_msg.lower() for w in tanglish_markers)

            if is_ta:
                lang = "ta"
            elif is_tanglish:
                lang = "tanglish"
            else:
                lang = "en"

            msg_lower = user_msg.lower()
            m_ord = re.search(r"ORD-\d+", user_msg, re.IGNORECASE)
            order_number = m_ord.group(0).upper() if m_ord else None

            if any(w in msg_lower for w in ["human", "manager", "supervisor", "agent", "executive", "useless", "worst", "மனிதா", "அதிகாரி"]):
                intent = "escalate"
            elif any(w in msg_lower for w in ["policy", "window", "timeline", "cod", "limit", "damage", "rules", "cancel", "நாட்கள்", "விதிகள்", "ரத்து"]):
                intent = "policy_question"
            elif any(w in msg_lower for w in ["refund", "return", "ரீஃபண்ட்", "திருப்பி"]):
                intent = "refund_request"
            elif order_number or any(w in msg_lower for w in ["track", "status", "delivery", "parcel", "ஆர்டர்", "பார்சல்", "varum"]):
                intent = "order_status"
            elif any(w in msg_lower for w in ["kurti", "saree", "headphone", "speaker", "audio", "price", "buy", "specs", "available", "bottle", "fryer", "shoe", "watch", "dress", "விலை", "புடவை"]):
                intent = "product_question"
            elif any(w in msg_lower for w in ["hi", "hello", "hey", "vanakkam", "thanks", "thank", "வணக்கம்", "நன்றி"]):
                intent = "smalltalk"
            else:
                intent = "policy_question" if "?" in user_msg else "smalltalk"

            category = None
            for cat in ["Traditional & Ethnic Wear", "Electronics & Audio", "Kitchen & Home Appliances", "Footwear & Accessories", "Pooja & Spiritual Items"]:
                if any(w in msg_lower for w in cat.lower().split()):
                    category = cat
                    break

            m_price = re.search(r"(?:under|below|kulla|less than)?\s*₹?\s*(\d{3,5})", msg_lower)
            max_price = int(m_price.group(1)) if m_price else None

            sim_result = {
                "intent": intent,
                "language": lang,
                "order_number": order_number,
                "refund_reason": "Customer return request" if intent == "refund_request" else None,
                "search_query": user_msg if intent in ("policy_question", "product_question") else None,
                "category": category,
                "max_price_inr": max_price,
            }

            return LLMResponse(
                content=json.dumps(sim_result),
                model=model,
                prompt_tokens=150,
                completion_tokens=40,
                cost_inr=Decimal("0.0050"),
                latency_ms=15,
            )

        # 2. Generator simulation
        lang = "en"
        for m in messages:
            c = m.get("content", "")
            if "language: ta" in c or "Language: ta" in c:
                lang = "ta"
            elif "language: tanglish" in c or "Language: tanglish" in c:
                lang = "tanglish"

        # Parse structured tool result JSON from the prompt
        tool_data: dict[str, Any] = {}
        m_tool = re.search(
            r"<structured_tool_result>\s*(\{.*?\})\s*</structured_tool_result>",
            last_content,
            re.DOTALL,
        )
        if m_tool:
            try:
                tool_data = json.loads(m_tool.group(1))
            except Exception:
                tool_data = {}

        status = tool_data.get("status", "")

        if status == "smalltalk":
            if lang == "ta":
                reply = "வணக்கம்! நான் உங்கள் பிராந்திய மின்-வணிக உதவி உதவியாளர். ஆர்டர் நிலை, ரீஃபண்டுகள் அல்லது தயாரிப்புகள் பற்றி நீங்கள் கேட்கலாம். இன்று நான் உங்களுக்கு எப்படி உதவட்டும்?"
            elif lang == "tanglish":
                reply = "Vanakkam! Unga orders track panna, refunds apply panna, or products paarka naan help panren. Enna help venum sollunga?"
            else:
                reply = "Hello! Welcome to our store support. I can assist you with order status, returns & refunds, store policies, or finding products in our catalog. How can I help you today?"

        elif status == "missing_order_number":
            if lang == "ta":
                reply = "உங்கள் ஆர்டர் விவரங்களைச் சரிபார்க்க, தயவுசெய்து உங்கள் ஆர்டர் எண்ணைத் (எ.கா: ORD-10001) குறிப்பிடவும்."
            elif lang == "tanglish":
                reply = "Unga order check panna, please unga order number (example: ORD-10001) sollunga."
            else:
                reply = "Could you please provide your order number (e.g., ORD-10001) so I can retrieve your order details?"

        elif status == "not_found":
            ord_num = tool_data.get("order_number", "specified")
            if lang == "ta":
                reply = f"மன்னிக்கவும், உங்கள் கணக்கின் கீழ் {ord_num} என்ற ஆர்டர் எண் காணப்படவில்லை. தயவுசெய்து சரியான ஆர்டர் எண்ணைச் சரிபார்க்கவும்."
            elif lang == "tanglish":
                reply = f"Sorry, unga account la {ord_num} order number kidaikala. Please correct order number check panni sollunga."
            else:
                reply = f"We could not find order {ord_num} under your account. Please check the order number and try again."

        elif status == "order_status":
            ord_num = tool_data.get("order_number", "")
            ord_st = tool_data.get("order_status", "")
            note = tool_data.get("tracking_note", "")
            amt = tool_data.get("total_amount", "")
            items_desc = ", ".join(i.get("product_name", "") for i in tool_data.get("items", []))

            if ord_st == "delivered":
                if lang == "ta":
                    reply = f"உங்கள் ஆர்டர் {ord_num} ({items_desc}) ₹{amt} வெற்றிகரமாக டெலிவரி செய்யப்பட்டுள்ளது. குறிப்பு: {note}."
                elif lang == "tanglish":
                    reply = f"Unga order {ord_num} ({items_desc}) ₹{amt} successfully deliver aayiduchu. Tracking note: {note}."
                else:
                    reply = f"Your order {ord_num} for ₹{amt} ({items_desc}) has been delivered successfully. Tracking note: {note}."
            elif ord_st == "shipped":
                if lang == "ta":
                    reply = f"உங்கள் ஆர்டர் {ord_num} ({items_desc}) அனுப்பப்பட்டு வழியில் உள்ளது. குறிப்பு: {note}."
                elif lang == "tanglish":
                    reply = f"Unga order {ord_num} transit la irukku. Tracking note: {note}."
                else:
                    reply = f"Your order {ord_num} ({items_desc}) is currently shipped and in transit. Tracking note: {note}."
            elif ord_st == "out_for_delivery":
                if lang == "ta":
                    reply = f"உங்கள் ஆர்டர் {ord_num} இன்று டெலிவரிக்காக வெளியே சென்றுள்ளது. குறிப்பு: {note}."
                elif lang == "tanglish":
                    reply = f"Unga order {ord_num} innaiku out for delivery la irukku. Courier partner: {note}."
                else:
                    reply = f"Your order {ord_num} is out for delivery today. Details: {note}."
            elif ord_st == "cancelled":
                if lang == "ta":
                    reply = f"உங்கள் ஆர்டர் {ord_num} ஷிப்பிங்கிற்கு முன்பே ரத்து செய்யப்பட்டுள்ளது. குறிப்பு: {note}."
                elif lang == "tanglish":
                    reply = f"Unga order {ord_num} dispatch munname cancel aayiduchu. Note: {note}."
                else:
                    reply = f"Your order {ord_num} was cancelled prior to shipping. Note: {note}."
            else:
                reply = f"Your order {ord_num} is currently in {ord_st} status. Tracking note: {note}."

        elif status == "auto_approved":
            ord_num = tool_data.get("order_number", "")
            amt = tool_data.get("amount", "")
            if lang == "ta":
                reply = f"உங்கள் ஆர்டர் {ord_num}-க்கான ₹{amt} ரீஃபண்ட் கோரிக்கை அங்கீகரிக்கப்பட்டுவிட்டது! தொகை 5 முதல் 7 வணிக நாட்களில் உங்கள் வங்கிக் கணக்கில் வரவு வைக்கப்படும்."
            elif lang == "tanglish":
                reply = f"Unga order {ord_num} refund (₹{amt}) approve aayiduchu! 5-7 business days kulla unga account la credit aagidum."
            else:
                reply = f"Your refund request for order {ord_num} (₹{amt}) has been auto-approved and processed. The amount will reflect in your original payment method in 5 to 7 business days."

        elif status == "pending_approval":
            ord_num = tool_data.get("order_number", "")
            amt = tool_data.get("amount", "")
            if lang == "ta":
                reply = f"ஆர்டர் {ord_num}-க்கான ரீஃபண்ட் தொகை ₹{amt} என்பது ₹2,000 உச்சவரம்பை விட அதிகம் என்பதால், இது மேற்பார்வையாளர் மதிப்பாய்வுக்கு அனுப்பப்பட்டுள்ளது. எங்கள் வாடிக்கையாளர் சேவை நிர்வாகி விரைவில் இதனை மதிப்பாய்வு செய்வார்."
            elif lang == "tanglish":
                reply = f"Unga order {ord_num} refund amount ₹{amt} ₹2,000 limit vida adhigam irukkaradhala supervisor review ku poyirukku. Customer support executive seekiram review pannuvaanga."
            else:
                reply = f"Your refund request for order {ord_num} (₹{amt}) requires manual review because it exceeds our ₹2,000 instant approval limit. A customer support supervisor will review and approve it shortly."

        elif status == "ineligible":
            reason = tool_data.get("reason", "ineligible")
            if lang == "ta":
                reply = f"மன்னிக்கவும், உங்கள் ரீஃபண்ட் கோரிக்கையை ஏற்க இயலாது. காரணம்: {reason}."
            elif lang == "tanglish":
                reply = f"Sorry, unga refund request accept panna mudiyathu. Reason: {reason}."
            else:
                reply = f"Unfortunately, this order is not eligible for a return/refund. Reason: {reason}."

        elif status == "policy_found":
            sections = tool_data.get("policy_sections", [])
            sec_summaries = " ".join(s.get("content", "").replace("## ", "") for s in sections[:2])
            if lang == "ta":
                reply = f"எங்கள் கொள்கை விவரங்கள்: {sec_summaries}"
            elif lang == "tanglish":
                reply = f"Enga store policy: {sec_summaries}"
            else:
                reply = f"According to our store policy: {sec_summaries}"

        elif status == "no_relevant_policy":
            if lang == "ta":
                reply = "மன்னிக்கவும், நீங்கள் கேட்ட குறிப்பிட்ட கொள்கை பற்றிய தகவல் கிடைக்கவில்லை. வாடிக்கையாளர் சேவை அதிகாரியுடன் பேச விரும்புகிறீர்களா?"
            elif lang == "tanglish":
                reply = "Sorry, neenga keta specific policy details kidaikala. Support executive kooda connect panna va?"
            else:
                reply = "I could not find specific store policy information matching your question. Would you like me to connect you with a customer support executive?"

        elif status == "products_found":
            prods = tool_data.get("products", [])
            lines_out = []
            for p in prods[:3]:
                name = p.get("name_ta") if lang == "ta" else p.get("name_en")
                price = p.get("price_inr")
                stk = "In Stock" if p.get("stock_qty", 0) > 0 else "Out of Stock"
                if lang == "ta":
                    stk = "இருப்பில் உள்ளது" if p.get("stock_qty", 0) > 0 else "இருப்பில் இல்லை"
                lines_out.append(f"• {name} - ₹{price} ({stk})")
            joined = "\n".join(lines_out)
            if lang == "ta":
                reply = f"உங்கள் தேடலுக்கு ஏற்ற தயாரிப்புகள் இதோ:\n{joined}"
            elif lang == "tanglish":
                reply = f"Neenga keta products catalog la irukku:\n{joined}"
            else:
                reply = f"Here are the matching products from our catalog:\n{joined}"

        elif status == "no_matching_products":
            if lang == "ta":
                reply = "மன்னிக்கவும், உங்கள் தேடலுக்குரிய பொருட்கள் எதுவும் எங்கள் கடையில் கிடைக்கவில்லை. வேறு தேடல் சொற்களைப் பயன்படுத்திப் பார்க்கவும்."
            elif lang == "tanglish":
                reply = "Sorry, matching products edhuvum kidaikala. Vera search terms pottu check pannunga."
            else:
                reply = "No matching products were found in our catalog. Try searching with broader terms or different categories."

        elif status == "escalated":
            if lang == "ta":
                reply = "உங்கள் உரையாடல் எங்கள் வாடிக்கையாளர் சேவை மேற்பார்வையாளருக்கு மாற்றப்பட்டுள்ளது. விரைவில் ஒரு அதிகாரி இணைவார்."
            elif lang == "tanglish":
                reply = "Unga chat customer support executive kooda connect aayiduchu. Oru agent seekiram join pannuvaanga."
            else:
                reply = "I have escalated your conversation to our customer support team. An executive will assist you shortly."

        else:
            reply = "Hello! How can I assist you with your orders, returns, or product inquiries today?"

        actions = ["Track order", "Return policy", "Browse store"]
        if status in ("order_status", "found_orders"):
            actions = ["Track another order", "Request refund", "Need help"]
        elif status in ("auto_approved", "pending_approval", "ineligible"):
            actions = ["Track refund", "View return policy", "Help with another order"]
        elif status in ("products_found", "no_matching_products"):
            actions = ["Filter by price", "Search top rated", "Browse all products"]
        elif status == "escalated":
            actions = ["Check ticket status", "Contact via email", "Return to main menu"]

        if response_format and response_format.get("type") == "json_object":
            structured_data = {
                "headline": f"{status.replace('_', ' ').title()}" if status else "Support Response",
                "reply": reply,
                "suggested_actions": actions,
                "data": tool_data,
            }
            final_content = json.dumps(structured_data, ensure_ascii=False)
        else:
            final_content = reply

        return LLMResponse(
            content=final_content,
            model=model,
            prompt_tokens=350,
            completion_tokens=50,
            cost_inr=Decimal("0.0200"),
            latency_ms=25,
        )

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.1,
        response_format: dict[str, str] | None = None,
    ) -> LLMResponse:
        """Execute chat completion against Groq API with retries and token/cost measurement."""
        # If API key is not configured or using placeholder, use the fast local dev simulator
        if not self.api_key or self.api_key.startswith("gsk_placeholder"):
            logger.info("Using local dev LLM simulator (GROQ_API_KEY is placeholder or unset).")
            return self._simulate_dev_completion(messages, model, response_format)

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        attempt = 0
        last_error: Exception | None = None
        start_time = time.monotonic()

        while attempt <= self.max_retries:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, headers=headers, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    choice = data["choices"][0]
                    content = choice["message"]["content"]
                    usage = data.get("usage", {})
                    p_tokens = usage.get("prompt_tokens", 0)
                    c_tokens = usage.get("completion_tokens", 0)

                    latency_ms = int((time.monotonic() - start_time) * 1000)
                    cost_inr = self._calculate_cost(model, p_tokens, c_tokens)

                    return LLMResponse(
                        content=content,
                        model=model,
                        prompt_tokens=p_tokens,
                        completion_tokens=c_tokens,
                        cost_inr=cost_inr,
                        latency_ms=latency_ms,
                        raw_response=data,
                    )
                elif resp.status_code == 401:
                    logger.error("Groq API returned HTTP 401 Unauthorized (Invalid API Key). Falling back to dev simulation.")
                    return self._simulate_dev_completion(messages, model, response_format)
                else:
                    error_msg = f"Groq API returned HTTP {resp.status_code}: {resp.text}"
                    logger.warning("Groq attempt %d failed: %s", attempt + 1, error_msg)
                    last_error = RuntimeError(error_msg)

            except Exception as exc:
                logger.warning("Groq attempt %d encountered exception: %s", attempt + 1, exc)
                last_error = exc

            attempt += 1
            if attempt <= self.max_retries:
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))

        latency_ms = int((time.monotonic() - start_time) * 1000)
        raise RuntimeError(
            f"Groq API failed after {self.max_retries + 1} attempts (latency: {latency_ms}ms): {last_error}"
        )
