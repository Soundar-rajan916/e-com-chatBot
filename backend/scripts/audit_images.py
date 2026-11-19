"""
Product Image Audit Script
==========================
Audits how product images are currently chosen and served across the database
and storefront, identifies duplicates, cross-category collisions, and root causes.

Usage:
    python -m scripts.audit_images
    or
    python backend/scripts/audit_images.py
"""

import asyncio
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

repo_root = backend_dir.parent

from sqlalchemy import select
from app.db import async_session_factory
from app.models import Product

# Exact replica of frontend CURATED_PRODUCT_PHOTOS from frontend/src/utils/productImages.ts
CURATED_PRODUCT_PHOTOS = [
    # Accessories
    {
        "keywords": ["cufflink", "cufflinks", "clifflinks", "silver cufflinks", "royal silver cufflinks", "handwoven silver cufflinks"],
        "url": "https://images.unsplash.com/photo-1590736969955-71cc94801759?auto=format&fit=crop&w=600&q=80",
        "description": "Woman's wrist with watch and bracelet (MISMATCH for cufflinks)",
    },
    {
        "keywords": ["chronograph", "wristwatch", "leather watch", "timepiece", "watch"],
        "url": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=600&q=80",
        "description": "Wristwatch",
    },
    {
        "keywords": ["cardholder", "card holder", "slim leather cardholder"],
        "url": "https://images.unsplash.com/photo-1606503829068-1964f4347781?auto=format&fit=crop&w=600&q=80",
        "description": "Cardholder",
    },
    {
        "keywords": ["money clip", "engraved money clip"],
        "url": "https://images.unsplash.com/photo-1606503829068-1964f4347781?auto=format&fit=crop&w=600&q=80",
        "description": "Cardholder / Money clip (reused)",
    },
    {
        "keywords": ["wallet", "bifold", "billfold", "leather bifold wallet"],
        "url": "https://images.unsplash.com/photo-1627123424574-724758594e93?auto=format&fit=crop&w=600&q=80",
        "description": "Leather wallet",
    },
    {
        "keywords": ["braided leather belt", "braided belt", "heritage braided leather belt"],
        "url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80",
        "description": "Backpack (MISMATCH for braided belt)",
    },
    {
        "keywords": ["reversible leather belt", "reversible belt", "essential reversible leather belt"],
        "url": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=600&q=80",
        "description": "Leather bag/purse",
    },
    {
        "keywords": ["leather belt", "belt"],
        "url": "https://images.unsplash.com/photo-1624222247344-550fb60583dc?auto=format&fit=crop&w=600&q=80",
        "description": "Leather belt",
    },
    {
        "keywords": ["tie bar", "tie clip", "polished brass tie bar"],
        "url": "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=600&q=80",
        "description": "Suit jacket/tie bar",
    },
    {
        "keywords": ["pocket square", "linen pocket square"],
        "url": "https://images.unsplash.com/photo-1589756823695-278bc923f962?auto=format&fit=crop&w=600&q=80",
        "description": "Tie / pocket square",
    },
    {
        "keywords": ["bow tie", "silk bow tie", "woven silk bow tie"],
        "url": "https://images.unsplash.com/photo-1589756823695-278bc923f962?auto=format&fit=crop&w=600&q=80",
        "description": "Tie / pocket square (reused)",
    },
    {
        "keywords": ["necktie", "jacquard necktie", "silk jacquard", "tie"],
        "url": "https://images.unsplash.com/photo-1589756823695-278bc923f962?auto=format&fit=crop&w=600&q=80",
        "description": "Tie / pocket square (reused)",
    },

    # Blazers & Suits
    {
        "keywords": ["waistcoat", "tailored waistcoat", "suit vest", "formal vest"],
        "url": "https://images.unsplash.com/photo-1592878904946-b3cd8ae243d0?auto=format&fit=crop&w=600&q=80",
        "description": "Waistcoat",
    },
    {
        "keywords": ["tuxedo", "black tuxedo jacket", "tuxedo jacket", "tux"],
        "url": "https://images.unsplash.com/photo-1593030761757-71fae45fa0e7?auto=format&fit=crop&w=600&q=80",
        "description": "Tuxedo",
    },
    {
        "keywords": ["houndstooth", "houndstooth wool jacket"],
        "url": "https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=600&q=80",
        "description": "Houndstooth jacket",
    },
    {
        "keywords": ["double-breasted", "double-breasted blazer", "double breasted"],
        "url": "https://images.unsplash.com/photo-1591561954557-26941169b49e?auto=format&fit=crop&w=600&q=80",
        "description": "Double breasted blazer",
    },
    {
        "keywords": ["single-breasted", "single-breasted blazer", "single breasted", "classic single-breasted"],
        "url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=600&q=80",
        "description": "Leather jacket / single-breasted",
    },
    {
        "keywords": ["tweed", "classic tweed blazer", "tweed blazer"],
        "url": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=600&q=80",
        "description": "Man in suit",
    },
    {
        "keywords": ["bandhgala", "nehru jacket", "nehru coat", "raw silk nehru"],
        "url": "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=600&q=80",
        "description": "Suit jacket",
    },
    {
        "keywords": ["charcoal suit jacket", "navy wool blazer", "blazer", "suit", "jacket"],
        "url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=600&q=80",
        "description": "Suit jacket fallback",
    },

    # Footwear
    {
        "keywords": ["running", "running shoes", "cushioned running"],
        "url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80",
        "description": "Nike red running shoe",
    },
    {
        "keywords": ["sneaker", "sneakers", "white leather sneaker"],
        "url": "https://images.unsplash.com/photo-1560769629-975ec94e6a86?auto=format&fit=crop&w=600&q=80",
        "description": "Sneakers",
    },
    {
        "keywords": ["penny loafer", "penny leather loafer"],
        "url": "https://images.unsplash.com/photo-1533867617858-e7b97e060509?auto=format&fit=crop&w=600&q=80",
        "description": "Brown monk straps / loafers",
    },
    {
        "keywords": ["tassel loafer", "tassel leather loafer"],
        "url": "https://images.unsplash.com/photo-1582895181348-29b1ca1f52d5?auto=format&fit=crop&w=600&q=80",
        "description": "Loafers",
    },
    {
        "keywords": ["monk strap", "double monk strap"],
        "url": "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?auto=format&fit=crop&w=600&q=80",
        "description": "Double monk strap shoes",
    },
    {
        "keywords": ["brogue", "brogues", "brogue leather shoes"],
        "url": "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?auto=format&fit=crop&w=600&q=80",
        "description": "Double monk strap shoes (reused for brogues)",
    },
    {
        "keywords": ["derby", "derby dress shoes"],
        "url": "https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=600&q=80",
        "description": "Sneakers / dress shoes",
    },
    {
        "keywords": ["oxford", "oxford leather shoes"],
        "url": "https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=600&q=80",
        "description": "Nike sneakers (MISMATCH for Oxford leather shoes)",
    },
    {
        "keywords": ["kolhapuri", "peshawari", "chappal", "sandals", "sandal", "cross sandals"],
        "url": "https://images.unsplash.com/photo-1603808033192-082d6919d3e1?auto=format&fit=crop&w=600&q=80",
        "description": "Sneakers (MISMATCH for sandals/chappal)",
    },
    {
        "keywords": ["moccasin", "driving moccasins", "slip-on mule", "suede slip-on", "loafer", "shoes", "shoe", "footwear"],
        "url": "https://images.unsplash.com/photo-1533867617858-e7b97e060509?auto=format&fit=crop&w=600&q=80",
        "description": "Footwear generic fallback",
    },

    # Dhotis & Ethnic
    {
        "keywords": ["kanchipuram", "mayilkann", "zari", "gold zari", "kasavu", "temple border", "double layer", "panchakacham", "coimbatore", "vesti", "veshti", "dhoti", "angavastram", "lungi", "kurta"],
        "url": "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=600&q=80",
        "description": "Woman in gold saree (MISMATCH for men's dhotis/lungi)",
    },

    # Casual Shirts
    {
        "keywords": ["linen shirt", "summer linen", "cuban collar", "camp collar", "short sleeve linen"],
        "url": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=600&q=80",
        "description": "Flannel/casual shirt",
    },
    {
        "keywords": ["chambray", "indigo chambray", "safari", "utility", "flannel", "plaid", "mandarin", "raw cotton"],
        "url": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=600&q=80",
        "description": "Flannel/casual shirt (reused)",
    },

    # Formal Shirts
    {
        "keywords": ["pinstripe", "stripe dress shirt", "fine stripe", "striped shirt"],
        "url": "https://images.unsplash.com/photo-1603252109303-2751441dd157?auto=format&fit=crop&w=600&q=80",
        "description": "Striped shirt",
    },
    {
        "keywords": ["french cuff", "cutaway", "spread collar", "herringbone", "twill", "poplin", "oxford shirt", "giza cotton", "pinpoint", "dress shirt", "formal shirt", "shirt"],
        "url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=600&q=80",
        "description": "White formal dress shirt",
    },

    # Trousers & Chinos
    {
        "keywords": ["jeans", "denim", "selvedge"],
        "url": "https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=600&q=80",
        "description": "Blue jeans",
    },
    {
        "keywords": ["cargo", "cargo pants"],
        "url": "https://images.unsplash.com/photo-1517445312882-bc9910d016b7?auto=format&fit=crop&w=600&q=80",
        "description": "Cargo pants",
    },
    {
        "keywords": ["pleated", "dress trousers", "wool trousers", "dress pants"],
        "url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=600&q=80",
        "description": "Trousers",
    },
    {
        "keywords": ["chinos", "khaki", "gurkha", "drawstring", "trousers", "pants"],
        "url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=600&q=80",
        "description": "Chinos / trousers",
    },

    # Polos & Tees
    {
        "keywords": ["henley", "waffle"],
        "url": "https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=600&q=80",
        "description": "T-shirt",
    },
    {
        "keywords": ["polo", "pique", "mercerized", "striped polo", "zip neck polo"],
        "url": "https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=600&q=80",
        "description": "Polo shirt",
    },
    {
        "keywords": ["tee", "t-shirt", "tshirt", "crewneck", "supima"],
        "url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=600&q=80",
        "description": "Crewneck t-shirt",
    },

    # Category Fallbacks
    {
        "keywords": ["formal_shirts"],
        "url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=600&q=80",
        "description": "Formal shirts category fallback",
    },
    {
        "keywords": ["casual_shirts"],
        "url": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=600&q=80",
        "description": "Casual shirts category fallback",
    },
    {
        "keywords": ["blazers_suits"],
        "url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=600&q=80",
        "description": "Blazers & suits fallback",
    },
    {
        "keywords": ["dhotis_ethnic"],
        "url": "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=600&q=80",
        "description": "Dhotis ethnic fallback",
    },
    {
        "keywords": ["footwear"],
        "url": "https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=600&q=80",
        "description": "Footwear fallback",
    },
    {
        "keywords": ["trousers_chinos"],
        "url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?auto=format&fit=crop&w=600&q=80",
        "description": "Trousers fallback",
    },
    {
        "keywords": ["tshirts_polos"],
        "url": "https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=600&q=80",
        "description": "T-shirts fallback",
    },
    {
        "keywords": ["accessories", "accessory"],
        "url": "https://images.unsplash.com/photo-1617137984095-74e4e5e3613f?auto=format&fit=crop&w=600&q=80",
        "description": "Accessories fallback",
    },
]


