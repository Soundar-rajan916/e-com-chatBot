import asyncio
import hashlib
import html
import logging
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.db import get_session
from app.models import Product
from app.schemas import (
    ProductDetailResponse,
    ProductListItemResponse,
    ProductListResponse,
)
from app.services.embeddings import get_embedder
from app.services.vectorstore import get_vector_store

logger = logging.getLogger("app.api.products")
router = APIRouter(prefix="/products", tags=["products"])
categories_router = APIRouter(tags=["products"])

# Color palettes and SVG vector art generators by category
CATEGORY_CONFIG = {
    "formal_shirts": {
        "color1": "#0f172a",
        "color2": "#1e3a8a",
        "svg_art": """<g transform="translate(165, 50)" fill="#ffffff">
      <path d="M10 8 L60 8 L55 78 L15 78 Z" fill="#3b82f6" rx="4" />
      <polygon points="24,8 35,32 46,8" fill="#ffffff" />
      <polygon points="32,15 38,15 36,65 34,65" fill="#dc2626" />
      <circle cx="35" cy="40" r="2" fill="#ffffff" />
      <circle cx="35" cy="52" r="2" fill="#ffffff" />
    </g>""",
    },
    "casual_shirts": {
        "color1": "#065f46",
        "color2": "#0d9488",
        "svg_art": """<g transform="translate(165, 50)" fill="#ffffff">
      <path d="M12 10 L58 10 L54 78 L16 78 Z" fill="#10b981" rx="4" />
      <polygon points="20,10 35,26 50,10" fill="#ecfdf5" />
      <circle cx="35" cy="38" r="2.5" fill="#ffffff" />
      <circle cx="35" cy="52" r="2.5" fill="#ffffff" />
      <circle cx="35" cy="66" r="2.5" fill="#ffffff" />
    </g>""",
    },
    "tshirts_polos": {
        "color1": "#1e293b",
        "color2": "#475569",
        "svg_art": """<g transform="translate(165, 52)" fill="#ffffff">
      <path d="M15 12 L55 12 L50 76 L20 76 Z" fill="#64748b" rx="4" />
      <path d="M5 20 L15 12 L15 36 L7 34 Z" fill="#475569" />
      <path d="M65 20 L55 12 L55 36 L63 34 Z" fill="#475569" />
      <polygon points="28,12 35,22 42,12" fill="#f8fafc" />
    </g>""",
    },
    "trousers_chinos": {
        "color1": "#3b2716",
        "color2": "#78350f",
        "svg_art": """<g transform="translate(165, 50)" fill="#ffffff">
      <path d="M16 10 L54 10 L50 78 L38 78 L35 36 L32 78 L20 78 Z" fill="#d97706" rx="2" />
      <line x1="16" y1="18" x2="54" y2="18" stroke="#ffffff" stroke-width="2" />
      <line x1="35" y1="18" x2="35" y2="34" stroke="#ffffff" stroke-width="1.5" />
    </g>""",
    },
    "blazers_suits": {
        "color1": "#1e1b4b",
        "color2": "#312e81",
        "svg_art": """<g transform="translate(165, 48)" fill="#ffffff">
      <path d="M12 12 L58 12 L52 80 L18 80 Z" fill="#4338ca" rx="4" />
      <polygon points="26,12 35,46 44,12" fill="#ffffff" />
      <polygon points="32,22 38,22 36,58 34,58" fill="#e11d48" />
      <rect x="42" y="32" width="8" height="2" fill="#ffffff" />
      <circle cx="35" cy="58" r="2.5" fill="#fbbf24" />
      <circle cx="35" cy="70" r="2.5" fill="#fbbf24" />
    </g>""",
    },
    "dhotis_ethnic": {
        "color1": "#78350f",
        "color2": "#b45309",
        "svg_art": """<g transform="translate(165, 50)" fill="#ffffff">
      <rect x="18" y="12" width="34" height="68" rx="2" fill="#fef3c7" />
      <rect x="18" y="12" width="6" height="68" fill="#fbbf24" />
      <line x1="24" y1="12" x2="24" y2="80" stroke="#d97706" stroke-width="1" />
      <line x1="38" y1="12" x2="38" y2="80" stroke="#f59e0b" stroke-dasharray="3 3" />
    </g>""",
    },
    "footwear": {
        "color1": "#451a03",
        "color2": "#78350f",
        "svg_art": """<g transform="translate(160, 56)" fill="#ffffff">
      <path d="M8 32 C12 18 30 18 42 22 L62 26 C72 32 72 44 68 46 L8 46 Z" fill="#92400e" />
      <rect x="6" y="44" width="64" height="8" rx="2" fill="#451a03" />
      <rect x="8" y="50" width="16" height="6" fill="#1c1917" />
    </g>""",
    },
    "accessories": {
        "color1": "#18181b",
        "color2": "#3f3f46",
        "svg_art": """<g transform="translate(165, 52)" fill="#ffffff">
      <circle cx="35" cy="38" r="20" stroke="#fbbf24" stroke-width="3" fill="#27272a" />
      <line x1="35" y1="38" x2="35" y2="24" stroke="#fbbf24" stroke-width="2" stroke-linecap="round" />
      <line x1="35" y1="38" x2="44" y2="38" stroke="#fbbf24" stroke-width="2" stroke-linecap="round" />
      <rect x="30" y="4" width="10" height="14" fill="#52525b" rx="2" />
      <rect x="30" y="58" width="10" height="14" fill="#52525b" rx="2" />
    </g>""",
    },
    "mens_wear": {
        "color1": "#0f172a",
        "color2": "#1e3a8a",
        "svg_art": """<g transform="translate(165, 50)" fill="#ffffff">
      <path d="M10 8 L60 8 L55 78 L15 78 Z" fill="#3b82f6" rx="4" />
      <polygon points="24,8 35,32 46,8" fill="#ffffff" />
      <polygon points="32,15 38,15 36,65 34,65" fill="#dc2626" />
      <circle cx="35" cy="40" r="2" fill="#ffffff" />
      <circle cx="35" cy="52" r="2" fill="#ffffff" />
    </g>""",
    },
    "clothing": {
        "color1": "#312e81",
        "color2": "#4f46e5",
        "svg_art": """<g transform="translate(170, 50)" fill="#ffffff">
      <path d="M12 8 C25 4 35 4 48 8 L54 26 C44 30 16 30 6 26 Z" opacity="0.95" />
      <path d="M6 26 L14 78 C24 82 36 82 46 78 L54 26 Z" opacity="0.85" />
      <path d="M8 78 L12 88 C26 91 34 91 48 88 L52 78 Z" fill="#fbbf24" />
      <line x1="20" y1="28" x2="25" y2="78" stroke="#ffffff" stroke-width="1.5" opacity="0.4" />
      <line x1="30" y1="28" x2="33" y2="78" stroke="#ffffff" stroke-width="1.5" opacity="0.4" />
      <line x1="40" y1="28" x2="41" y2="78" stroke="#ffffff" stroke-width="1.5" opacity="0.4" />
    </g>""",
    },
    "sarees": {
        "color1": "#831843",
        "color2": "#be185d",
        "svg_art": """<g transform="translate(165, 50)" fill="#ffffff">
      <path d="M10 10 C25 5 45 5 60 10 L68 30 C50 34 20 34 2 30 Z" opacity="0.95" fill="#fef08a" />
      <path d="M2 30 L12 82 C28 86 42 86 58 82 L68 30 Z" opacity="0.85" />
      <path d="M6 80 L10 90 C30 94 40 94 60 90 L64 80 Z" fill="#fbbf24" />
      <line x1="18" y1="32" x2="22" y2="82" stroke="#fbbf24" stroke-width="2" opacity="0.7" />
      <line x1="32" y1="32" x2="35" y2="82" stroke="#fbbf24" stroke-width="2" opacity="0.7" />
      <line x1="46" y1="32" x2="48" y2="82" stroke="#fbbf24" stroke-width="2" opacity="0.7" />
    </g>""",
    },
    "textiles": {
        "color1": "#831843",
        "color2": "#be185d",
        "svg_art": """<g transform="translate(165, 50)" fill="#ffffff">
      <path d="M10 10 C25 5 45 5 60 10 L68 30 C50 34 20 34 2 30 Z" opacity="0.95" fill="#fef08a" />
      <path d="M2 30 L12 82 C28 86 42 86 58 82 L68 30 Z" opacity="0.85" />
      <path d="M6 80 L10 90 C30 94 40 94 60 90 L64 80 Z" fill="#fbbf24" />
      <line x1="18" y1="32" x2="22" y2="82" stroke="#fbbf24" stroke-width="2" opacity="0.7" />
    </g>""",
    },
    "electronics": {
        "color1": "#0c4a6e",
        "color2": "#0284c7",
        "svg_art": """<g transform="translate(165, 50)" stroke="#ffffff" fill="none" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 48 A 28 28 0 0 1 58 48" stroke-width="5" />
      <rect x="6" y="42" width="12" height="28" rx="6" fill="#38bdf8" stroke="#ffffff" stroke-width="2" />
      <rect x="52" y="42" width="12" height="28" rx="6" fill="#38bdf8" stroke="#ffffff" stroke-width="2" />
      <path d="M2 56 Q 6 56 8 56" stroke="#fef08a" stroke-width="2" />
    </g>""",
    },
    "home & kitchen": {
        "color1": "#7c2d12",
        "color2": "#c2410c",
        "svg_art": """<g transform="translate(160, 52)" fill="#ffffff">
      <ellipse cx="40" cy="22" rx="36" ry="10" fill="#fef08a" opacity="0.9" />
      <path d="M6 22 C6 58 18 70 40 70 C62 70 74 58 74 22 Z" opacity="0.85" />
      <ellipse cx="40" cy="19" rx="8" ry="4" fill="#fbbf24" />
      <path d="M3 24 Q -3 32 3 38 Q 6 38 6 30" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" />
      <path d="M77 24 Q 83 32 77 38 Q 74 38 74 30" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" />
    </g>""",
    },
    "cookware": {
        "color1": "#1c1917",
        "color2": "#44403c",
        "svg_art": """<g transform="translate(160, 52)" fill="#ffffff">
      <ellipse cx="40" cy="22" rx="36" ry="10" fill="#fef08a" opacity="0.9" />
      <path d="M6 22 C6 58 18 70 40 70 C62 70 74 58 74 22 Z" opacity="0.85" />
      <ellipse cx="40" cy="19" rx="8" ry="4" fill="#fbbf24" />
      <path d="M3 24 Q -3 32 3 38 Q 6 38 6 30" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" />
      <path d="M77 24 Q 83 32 77 38 Q 74 38 74 30" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" />
    </g>""",
    },
    "beauty & personal care": {
        "color1": "#831843",
        "color2": "#db2777",
        "svg_art": """<g transform="translate(170, 50)" fill="#ffffff">
      <rect x="25" y="8" width="10" height="14" rx="2" fill="#fbbf24" />
      <rect x="27" y="2" width="6" height="8" rx="3" fill="#f472b6" />
      <rect x="15" y="22" width="30" height="52" rx="6" opacity="0.9" />
      <rect x="19" y="32" width="22" height="30" rx="2" fill="#ffffff" fill-opacity="0.25" />
    </g>""",
    },
    "groceries": {
        "color1": "#064e3b",
        "color2": "#059669",
        "svg_art": """<g transform="translate(160, 52)" fill="#ffffff">
      <path d="M8 32 C8 62 22 72 40 72 C58 72 72 62 72 32 Z" opacity="0.85" />
      <ellipse cx="40" cy="32" rx="32" ry="12" fill="#fef08a" opacity="0.9" />
      <circle cx="34" cy="24" r="3" fill="#fb923c" />
      <circle cx="44" cy="26" r="3.5" fill="#f87171" />
      <circle cx="40" cy="18" r="2.5" fill="#34d399" />
    </g>""",
    },
    "spices": {
        "color1": "#7c2d12",
        "color2": "#ea580c",
        "svg_art": """<g transform="translate(160, 52)" fill="#ffffff">
      <path d="M8 32 C8 62 22 72 40 72 C58 72 72 62 72 32 Z" opacity="0.85" />
      <ellipse cx="40" cy="32" rx="32" ry="12" fill="#fef08a" opacity="0.9" />
      <circle cx="34" cy="24" r="3.5" fill="#ef4444" />
      <circle cx="46" cy="26" r="3" fill="#fbbf24" />
      <circle cx="40" cy="18" r="3" fill="#10b981" />
    </g>""",
    },
    "footwear": {
        "color1": "#1e293b",
        "color2": "#475569",
        "svg_art": """<g transform="translate(155, 60)" fill="#ffffff">
      <path d="M8 36 C18 36 28 16 48 16 C62 16 72 26 78 36 L84 42 C84 48 74 50 8 50 C4 50 4 42 8 36 Z" opacity="0.9" />
      <rect x="6" y="48" width="80" height="7" rx="3" fill="#38bdf8" />
      <path d="M34 18 L44 28" stroke="#ffffff" stroke-width="2" />
      <path d="M42 18 L52 28" stroke="#ffffff" stroke-width="2" />
    </g>""",
    },
    "beverages": {
        "color1": "#451a03",
        "color2": "#9a3412",
        "svg_art": """<g transform="translate(165, 50)" fill="#ffffff">
      <path d="M14 26 L20 72 C22 76 48 76 50 72 L56 26 Z" opacity="0.9" />
      <ellipse cx="35" cy="26" rx="21" ry="8" fill="#fef08a" />
      <path d="M26 16 Q 28 8 30 4" stroke="#ffffff" stroke-width="2" fill="none" opacity="0.7" stroke-linecap="round" />
      <path d="M38 18 Q 40 10 42 6" stroke="#ffffff" stroke-width="2" fill="none" opacity="0.7" stroke-linecap="round" />
    </g>""",
    },
}

