import asyncio
import hashlib
import json
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_factory, engine
from app.models import Product
from app.services.embeddings import get_embedder


def compute_product_text(p: dict[str, Any]) -> str:
    """Combines multilingual product attributes into an embeddable text representation."""
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


async def ingest_products(
    session: AsyncSession, products_data: list[dict[str, Any]], batch_size: int = 64
) -> tuple[int, int, int]:
    embedder = get_embedder()
    print("Loading existing products to evaluate hash differences...")

    # Map existing products by SKU
    stmt = select(Product)
    res = await session.execute(stmt)
    existing_products: dict[str, Product] = {p.sku: p for p in res.scalars().all()}
    print(f"Found {len(existing_products)} existing products in database.")

    to_process: list[tuple[dict[str, Any], str, str, Any]] = []
    skipped = 0
    added = 0
    updated = 0

    for p in products_data:
        sku = p["sku"]
        embed_text = compute_product_text(p)
        content_hash = compute_content_hash(embed_text, p["price"], p["stock_qty"])
        existing = existing_products.get(sku)

        if existing and existing.content_hash == content_hash:
            skipped += 1
            continue

        to_process.append((p, embed_text, content_hash, existing))

    total_to_process = len(to_process)
    print(f"Products to embed and save: {total_to_process} ({skipped} skipped as unchanged).")

    for i in range(0, total_to_process, batch_size):
        batch = to_process[i : i + batch_size]
        texts = [item[1] for item in batch]
        print(
            f"  Embedding batch {i // batch_size + 1}/{(total_to_process + batch_size - 1) // batch_size} ({len(batch)} items)..."
        )

        embeddings = await embedder.embed_documents(texts)

        for (p, embed_text, content_hash, existing), emb in zip(batch, embeddings):
            price_dec = Decimal(str(p["price"]))
            rating_dec = Decimal(str(p["rating"])) if p.get("rating") is not None else None

            if existing:
                existing.name_en = p["name_en"]
                existing.name_ta = p["name_ta"]
                existing.category = p["category"]
                existing.subcategory = p.get("subcategory")
                existing.description_en = p["description_en"]
                existing.description_ta = p["description_ta"]
                existing.price = price_dec
                existing.stock_qty = p["stock_qty"]
                existing.rating = rating_dec
                existing.content_hash = content_hash
                existing.embedding = emb
                updated += 1
            else:
                new_prod = Product(
                    id=uuid.uuid4(),
                    sku=p["sku"],
                    name_en=p["name_en"],
                    name_ta=p["name_ta"],
                    category=p["category"],
                    subcategory=p.get("subcategory"),
                    description_en=p["description_en"],
                    description_ta=p["description_ta"],
                    price=price_dec,
                    stock_qty=p["stock_qty"],
                    rating=rating_dec,
                    content_hash=content_hash,
                    embedding=emb,
                )
                session.add(new_prod)
                added += 1

        await session.commit()

    return added, updated, skipped


async def main():
    json_path = Path(__file__).resolve().parent.parent / "data" / "products.json"
    if not json_path.exists():
        print(f"Error: {json_path} not found. Run scripts/generate_products.py first.")
        return

    with open(json_path, encoding="utf-8") as f:
        products_data = json.load(f)

    print(f"Loaded {len(products_data)} products from {json_path.name}.")
    async with async_session_factory() as session:
        added, updated, skipped = await ingest_products(session, products_data)

    print("\n" + "=" * 50)
    print("PRODUCT INGESTION COMPLETE:")
    print(f"  Added:   {added}")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")
    print("=" * 50)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
