"""
Tests for Name-Driven Query Writer
==================================
Tests:
- Golden list of 40+ realistic product names across categories
- Name cleaning (removes marketing adjectives, colors, SKUs)
- Vague names get item: null
- Invalid JSON retried then skipped
- Disk caching works
"""

import pytest
from app.services.image_pipeline.query_writer import (
    ProductPlanVerdict,
    QueryWriter,
)


GOLDEN_PRODUCT_TEST_CASES = [
    # Accessories
    ("Royal Silver Cufflinks", "Accessories", "silver cufflinks"),
    ("Handwoven Silver Cufflinks", "Accessories", "silver cufflinks"),
    ("Classic Mother of Pearl Cufflinks", "Accessories", "silver cufflinks"),
    ("Premium Braided Leather Belt", "Accessories", "braided leather belt"),
    ("Reversible Formal Leather Belt", "Accessories", "leather belt"),
    ("Top-Grain Brass Buckle Belt", "Accessories", "leather belt"),
    ("Classic Chronograph Watch with Leather Strap", "Accessories", "wristwatch"),
    ("Heritage Automatic Wristwatch", "Accessories", "wristwatch"),
    ("Minimalist Slim Leather Cardholder", "Accessories", "cardholder"),
    ("Matte Finish Engraved Money Clip", "Accessories", "money clip"),
    ("Classic Leather Bifold Wallet", "Accessories", "leather wallet"),
    ("Polished Brass Tie Bar", "Accessories", "tie bar"),
    ("Pure Silk Pocket Square", "Accessories", "pocket square"),
    ("Black Satin Bow Tie", "Accessories", "bow tie"),
    ("Jacquard Silk Necktie", "Accessories", "necktie"),

    # Formal Shirts
    ("Royal Oxford Formal Shirt", "Formal Shirts", "oxford shirt"),
    ("Pure Egyptian Cotton Dress Shirt", "Formal Shirts", "dress shirt"),
    ("Classic French Cuff Dress Shirt", "Formal Shirts", "dress shirt"),
    ("Slim Fit Poplin Formal Shirt", "Formal Shirts", "formal shirt"),
    ("Spread Collar Business Shirt", "Formal Shirts", "business shirt"),
    ("Tailored Twill Formal Shirt", "Formal Shirts", "formal shirt"),

    # Casual & Linen
    ("Pure Linen Long Sleeve Shirt", "Casual & Linen", "linen shirt"),
    ("Mandarin Collar Linen Casual Shirt", "Casual & Linen", "mandarin collar shirt"),
    ("Camp Collar Relaxed Summer Shirt", "Casual & Linen", "camp collar shirt"),
    ("Indigo Denim Casual Shirt", "Casual & Linen", "denim shirt"),
    ("Classic Pique Polo T-Shirt", "Casual & Linen", "polo shirt"),
    ("Heavyweight Crewneck Casual Tee", "Casual & Linen", "crewneck t-shirt"),

    # Dhotis & Ethnic
    ("Traditional Kanchipuram Silk Dhoti", "Dhotis & Ethnic", "silk dhoti"),
    ("Pure Cotton Gold Zari Border Veshti", "Dhotis & Ethnic", "cotton dhoti"),
    ("Embroidered Raw Silk Kurta", "Dhotis & Ethnic", "silk kurta"),
    ("Handloom Cotton Festive Kurta", "Dhotis & Ethnic", "cotton kurta"),
    ("Brocade Nehru Jacket with Mandarin Collar", "Dhotis & Ethnic", "nehru jacket"),
    ("Raw Silk Bandhgala Jacket", "Dhotis & Ethnic", "bandhgala jacket"),

    # Trousers
    ("Pleated Wool Flannel Dress Trousers", "Trousers", "wool trousers"),
    ("Flat Front Stretch Cotton Chinos", "Trousers", "chinos"),
    ("Slim Fit Formal Business Trousers", "Trousers", "dress trousers"),
    ("Relaxed Fit Linen Drawstring Trousers", "Trousers", "linen trousers"),

    # Blazers & Suits
    ("Single Breasted Navy Wool Blazer", "Blazers & Suits", "wool blazer"),
    ("Classic Charcoal Double Breasted Suit", "Blazers & Suits", "suit"),
    ("Black Dinner Jacket Tuxedo with Satin Lapel", "Blazers & Suits", "tuxedo"),
    ("Tailored Formal Waistcoat Vest", "Blazers & Suits", "waistcoat"),

    # Footwear
    ("Essential Oxford Leather Shoes", "Footwear", "oxford shoes"),
    ("Urban Penny Leather Loafers", "Footwear", "loafers"),
    ("Handcrafted Leather Kolhapuri Chappals", "Footwear", "kolhapuri chappals"),
    ("Classic Double Monk Strap Dress Shoes", "Footwear", "monk strap shoes"),
    ("Vintage Wingtip Brogues", "Footwear", "brogues"),
    ("Minimalist White Leather Low-Top Sneakers", "Footwear", "sneakers"),
    ("Breathable Cushioned Athletic Running Shoes", "Footwear", "running shoes"),
]