DEFAULT_CONFIG = {
    "color1": "#064e3b",
    "color2": "#0f766e",
    "svg_art": """<g transform="translate(165, 50)" fill="#ffffff">
    <rect x="10" y="24" width="50" height="52" rx="8" opacity="0.9" />
    <path d="M22 24 C22 8 48 8 48 24" fill="none" stroke="#fef08a" stroke-width="4" stroke-linecap="round" />
    <path d="M28 44 L42 44" stroke="#064e3b" stroke-width="2.5" opacity="0.5" stroke-linecap="round" />
  </g>""",
}


def get_category_config(category: str) -> dict[str, str]:
    cat_lower = category.lower().strip()
    for key, val in CATEGORY_CONFIG.items():
        if key in cat_lower:
            return val
    return DEFAULT_CONFIG


CATEGORY_ICONS = {
    "formal_shirts": "👔",
    "casual_shirts": "🌿",
    "tshirts_polos": "👕",
    "trousers_chinos": "👖",
    "blazers_suits": "🧥",
    "dhotis_ethnic": "🥻",
    "footwear": "👞",
    "accessories": "⌚",
    "mens_wear": "👔",
}


def get_category_palette(category: str) -> tuple[str, str, str]:
    cfg = get_category_config(category)
    cat_lower = category.lower().strip()
    icon = "👔"
    for key, ic in CATEGORY_ICONS.items():
        if key in cat_lower:
            icon = ic
            break
    return (cfg["color1"], cfg["color2"], icon)


