import asyncio
import hashlib
import html
import logging
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

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

# Color palettes by category for SVG placeholder generation
CATEGORY_PALETTES = {
    "clothing": ("#4f46e5", "#818cf8", "👕"),
    "electronics": ("#0369a1", "#38bdf8", "📱"),
    "home & kitchen": ("#c2410c", "#fb923c", "🍳"),
    "beauty & personal care": ("#be185d", "#f472b6", "✨"),
    "books & media": ("#15803d", "#4ade80", "📚"),
    "groceries": ("#047857", "#34d399", "🛒"),
    "toys & baby": ("#b45309", "#fbbf24", "🧸"),
    "sports & fitness": ("#0f766e", "#2dd4bf", "⚽"),
}
DEFAULT_PALETTE = ("#6d28d9", "#a78bfa", "🛍️")


def get_category_palette(category: str) -> tuple[str, str, str]:
    cat_lower = category.lower().strip()
    for key, val in CATEGORY_PALETTES.items():
        if key in cat_lower:
            return val
    # Stable fallback based on category string hash
    h = int(hashlib.md5(category.encode("utf-8")).hexdigest()[:4], 16)
    palettes = list(CATEGORY_PALETTES.values())
    return palettes[h % len(palettes)]


def generate_product_svg(product_id: str, name: str, category: str, price: Decimal) -> str:
    color1, color2, icon = get_category_palette(category)
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
  <rect width="400" height="300" fill="url(#grad_{product_id})" rx="12" />
  <rect x="20" y="20" width="360" height="260" fill="#ffffff" fill-opacity="0.1" rx="8" />
  <text x="200" y="110" font-family="system-ui, sans-serif" font-size="54" text-anchor="middle">{icon}</text>
  <text x="200" y="160" font-family="system-ui, sans-serif" font-size="14" font-weight="600" fill="#ffffff" fill-opacity="0.85" text-anchor="middle" letter-spacing="1.5">{safe_category}</text>
  <text x="200" y="195" font-family="system-ui, sans-serif" font-size="16" font-weight="700" fill="#ffffff" text-anchor="middle">{safe_name}</text>
  <text x="200" y="235" font-family="system-ui, sans-serif" font-size="20" font-weight="800" fill="#fef08a" text-anchor="middle">{safe_price}</text>
</svg>"""


@router.get("/{id_str}/image.svg")
async def get_product_image_svg(
    id_str: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    # Try finding product by ID or SKU
    stmt = select(Product)
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
    else:
        svg_content = generate_product_svg(
            str(product.id), product.name_en, product.category, product.price
        )

    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
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

    # Main data query
    stmt = select(Product).where(*base_filters)

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

    return ProductListResponse(
        items=[
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
                image_url=f"/api/products/{p.id}/image.svg",
            )
            for p in products
        ],
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
    stmt = select(Product)
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
        image_url=f"/api/products/{product.id}/image.svg",
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
        .where(
            Product.category == product.category,
            Product.id != product.id,
            Product.is_active.is_(True),
            Product.stock_qty > 0,
        )
        .order_by(Product.rating.desc().nullslast(), Product.stock_qty.desc())
        .limit(4)
    )
    rel_res = await session.execute(related_stmt)
    related = rel_res.scalars().all()

    return [
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
            image_url=f"/api/products/{p.id}/image.svg",
        )
        for p in related
    ]