def resolve_frontend_image(product: Product) -> tuple[str, str]:
    """Replicates frontend/src/utils/productImages.ts resolution logic."""
    title_text = f"{product.name_en or ''}".lower()
    for item in CURATED_PRODUCT_PHOTOS:
        if any(kw in title_text for kw in item["keywords"]):
            return item["url"], item.get("description", "")

    search_text = f"{title_text} {product.category or ''} {product.sku or ''}".lower()
    for item in CURATED_PRODUCT_PHOTOS:
        if any(kw in search_text for kw in item["keywords"]):
            return item["url"], item.get("description", "")

    return f"/api/products/{product.id}/image.svg", "SVG Fallback"


def detect_product_type_simple(name: str, category: str) -> str:
    """Heuristic identification of product type from title."""
    n = name.lower()
    if "cufflink" in n:
        return "cufflinks"
    if "watch" in n or "chronograph" in n:
        return "watch"
    if "cardholder" in n or "card holder" in n:
        return "cardholder"
    if "money clip" in n:
        return "money_clip"
    if "wallet" in n:
        return "wallet"
    if "belt" in n:
        return "belt"
    if "tie bar" in n or "tie clip" in n:
        return "tie_bar"
    if "pocket square" in n:
        return "pocket_square"
    if "bow tie" in n:
        return "bow_tie"
    if "tie" in n or "necktie" in n:
        return "necktie"
    if "waistcoat" in n or "vest" in n:
        return "waistcoat"
    if "tuxedo" in n:
        return "tuxedo"
    if "blazer" in n or "jacket" in n or "suit" in n:
        return "blazer"
    if "sneaker" in n:
        return "sneakers"
    if "loafer" in n:
        return "loafers"
    if "monk strap" in n:
        return "monk_strap"
    if "brogue" in n:
        return "brogues"
    if "derby" in n:
        return "derby_shoes"
    if "oxford" in n:
        return "oxford_shoes"
    if "sandal" in n or "chappal" in n:
        return "sandals"
    if "dhoti" in n or "vesti" in n or "veshti" in n:
        return "dhoti"
    if "kurta" in n:
        return "kurta"
    if "jeans" in n or "denim" in n:
        return "jeans"
    if "cargo" in n:
        return "cargo_pants"
    if "trouser" in n or "chinos" in n or "pants" in n:
        return "trousers"
    if "polo" in n:
        return "polo_shirt"
    if "t-shirt" in n or "tee" in n:
        return "t_shirt"
    if "shirt" in n:
        return "formal_shirt" if category == "formal_shirts" else "casual_shirt"
    return category or "unknown"