def generate_product_svg(product_id: str, name: str, category: str, price: Decimal) -> str:
    cfg = get_category_config(category)
    color1 = cfg["color1"]
    color2 = cfg["color2"]
    svg_art = cfg["svg_art"]

    safe_name = html.escape(name[:30] + ("..." if len(name) > 30 else ""))
    safe_category = html.escape(category.upper())
    safe_price = f"₹{price:,.2f}"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <defs>
    <linearGradient id="grad_{product_id}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{color1}" />
      <stop offset="100%" stop-color="{color2}" />
    </linearGradient>
  </defs>
  <rect width="400" height="300" fill="url(#grad_{product_id})" rx="14" />
  <rect x="16" y="16" width="368" height="268" fill="#ffffff" fill-opacity="0.08" rx="10" />
  {svg_art}
  <text x="200" y="165" font-family="system-ui, sans-serif" font-size="13" font-weight="700" fill="#ffffff" fill-opacity="0.85" text-anchor="middle" letter-spacing="1.5">{safe_category}</text>
  <text x="200" y="198" font-family="system-ui, sans-serif" font-size="16" font-weight="700" fill="#ffffff" text-anchor="middle">{safe_name}</text>
  <text x="200" y="238" font-family="system-ui, sans-serif" font-size="20" font-weight="800" fill="#fef08a" text-anchor="middle">{safe_price}</text>