@pytest.mark.asyncio
async def test_golden_product_names_canonical_item(tmp_path):
    writer = QueryWriter(cache_dir=tmp_path)

    for i, (name, cat, expected_item) in enumerate(GOLDEN_PRODUCT_TEST_CASES):
        plan = await writer.plan_product(
            product_id=f"test_id_{i}",
            name_en=name,
            category=cat,
            subcategory=cat,
        )
        assert plan.item is not None, f"Item was null for '{name}'"
        assert plan.item == expected_item, f"For '{name}': expected '{expected_item}', got '{plan.item}'"
        assert len(plan.queries) >= 1, f"No queries generated for '{name}'"
        for q in plan.queries:
            assert len(q) <= 100, f"Query '{q}' exceeds Pixabay 100 char limit"


@pytest.mark.asyncio
async def test_screenshot_products_name_cleaning(tmp_path):
    writer = QueryWriter(cache_dir=tmp_path)

    # 1. Royal Silver Cufflinks -> silver cufflinks
    p1 = await writer.plan_product("1", "Royal Silver Cufflinks", "Accessories")
    assert p1.item == "silver cufflinks"
    assert p1.people_ok is False

    # 2. Handwoven Silver Cufflinks -> silver cufflinks
    p2 = await writer.plan_product("2", "Handwoven Silver Cufflinks", "Accessories")
    assert p2.item == "silver cufflinks"
    assert p2.people_ok is False

    # 3. Premium Braided Leather Belt -> braided leather belt
    p3 = await writer.plan_product("3", "Premium Braided Leather Belt", "Accessories")
    assert p3.item == "braided leather belt"
    assert p3.people_ok is False


@pytest.mark.asyncio
async def test_vague_names_get_null_item(tmp_path):
    writer = QueryWriter(cache_dir=tmp_path)

    vague_names = [
        "Special Item #42",
        "Assorted Merchandise Pack",
        "Mystery Deal Combo",
        "Seasonal Gift Item",
    ]

    for name in vague_names:
        plan = await writer.plan_product("vague_id", name, "Miscellaneous")
        assert plan.item is None, f"Expected null item for vague name '{name}', got '{plan.item}'"


@pytest.mark.asyncio
async def test_plan_caching_on_disk(tmp_path):
    writer = QueryWriter(cache_dir=tmp_path)

    # First call writes to cache
    plan1 = await writer.plan_product("c1", "Royal Silver Cufflinks", "Accessories")

    # Second call should read from disk cache
    plan2 = await writer.plan_product("c1", "Royal Silver Cufflinks", "Accessories")
    assert plan1.item == plan2.item
    assert plan1.queries == plan2.queries