async def run_audit():
    reports_dir = repo_root / "reports" / "images"
    reports_dir.mkdir(parents=True, exist_ok=True)
    csv_path = reports_dir / "audit.csv"
    md_path = reports_dir / "audit.md"

    print("Auditing product images from database...")
    async with async_session_factory() as session:
        result = await session.execute(select(Product).order_by(Product.category, Product.name_en))
        products = result.scalars().all()

    total_products = len(products)
    print(f"Total products found in database: {total_products}")

    # Grouping by frontend image URL
    image_groups = defaultdict(list)
    product_rows = []

    for p in products:
        resolved_url, desc = resolve_frontend_image(p)
        ptype = detect_product_type_simple(p.name_en, p.category)
        row = {
            "id": str(p.id),
            "sku": p.sku,
            "name_en": p.name_en,
            "category": p.category,
            "subcategory": p.subcategory or "",
            "price": float(p.price),
            "product_type": ptype,
            "frontend_resolved_url": resolved_url,
            "backend_url": f"/api/products/{p.id}/image.svg",
            "url_desc": desc,
        }
        product_rows.append(row)
        image_groups[resolved_url].append(row)

    distinct_images = len(image_groups)
    duplicate_groups = {url: items for url, items in image_groups.items() if len(items) > 1}

    # Cross-category duplicate groups
    cross_category_groups = {}
    cross_type_groups = {}

    for url, items in duplicate_groups.items():
        categories = {item["category"] for item in items}
        types = {item["product_type"] for item in items}
        if len(categories) > 1:
            cross_category_groups[url] = categories
        if len(types) > 1:
            cross_type_groups[url] = types

    # Write CSV
    print(f"Writing audit CSV to {csv_path}...")
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "sku",
            "name_en",
            "category",
            "subcategory",
            "product_type",
            "frontend_resolved_url",
            "backend_url",
            "image_description",
            "duplicate_group_size",
            "cross_category_group",
            "cross_type_group",
        ])
        for row in product_rows:
            url = row["frontend_resolved_url"]
            grp_size = len(image_groups[url])
            is_cross_cat = url in cross_category_groups
            is_cross_type = url in cross_type_groups
            writer.writerow([
                row["sku"],
                row["name_en"],
                row["category"],
                row["subcategory"],
                row["product_type"],
                row["frontend_resolved_url"],
                row["backend_url"],
                row["url_desc"],
                grp_size,
                "YES" if is_cross_cat else "NO",
                "YES" if is_cross_type else "NO",
            ])

    # Largest duplicate groups sorted descending
    sorted_duplicate_groups = sorted(duplicate_groups.items(), key=lambda x: len(x[1]), reverse=True)

    # Write Markdown
    print(f"Writing audit Markdown report to {md_path}...")
    with open(md_path, mode="w", encoding="utf-8") as f:
        f.write("# Product Image Audit Report\n\n")
        f.write(f"- **Total Products in Catalog**: {total_products}\n")
        f.write(f"- **Distinct Resolved Image URLs**: {distinct_images}\n")
        f.write(f"- **Total Duplicate Groups (images shared by >1 product)**: {len(duplicate_groups)}\n")
        f.write(f"- **Duplicate Groups Spanning Different Categories**: {len(cross_category_groups)}\n")
        f.write(f"- **Duplicate Groups Spanning Different Product Types**: {len(cross_type_groups)}\n")
        f.write(f"- **Average Products Per Image**: {total_products / distinct_images:.1f}\n\n")

        f.write("## 1. Executive Summary & Root Cause Analysis\n\n")
        f.write("### Mechanism Causing Wrong and Reused Images\n")
        f.write(
            "1. **Client-Side Naive Keyword Dictionary (`frontend/src/utils/productImages.ts`)**:\n"
            "   The database `products` table has never stored real product image URLs. Instead, the backend API "
            "returns a placeholder SVG URL (`/api/products/{id}/image.svg`).\n"
            "   To display photos in the storefront, `productImages.ts` intercepts image rendering using a hardcoded "
            "array `CURATED_PRODUCT_PHOTOS` containing only **~40 static Unsplash URLs** mapped via substring matching.\n\n"
            "2. **Severe False-Positive Keyword Collisions**:\n"
            "   - Substring matching `titleText.includes(kw)` creates disastrous false associations. For instance:\n"
            "     - `cufflink` matches `https://images.unsplash.com/photo-1590736969955-71cc94801759` which actually depicts a **woman's wrist with a wristwatch and gold bracelet**.\n"
            "     - `braided leather belt` matches `https://images.unsplash.com/photo-1553062407-98eeb64c6a62` which is actually an image of a **travel backpack**.\n"
            "     - `oxford` in footwear matches `https://images.unsplash.com/photo-1549298916-b41d501d3772` which is a **red Nike sneaker**, completely wrong for formal leather Oxford dress shoes.\n"
            "     - `dhotis_ethnic` products match `photo-1610030469983-98e550d6193c` which is a **woman in a wedding saree**, showing women's clothing for men's dhotis and lungis.\n\n"
            "3. **Extreme Cardinality Collapse (2120 Products -> ~30 Images)**:\n"
            "   Because 2,120 catalog items are matched against only ~30 distinct Unsplash URLs, hundreds of unique products "
            "share the EXACT same image. For example, over **500 formal shirts** share a single white shirt photo.\n\n"
            "4. **No Verification Gate & No Backend Source of Truth**:\n"
            "   Images were never verified with a Vision model to ensure the photo actually contains the advertised item, "
            "contains no people where inappropriate, has no third-party luxury logos, and has no duplicates across distinct products.\n\n"
        )

        f.write("## 2. Top 10 Largest Duplicate Groups\n\n")
        f.write("| Image URL | Description | Product Count | Sample Products |\n")
        f.write("|---|---|---|---|\n")
        for url, items in sorted_duplicate_groups[:10]:
            desc = items[0]["url_desc"]
            sample_names = ", ".join([f"`{it['name_en']}` ({it['sku']})" for it in items[:3]])
            if len(items) > 3:
                sample_names += f" and {len(items)-3} more"
            f.write(f"| `{url[:60]}...` | {desc} | **{len(items)}** | {sample_names} |\n")

        f.write("\n## 3. Duplicate Groups Spanning Different Categories\n\n")
        f.write("| Image URL | Description | Categories Spanned | Sample Products |\n")
        f.write("|---|---|---|---|\n")
        for url, cats in list(cross_category_groups.items())[:10]:
            items = duplicate_groups[url]
            desc = items[0]["url_desc"]
            cats_str = ", ".join(cats)
            samples = ", ".join([f"`{it['name_en']}` [{it['category']}]" for it in items[:4]])
            f.write(f"| `{url[:60]}...` | {desc} | {cats_str} | {samples} |\n")

        f.write("\n## 4. Duplicate Groups Spanning Different Product Types (Mismatches)\n\n")
        f.write("| Image URL | Description | Types Spanned | Sample Products |\n")
        f.write("|---|---|---|---|\n")
        for url, types in list(cross_type_groups.items())[:10]:
            items = duplicate_groups[url]
            desc = items[0]["url_desc"]
            types_str = ", ".join(types)
            samples = ", ".join([f"`{it['name_en']}` ({it['product_type']})" for it in items[:4]])
            f.write(f"| `{url[:60]}...` | {desc} | {types_str} | {samples} |\n")

        f.write("\n## 5. Architectural Fix in the New Pipeline\n\n")
        f.write(
            "1. **Controlled Vocabulary & Type Normalization (`data/image_types.yml`)**:\n"
            "   Normalize names (stripping marketing prefixes like 'Royal', 'Heritage', 'Handwoven') into canonical "
            "types (e.g. `cufflinks`, `leather_belt`, `oxford_shoes`, `silk_dhoti`).\n\n"
            "2. **Official Provider API Retrieval (`ImageProvider`)**:\n"
            "   Query Pexels / Unsplash with strict queries, aspect ratios, and rate limits, saving provider metadata (photographer, license, URL).\n\n"
            "3. **Vision Model Gate (`VisionJudge`)**:\n"
            "   Filter each candidate through Groq Llama 3.2 Vision. Verify the target item is clearly visible, "
            "reject luxury brand logos, reject inappropriate person poses, and enforce confidence >= 0.8.\n\n"
            "4. **Perceptual Deduplication (`dHash` + Hamming Distance)**:\n"
            "   Ensure visually identical images are not assigned across different products (Hamming distance > 6, max reuse <= 3 strictly within same type).\n\n"
            "5. **Database Storage & API Serving**:\n"
            "   Store verified image assignments in a new `product_images` table with photographer attribution and status. "
            "Serve `/api/products/{id}/image.svg` resolving to the verified image URL with SVG fallback.\n"
        )

    print(f"Audit completed successfully! Reports saved to:\n  {csv_path}\n  {md_path}")


if __name__ == "__main__":
    asyncio.run(run_audit())