</svg>"""


@router.get("/{id_str}/image.svg")
async def get_product_image_svg(
    id_str: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    # Try finding product by ID or SKU with attached product_image
    stmt = select(Product).options(selectinload(Product.image))
    try:
        val_uuid = uuid.UUID(id_str)
        stmt = stmt.where(Product.id == val_uuid)
    except ValueError:
        stmt = stmt.where(Product.sku == id_str)

    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        # Generate generic SVG
        svg_content = generate_product_svg("generic", "Product Image", "Store", Decimal("0.00"))
        etag = f'"{hashlib.md5(svg_content.encode("utf-8")).hexdigest()}"'
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=86400"})
        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=86400", "ETag": etag},
        )

    # If verified or override image exists, redirect 302 to the CDN URL
    if product.image and product.image.status in ("verified", "override") and product.image.url:
        etag = f'"{product.image.phash or str(product.image.id)}"'
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=86400"})
        return Response(
            status_code=302,
            headers={
                "Location": product.image.url,
                "Cache-Control": "public, max-age=86400",
                "ETag": etag,
            },
        )

    # Fallback to generated SVG
    svg_content = generate_product_svg(
        str(product.id), product.name_en, product.category, product.price
    )
    etag = f'"{hashlib.md5(svg_content.encode("utf-8")).hexdigest()}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=86400"})

    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400", "ETag": etag},
    )


@router.get("", response_model=ProductListResponse)
async def list_products(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str | None = Query(None, description="Search query"),
    category: str | None = Query(None, description="Category filter"),
    sort: Literal["newest", "price_asc", "price_desc", "rating_desc"] = Query("newest"),
    min_price: Decimal | None = Query(None, ge=0),
    max_price: Decimal | None = Query(None, ge=0),
    in_stock_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ProductListResponse:
    settings = get_settings()

    # Base conditions
    base_filters = [Product.is_active.is_(True)]
    if category:
        cat_clean = category.lower().strip()
        if cat_clean in ("mens_wear", "menswear", "men", "all"):
            # Whole menswear store catalog - do not restrict by single subcategory
            pass
        elif cat_clean in ("sarees_ethnic", "ethnic", "dhoti", "dhotis"):
            # Map legacy sarees_ethnic / dhoti parameter to active dhotis_ethnic category
            base_filters.append(Product.category == "dhotis_ethnic")
        else:
            base_filters.append(Product.category == category)
    if min_price is not None:
        base_filters.append(Product.price >= min_price)
    if max_price is not None:
        base_filters.append(Product.price <= max_price)
    if in_stock_only:
        base_filters.append(Product.stock_qty > 0)

    # Perform search if q is provided
    product_id_ranks: dict[uuid.UUID, float] = {}

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        # 1. Keyword search matches
        keyword_stmt = (
            select(Product.id)
            .where(
                *base_filters,
                or_(
                    Product.name_en.ilike(search_term),
                    Product.name_ta.ilike(search_term),
                    Product.description_en.ilike(search_term),
                    Product.category.ilike(search_term),
                    Product.sku.ilike(search_term),
                ),
            )
            .limit(100)
        )
        kw_res = await session.execute(keyword_stmt)
        kw_ids = kw_res.scalars().all()
        for rank, p_id in enumerate(kw_ids):
            product_id_ranks[p_id] = product_id_ranks.get(p_id, 0.0) + (1.0 / (60 + rank))

        # 2. Vector search with timeout
        try:
            embedder = get_embedder()
            timeout_sec = settings.PRODUCT_SEARCH_EMBED_TIMEOUT_MS / 1000.0

            async def run_vector():
                q_emb = await embedder.embed_query(q)
                store = get_vector_store()
                return await store.search(
                    session=session,
                    table="products",
                    query_embedding=q_emb,
                    top_k=50,
                    filters={"category": category} if category else None,
                )

            hits = await asyncio.wait_for(run_vector(), timeout=timeout_sec)
            for rank, hit in enumerate(hits):
                product_id_ranks[hit.id] = product_id_ranks.get(hit.id, 0.0) + (1.0 / (60 + rank))
        except Exception as e:
            logger.warning("Vector search fallback to keyword for '%s': %s", q, e)

        if product_id_ranks:
            base_filters.append(Product.id.in_(list(product_id_ranks.keys())))
        else:
            # Query returned no matches
            base_filters.append(Product.id.in_([]))

    # Total count query
    count_stmt = select(func.count(Product.id)).where(*base_filters)
    total = (await session.execute(count_stmt)).scalar() or 0

    # Main data query with eager loaded image
    stmt = select(Product).options(selectinload(Product.image)).where(*base_filters)

    # Sorting
    if product_id_ranks and sort == "newest":
        # Order by RRF fusion rank if search query was executed and default sort
        pass  # We will sort post-fetch or by id order
    elif sort == "price_asc":
        stmt = stmt.order_by(Product.price.asc(), Product.id.asc())
    elif sort == "price_desc":
        stmt = stmt.order_by(Product.price.desc(), Product.id.asc())
    elif sort == "rating_desc":
        stmt = stmt.order_by(Product.rating.desc().nullslast(), Product.id.asc())
    else:
        stmt = stmt.order_by(Product.created_at.desc(), Product.id.asc())

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await session.execute(stmt)
    products = list(result.scalars().all())

    # If sorted by relevance
    if product_id_ranks and sort == "newest":
        products.sort(key=lambda p: product_id_ranks.get(p.id, 0.0), reverse=True)

    # Facets: distinct categories & price bounds
    cat_stmt = select(Product.category).where(Product.is_active.is_(True)).distinct().order_by(Product.category)
    cat_res = await session.execute(cat_stmt)
    categories = [c for c in cat_res.scalars().all() if c]

    price_bounds_stmt = select(
        func.min(Product.price),
        func.max(Product.price),
    ).where(Product.is_active.is_(True))
    bounds_res = await session.execute(price_bounds_stmt)
    p_min, p_max = bounds_res.one()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    item_responses = []
    for p in products:
        img_url = f"/api/products/{p.id}/image.svg"
        credit = None
        img_status = "placeholder"
        if p.image:
            img_status = p.image.status
            if p.image.status in ("verified", "override") and p.image.url:
                img_url = p.image.url
                if p.image.photographer:
                    credit = f"Photo: {p.image.photographer} / {p.image.provider.capitalize()}"

        item_responses.append(
            ProductListItemResponse(
                id=p.id,
                sku=p.sku,
                name_en=p.name_en,
                name_ta=p.name_ta,
                category=p.category,
                subcategory=p.subcategory,
                price=p.price,
                stock_qty=p.stock_qty,
                rating=p.rating,
                image_url=img_url,
                image_credit=credit,
                image_status=img_status,
            )
        )

    return ProductListResponse(
        items=item_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        categories=categories,
        price_min=p_min or Decimal("0.00"),
        price_max=p_max or Decimal("0.00"),
    )


@categories_router.get("/categories")
@router.get("/categories")
async def get_categories(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict]:
    stmt = (
        select(
            Product.category,
            func.count(Product.id).label("count"),
            func.min(Product.price).label("min_price"),
            func.max(Product.price).label("max_price"),
        )
        .where(Product.is_active.is_(True))
        .group_by(Product.category)
        .order_by(Product.category)
    )
    res = await session.execute(stmt)
    rows = res.all()
    return [
        {
            "category": r[0],
            "count": r[1],
            "min_price": r[2],
            "max_price": r[3],
            "icon": get_category_palette(r[0])[2],
        }
        for r in rows
    ]


@router.get("/{id_or_sku}", response_model=ProductDetailResponse)
async def get_product_detail(
    id_or_sku: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProductDetailResponse:
    stmt = select(Product).options(selectinload(Product.image))
    try:
        val_uuid = uuid.UUID(id_or_sku)
        stmt = stmt.where(Product.id == val_uuid)
    except ValueError:
        stmt = stmt.where(Product.sku == id_or_sku)

    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or currently unavailable.",
        )

    img_url = f"/api/products/{product.id}/image.svg"
    credit = None
    img_status = "placeholder"
    if product.image:
        img_status = product.image.status
        if product.image.status in ("verified", "override") and product.image.url:
            img_url = product.image.url
            if product.image.photographer:
                credit = f"Photo: {product.image.photographer} / {product.image.provider.capitalize()}"

    return ProductDetailResponse(
        id=product.id,
        sku=product.sku,
        name_en=product.name_en,
        name_ta=product.name_ta,
        category=product.category,
        subcategory=product.subcategory,
        description_en=product.description_en,
        description_ta=product.description_ta,
        price=product.price,
        stock_qty=product.stock_qty,
        is_active=product.is_active,
        rating=product.rating,
        image_url=img_url,
        image_credit=credit,
        image_status=img_status,
    )


@router.get("/{id_str}/related", response_model=list[ProductListItemResponse])
async def get_related_products(
    id_str: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProductListItemResponse]:
    # Look up base product
    stmt = select(Product)
    try:
        val_uuid = uuid.UUID(id_str)
        stmt = stmt.where(Product.id == val_uuid)
    except ValueError:
        stmt = stmt.where(Product.sku == id_str)

    res = await session.execute(stmt)
    product = res.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    related_stmt = (
        select(Product)
        .options(selectinload(Product.image))
        .where(
            Product.category == product.category,
            Product.id != product.id,
            Product.is_active.is_(True),
        )
        .order_by(Product.rating.desc().nullslast(), Product.created_at.desc())
        .limit(4)
    )
    related_res = await session.execute(related_stmt)
    related_products = list(related_res.scalars().all())

    results = []
    for p in related_products:
        p_img_url = f"/api/products/{p.id}/image.svg"
        p_credit = None
        p_status = "placeholder"
        if p.image:
            p_status = p.image.status
            if p.image.status in ("verified", "override") and p.image.url:
                p_img_url = p.image.url
                if p.image.photographer:
                    p_credit = f"Photo: {p.image.photographer} / {p.image.provider.capitalize()}"

        results.append(
            ProductListItemResponse(
                id=p.id,
                sku=p.sku,
                name_en=p.name_en,
                name_ta=p.name_ta,
                category=p.category,
                subcategory=p.subcategory,
                price=p.price,
                stock_qty=p.stock_qty,
                rating=p.rating,
                image_url=p_img_url,
                image_credit=p_credit,
                image_status=p_status,
            )
        )
    return results
