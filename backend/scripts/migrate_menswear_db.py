import asyncio
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_factory, engine
from app.models import Product, CartItem
from app.services.embeddings import get_embedder

MENSWEAR_CATEGORIES = [
    "formal_shirts",
    "casual_shirts",
    "tshirts_polos",
    "trousers_chinos",
    "blazers_suits",
    "dhotis_ethnic",
    "footwear",
    "accessories",
]


def compute_product_text(p: dict[str, Any]) -> str:
    parts = [
        p.get("name_en", ""),
        p.get("name_ta", ""),
        f"Category: {p.get('category', '')}",
    ]
    if p.get("subcategory"):
        parts.append(f"Subcategory: {p['subcategory']}")
    parts.append(p.get("description_en", ""))
    parts.append(p.get("description_ta", ""))
    return " | ".join(filter(None, parts))


def compute_content_hash(text: str, price: Any, stock: Any) -> str:
    payload = f"{text}|{price}|{stock}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def run_migration():
    json_path = Path(__file__).resolve().parent.parent / "data" / "products.json"
    with open(json_path, "r", encoding="utf-8") as f:
        products_data = json.load(f)

    print(f"Loaded {len(products_data)} menswear products from {json_path.name}")

    active_skus = {p["sku"] for p in products_data}

    async with async_session_factory() as session:
        # 1. Deactivate all products not in active menswear catalog or categories
        print("Deactivating all non-menswear products...")
        deactivate_stmt = (
            update(Product)
            .where(
                (Product.category.not_in(MENSWEAR_CATEGORIES))
                | (Product.sku.not_in(list(active_skus)))
            )
            .values(is_active=False)
        )
        res_deact = await session.execute(deactivate_stmt)
        print(f"Deactivated {res_deact.rowcount} non-menswear or obsolete products.")

        # Clean cart items referencing inactive products
        clean_cart_stmt = delete(CartItem).where(
            CartItem.product_id.in_(
                select(Product.id).where(Product.is_active.is_(False))
            )
        )
        res_cart = await session.execute(clean_cart_stmt)
        print(f"Removed {res_cart.rowcount} cart items for inactive products.")

        await session.commit()

        # 2. Ingest / Upsert all menswear items
        embedder = get_embedder()
        print("Upserting and embedding active menswear products...")

        stmt = select(Product)
        res = await session.execute(stmt)
        existing_products: dict[str, Product] = {p.sku: p for p in res.scalars().all()}

        to_process: list[tuple[dict[str, Any], str, str, Product | None]] = []
        skipped = 0

        for p in products_data:
            sku = p["sku"]
            embed_text = compute_product_text(p)
            content_hash = compute_content_hash(embed_text, p["price"], p["stock_qty"])
            existing = existing_products.get(sku)

            if existing and existing.content_hash == content_hash and existing.is_active is True:
                skipped += 1
                continue

            to_process.append((p, embed_text, content_hash, existing))

        print(f"Products to embed and upsert: {len(to_process)} ({skipped} skipped as identical).")

        batch_size = 64
        total_batches = (len(to_process) + batch_size - 1) // batch_size if to_process else 0

        for i in range(0, len(to_process), batch_size):
            batch = to_process[i : i + batch_size]
            texts = [item[1] for item in batch]
            print(f"  Embedding batch {i // batch_size + 1}/{total_batches} ({len(batch)} items)...")

            embeddings = await embedder.embed_documents(texts)

            for (p, embed_text, content_hash, existing), emb in zip(batch, embeddings):
                price_dec = Decimal(str(p["price"]))
                rating_dec = Decimal(str(p["rating"])) if p.get("rating") is not None else None

                if existing:
                    existing.name_en = p["name_en"]
                    existing.name_ta = p["name_ta"]
                    existing.category = p["category"]
                    existing.subcategory = p.get("subcategory")
                    existing.description_en = p.get("description_en", "")
                    existing.description_ta = p.get("description_ta", "")
                    existing.price = price_dec
                    existing.stock_qty = p.get("stock_qty", 0)
                    existing.rating = rating_dec
                    existing.content_hash = content_hash
                    existing.embedding = emb
                    existing.is_active = True
                else:
                    new_p = Product(
                        sku=p["sku"],
                        name_en=p["name_en"],
                        name_ta=p["name_ta"],
                        category=p["category"],
                        subcategory=p.get("subcategory"),
                        description_en=p.get("description_en", ""),
                        description_ta=p.get("description_ta", ""),
                        price=price_dec,
                        stock_qty=p.get("stock_qty", 0),
                        rating=rating_dec,
                        content_hash=content_hash,
                        embedding=emb,
                        is_active=True,
                    )
                    session.add(new_p)

            await session.commit()

        # 3. Validation query
        check_stmt = (
            select(Product.category, func.count(Product.id))
            .where(Product.is_active.is_(True))
            .group_by(Product.category)
            .order_by(Product.category)
        )
        res_check = await session.execute(check_stmt)
        active_counts = res_check.all()

        print("\n=== Active Database Categories Verification ===")
        total_active = 0
        for cat, cnt in active_counts:
            print(f"  {cat}: {cnt} items")
            total_active += cnt
        print(f"Total Active Men's Wear Products in DB: {total_active}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migration())
