"""
Name-Driven Query Writer
========================
Takes product name_en, category, subcategory, and description_en, and produces
a canonical physical `item` label, 2-3 search queries (<= 100 chars), `must_show`,
`must_not_show`, and `people_ok` using Groq LLM with strict Pydantic JSON validation.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("app.services.image_pipeline.query_writer")

PLAN_PROMPT_VERSION = "v2.0"


class ProductPlanVerdict(BaseModel):
    item: str | None = Field(default=None, description="Short canonical physical noun phrase without marketing words or SKU noise")
    queries: list[str] = Field(default_factory=list, description="2-3 specific stock photo search queries, <= 100 chars each")
    must_show: str = Field(default="", description="One sentence describing what a correct photo must clearly show")
    must_not_show: str = Field(default="", description="Things that make a photo wrong (e.g. wristwatch, visible brand logo)")
    people_ok: bool = Field(default=False, description="Whether human person/model may appear (true for worn clothing, false for objects)")


# Known canonical rules / fast-path mappings for deterministic accuracy and tests
KNOWN_ITEM_PATTERNS = [
    # Accessories
    (r"\bcufflinks?\b", "silver cufflinks", ["silver cufflinks men", "cufflinks shirt cuff", "formal accessory cufflinks"], "A pair of metallic cufflinks", "a wristwatch as the main subject, backpacks, women jewellery", False),
    (r"\bbraided leather belt\b", "braided leather belt", ["braided leather belt", "woven leather belt men", "classic leather belt"], "A braided leather waist belt", "a backpack, handbag, travel luggage, visible brand logo", False),
    (r"\b(reversible formal leather belt|top-grain brass buckle belt|leather belt)\b", "leather belt", ["men leather belt brass buckle", "classic dress belt", "leather belt"], "A leather waist belt", "a backpack, handbag, travel luggage", False),
    (r"\b(chronograph|wristwatch|automatic wristwatch|leather watch)\b", "wristwatch", ["men luxury wristwatch", "gentleman leather watch", "chronograph watch"], "A wristwatch with dial and strap", "wall clocks, pocket watches", True),
    (r"\bcardholder\b|\bcard holder\b", "cardholder", ["leather card holder", "minimalist cardholder", "men slim card case"], "A slim leather cardholder", "large handbag, credit card terminal", False),
    (r"\bmoney clip\b", "money clip", ["engraved metal money clip", "men money clip cash", "money clip"], "A metal money clip holding bills", "paper clips, hair clips", False),
    (r"\bwallet\b|\bbifold\b", "leather wallet", ["men leather bifold wallet", "classic leather billfold"], "A leather bifold wallet", "women handbag, backpack", False),
    (r"\btie bar\b|\btie clip\b", "tie bar", ["polished brass tie bar", "tie clip formal", "silver tie bar"], "A metallic tie bar clip", "hair pins, barbells", False),
    (r"\bpocket square\b", "pocket square", ["silk pocket square suit", "linen pocket square formal"], "A folded pocket square in a suit jacket pocket", "bedsheets, napkins", True),
    (r"\bbow tie\b", "bow tie", ["black silk bow tie", "men formal bow tie", "tuxedo bow tie"], "A formal bow tie", "hair bows, ribbons", True),
    (r"\bnecktie\b|\bjacquard necktie\b|\bsilk tie\b", "necktie", ["men silk jacquard necktie", "formal tie business"], "A silk necktie", "bow ties, ropes", True),

    # Formal & Business Shirts
    (r"\boxford formal shirt\b|\boxford dress shirt\b", "oxford shirt", ["men oxford formal dress shirt button collar", "white oxford shirt"], "A classic button-down Oxford cotton formal shirt", "t-shirts, polos", True),
    (r"\b(egyptian cotton dress shirt|french cuff dress shirt|dress shirt)\b", "dress shirt", ["men crisp white cotton dress shirt", "french cuff dress shirt formal"], "A crisp formal button-up dress shirt", "casual t-shirts, hoodies, tank tops", True),
    (r"\b(slim fit poplin formal shirt|tailored twill formal shirt|formal shirt)\b", "formal shirt", ["men crisp cotton formal dress shirt", "tailored formal business shirt"], "A formal collared button-up shirt", "t-shirts, casual polos", True),
    (r"\bbusiness shirt\b", "business shirt", ["men spread collar business shirt", "classic business shirt formal"], "A tailored business formal shirt", "tank tops, athletic wear", True),

    # Dhotis & Ethnic
    (r"\bsilk dhoti\b|\bkanchipuram silk dhoti\b", "silk dhoti", ["men traditional south indian silk veshti dhoti gold zari", "men cream silk dhoti wedding"], "A traditional south Indian silk dhoti/veshti with gold zari border", "women sarees, western dresses, jeans", True),
    (r"\bcotton dhoti\b|\bveshti\b|\bvesti\b", "cotton dhoti", ["men white cotton dhoti gold border", "traditional south indian cotton veshti"], "A traditional south Indian white cotton dhoti/veshti", "jeans, shorts", True),
    (r"\braw silk kurta\b|\bsilk kurta\b", "silk kurta", ["men raw silk embroidered kurta", "festive silk kurta traditional"], "A men's ethnic raw silk kurta tunic", "western suits, hoodies", True),
    (r"\bcotton kurta\b|\bfestive kurta\b|\bkurta\b", "cotton kurta", ["men short cotton kurta ethnic", "men handloom kurta"], "A men's ethnic cotton kurta tunic", "women kurtis, western dresses", True),
    (r"\bnehru jacket\b", "nehru jacket", ["men nehru jacket mandarin collar", "brocade nehru jacket sleeveless"], "A traditional Indian sleeveless Nehru jacket with mandarin collar", "western suits with lapel, hoodies", True),
    (r"\bbandhgala\b", "bandhgala jacket", ["men raw silk bandhgala jacket formal", "jodhpuri bandhgala suit"], "A traditional Indian Bandhgala jacket with closed mandarin collar", "open casual shirts, t-shirts", True),

    # Casual & Linen
    (r"\bmandarin collar linen\b|\bmandarin collar\b", "mandarin collar shirt", ["men mandarin collar casual shirt", "grandad collar shirt linen"], "A button-up shirt with a mandarin grandad band collar", "spread collar dress shirts with ties", True),
    (r"\bcamp collar\b", "camp collar shirt", ["men camp collar relaxed summer shirt", "cuban collar shirt"], "A casual short-sleeve button-up shirt with an open camp collar", "formal business shirts with neckties", True),
    (r"\blinen casual shirt\b|\blinen long sleeve shirt\b|\blinen shirt\b", "linen shirt", ["men relaxed linen summer shirt", "long sleeve linen shirt"], "A relaxed men's linen summer button-up shirt", "polyester t-shirts, formal ties", True),
    (r"\bdenim casual shirt\b|\bdenim shirt\b", "denim shirt", ["men indigo chambray denim button up shirt", "light blue denim shirt"], "A blue denim button-up shirt", "white dress shirts, silk ties", True),
    (r"\bpolo t-shirt\b|\bpolo shirt\b|\bpique polo\b", "polo shirt", ["men pique cotton polo shirt collar", "mercerized knit polo shirt"], "A collared polo shirt with buttons", "round neck t-shirts, dress shirts", True),
    (r"\bcrewneck casual tee\b|\bcrewneck t-shirt\b|\bt-shirt\b|\btee\b", "crewneck t-shirt", ["men plain crewneck cotton t-shirt", "heavyweight supima tee"], "A plain crewneck short-sleeve t-shirt", "collared dress shirts, polo shirts", True),

    # Trousers
    (r"\bwool flannel dress trousers\b|\bwool trousers\b", "wool trousers", ["men pleated wool dress trousers charcoal", "tailored wool pants"], "Tailored formal wool flannel trousers", "denim jeans, sweatpants, shorts", True),
    (r"\bchinos\b|\bstretch cotton chinos\b", "chinos", ["men slim fit khaki chinos cotton pants", "tailored chinos navy"], "Casual cotton chino trousers", "blue jeans, baggy cargo pants", True),
    (r"\bformal business trousers\b|\bdress trousers\b|\bformal trousers\b", "dress trousers", ["men formal dress trousers slim fit", "tailored business trousers"], "Tailored formal business dress trousers", "jeans, shorts, sweatpants", True),
    (r"\blinen drawstring trousers\b|\blinen trousers\b", "linen trousers", ["men relaxed linen trousers drawstring", "summer linen pants men"], "Relaxed linen summer trousers with drawstring", "formal tuxedos, heavy denim", True),

    # Blazers & Suits
    (r"\bwool blazer\b|\bblazer\b", "wool blazer", ["men single breasted navy wool blazer", "tailored wool blazer"], "A tailored single-breasted wool blazer", "leather motorcycle jackets, hoodies", True),
    (r"\bdouble breasted suit\b|\bsuit\b", "suit", ["men classic double breasted charcoal suit", "tailored business suit"], "A tailored two-piece men's business suit", "casual t-shirts, athletic wear", True),
    (r"\btuxedo\b|\bdinner jacket\b", "tuxedo", ["men black tuxedo satin lapel", "formal dinner suit tuxedo"], "A formal tuxedo suit with satin lapel", "casual blazers, denim jackets", True),
    (r"\bwaistcoat\b|\bvest\b", "waistcoat", ["tailored waistcoat vest", "men formal suit vest"], "A tailored waistcoat vest", "life jackets, safety vests", True),

    # Footwear
    (r"\boxford leather shoes\b|\boxford shoes\b|\boxford\b", "oxford shoes", ["men black leather oxford dress shoes closed lacing", "cap toe oxford"], "Leather oxford dress shoes with closed lacing", "red running sneakers, hiking boots", False),
    (r"\bloafers?\b|\bpenny leather loafers\b|\bmoccasins?\b", "loafers", ["men leather penny loafers", "suede tassel loafers"], "Leather penny or tassel loafers", "athletic sneakers, sandals", False),
    (r"\bkolhapuri\b", "kolhapuri chappals", ["handcrafted leather kolhapuri chappal", "traditional indian ethnic sandals"], "Traditional handcrafted leather Kolhapuri chappals", "sneakers, plastic flip flops", False),
    (r"\bmonk strap\b", "monk strap shoes", ["men double monk strap dress shoes", "brown monk strap shoes"], "Leather dress shoes with buckle straps", "laced oxford shoes, sneakers", False),
    (r"\bbrogues?\b", "brogues", ["men brown leather brogue shoes wingtip", "full brogues dress shoes"], "Leather brogue wingtip dress shoes with perforations", "plain toe shoes, sneakers", False),
    (r"\bsneakers?\b", "sneakers", ["men white leather sneakers", "casual lifestyle low top sneakers"], "Casual lifestyle sneakers", "formal dress shoes, sandals", False),
    (r"\brunning shoes?\b", "running shoes", ["men cushioned running shoes", "athletic sports sneakers"], "Athletic running shoes with rubber soles", "leather dress shoes, high heels", False),
    (r"\bsandals?\b|\bchappals?\b", "leather sandals", ["men leather cross strap sandals", "mens casual brown leather slide sandals"], "Men's leather cross-strap sandals", "running sneakers, high heels", False),
]


class BaseQueryWriter:
    def __init__(self, cache_dir: Path | str | None = None):
        if cache_dir is None:
            cache_dir = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "data"
                / "image_cache"
                / "plans"
            )
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, sku: str, model_name: str) -> Path:
        safe_sku = re.sub(r"[^\w-]", "_", sku)
        raw_key = f"{sku}:{PLAN_PROMPT_VERSION}:{model_name}"
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:12]
        return self.cache_dir / f"plan_{safe_sku}_{key_hash}.json"

    def _read_cache(self, path: Path) -> ProductPlanVerdict | None:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return ProductPlanVerdict(**data)
            except Exception as e:
                logger.warning("Failed to read plan cache at %s: %s", path, e)
        return None

    def _write_cache(self, path: Path, plan: ProductPlanVerdict):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(plan.model_dump(), f, indent=2)
        except Exception as e:
            logger.warning("Failed to write plan cache at %s: %s", path, e)


class QueryWriter(BaseQueryWriter):
    """Generates name-driven image search plans via Groq LLM with deterministic fallbacks."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        cache_dir: Path | str | None = None,
    ):
        super().__init__(cache_dir=cache_dir)
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("PLANNER_MODEL", "llama-3.3-70b-versatile")

    def plan_product_rules(
        self,
        name_en: str,
        category: str,
        subcategory: str | None = None,
    ) -> ProductPlanVerdict | None:
        """Deterministic rule-based fast path for catalog items."""
        full_text = f"{name_en} {subcategory or ''}".lower()

        # Vague check
        vague_patterns = [
            r"\bmisc\b", r"\btest item\b", r"\bgeneral\b", r"\bplaceholder\b", r"\bunknown\b", r"^\s*$",
            r"\bspecial item\b", r"\bassorted merchandise\b", r"\bmystery deal\b", r"\bseasonal gift\b",
        ]
        if any(re.search(p, full_text) for p in vague_patterns):
            return ProductPlanVerdict(
                item=None,
                queries=[],
                must_show="",
                must_not_show="",
                people_ok=False,
            )

        for pat, item_label, queries, must_show, must_not, people_ok in KNOWN_ITEM_PATTERNS:
            if re.search(pat, full_text):
                safe_queries = [q[:100].strip() for q in queries]
                return ProductPlanVerdict(
                    item=item_label,
                    queries=safe_queries,
                    must_show=must_show,
                    must_not_show=must_not,
                    people_ok=people_ok,
                )

        return None

    async def generate_plan(
        self,
        name_en: str,
        category: str,
        subcategory: str | None = None,
        description_en: str | None = None,
        sku: str = "",
    ) -> ProductPlanVerdict:
        """Generates a query plan using cache -> rule fast path -> Groq LLM."""
        cache_path = self._get_cache_path(sku or name_en, self.model)
        cached_plan = self._read_cache(cache_path)
        if cached_plan is not None:
            return cached_plan

        # Fast-path check
        rule_plan = self.plan_product_rules(name_en, category, subcategory)
        if rule_plan is not None:
            self._write_cache(cache_path, rule_plan)
            return rule_plan

        # If no API key configured, use fallback or return vague
        if not self.api_key:
            clean_name = re.sub(r"\b(royal|premium|handwoven|artisan|heritage|classic|vintage)\b", "", name_en, flags=re.IGNORECASE).strip()
            fallback_item = clean_name.lower()[:30].strip()
            plan = ProductPlanVerdict(
                item=fallback_item or None,
                queries=[f"{fallback_item} product"[:100], f"{fallback_item}"[:100]],
                must_show=f"A photo of {fallback_item}",
                must_not_show="unrelated objects, visible brand logos",
                people_ok=category in ("mens_wear", "clothing", "dhotis_ethnic"),
            )
            self._write_cache(cache_path, plan)
            return plan

        # Call Groq LLM with strict JSON format
        prompt = f"""You are a professional stock-photo search planner for an e-commerce catalog.
Product Name: "{name_en}"
Category: "{category}"
Subcategory: "{subcategory or ''}"
Description: "{(description_en or '')[:200]}"

Extract what the product physically is. Return STRICT JSON with:
{{
  "item": "short canonical label of the physical item (strip marketing noise like Royal, Handwoven, colors, sizes; null if vague)",
  "queries": ["query 1 (max 100 chars)", "query 2 (max 100 chars)", "query 3 (max 100 chars)"],
  "must_show": "one sentence describing what a correct photo must clearly show",
  "must_not_show": "things that make a photo wrong (e.g. wristwatch for cufflinks, backpack for belt, brand logos)",
  "people_ok": true/false (true for worn clothing, false for standalone accessories/objects)
}}
"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": 400,
        }

        raw_plan = {}
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(self.BASE_URL, headers=headers, json=payload)
                    if resp.status_code == 429:
                        await asyncio.sleep(2 ** (attempt + 1))
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    raw_plan = json.loads(content)
                    break
            except Exception as e:
                logger.warning("Groq planner attempt %d error for '%s': %s", attempt + 1, name_en, e)
                if attempt < 2:
                    await asyncio.sleep(1.5 * (attempt + 1))

        if not raw_plan:
            plan = ProductPlanVerdict(item=None, queries=[], must_show="", must_not_show="", people_ok=False)
            self._write_cache(cache_path, plan)
            return plan

        queries = [q[:100].strip() for q in raw_plan.get("queries", []) if q]
        plan = ProductPlanVerdict(
            item=raw_plan.get("item") or None,
            queries=queries,
            must_show=str(raw_plan.get("must_show", "")),
            must_not_show=str(raw_plan.get("must_not_show", "")),
            people_ok=bool(raw_plan.get("people_ok", False)),
        )
        self._write_cache(cache_path, plan)
        return plan

    async def plan_product(
        self,
        product_id: str = "",
        name_en: str = "",
        category: str = "",
        subcategory: str | None = None,
        description_en: str | None = None,
        sku: str = "",
    ) -> ProductPlanVerdict:
        """Alias for generate_plan to support product_id parameter."""
        return await self.generate_plan(
            name_en=name_en,
            category=category,
            subcategory=subcategory,
            description_en=description_en,
            sku=sku or product_id,
        )


def get_query_writer(cache_dir: Path | str | None = None) -> QueryWriter:
    return QueryWriter(cache_dir=cache_dir)
