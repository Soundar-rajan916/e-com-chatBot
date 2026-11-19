"""
Name-Driven Product Image Pipeline Orchestrator
===============================================
End-to-end pipeline:
1. Read the name: derive physical `item`, queries, `must_show`, `must_not_show`, and `people_ok`
   using Groq LLM with strict Pydantic JSON; store in `product_image_plans`.
2. Find candidates: fetch from Pixabay official API per distinct `item` with 24h caching and rate limits.
3. Check photo matches name: relevance gate with Groq Vision (or fake) checking `shows_item`,
   `is_main_subject`, `matches_must_show`, no brand logos/text, no watermarks, no dominant person unless `people_ok`.
4. Deduplication & perceptual hashing (64-bit dHash with Pillow, Hamming <= 6).
5. Deterministic assignment: max reuse <= 2 strictly within same `item`, 0 cross-item reuse.
6. Self-hosting: winner images converted to WebP (800px large, 400px thumb) in `backend/media/products/`.
7. Store in `product_images` table and generate review HTML contact sheet and summary markdown.

Usage:
    python -m scripts.build_product_images [FLAGS]
"""

import argparse
import asyncio
import hashlib
import io
import logging
import os
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env", override=True)

import httpx
from PIL import Image
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from app.db import async_session_factory
from app.models import Product, ProductImage, ProductImagePlan
from app.services.image_pipeline.assigner import DeterministicAssigner
from app.services.image_pipeline.dedup import compute_dhash, hamming_distance
from app.services.image_pipeline.providers import ImageCandidate, get_image_provider
from app.services.image_pipeline.query_writer import get_query_writer
from app.services.image_pipeline.vision import get_vision_judge
from scripts.images_review import generate_review

repo_root = backend_dir.parent
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("build_product_images")


async def run_pipeline(
    dry_run: bool = False,
    max_vision_calls: int | None = None,
    only_category: str | None = None,
    only_sku: str | None = None,
    rebuild: bool = False,
    resume: bool = False,
    skip_download: bool = False,
):
    print("=" * 75)
    print("NAME-DRIVEN PRODUCT IMAGE PIPELINE (PIXABAY & VISION)")
    print("=" * 75)
    print(f"Options: dry_run={dry_run}, max_vision_calls={max_vision_calls}, only_category={only_category}, only_sku={only_sku}")
    print(f"         rebuild={rebuild}, resume={resume}, skip_download={skip_download}")

    cache_dir = repo_root / "data" / "image_cache"
    media_dir = backend_dir / "media" / "products"
    media_dir.mkdir(parents=True, exist_ok=True)

    if rebuild:
        print("Clearing on-disk response caches for rebuild...")
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initialize components
    query_writer = get_query_writer()
    provider = get_image_provider()
    judge = get_vision_judge()
    assigner = DeterministicAssigner()

    # 2. Query Target Products from DB
    async with async_session_factory() as session:
        stmt = (
            select(Product)
            .options(selectinload(Product.image), selectinload(Product.image_plan))
            .order_by(Product.category, Product.sku)
        )
        if only_sku:
            stmt = stmt.where(Product.sku == only_sku)
        if only_category:
            stmt = stmt.where(Product.category.ilike(f"%{only_category}%"))
        res = await session.execute(stmt)
        products = list(res.scalars().all())

    print(f"Loaded {len(products)} products from database.")

    # 3. Read Names: Produce Product Image Plans
    print("\n[Step 1] Reading product names & generating canonical plans...")
    plans_by_sku: dict[str, dict] = {}
    items_by_sku: dict[str, str | None] = {}
    distinct_items = defaultdict(list)

    for p in products:
        plan = await query_writer.plan_product(
            product_id=str(p.id),
            name_en=p.name_en,
            category=p.category,
            subcategory=p.subcategory,
            description_en=p.description_en,
        )
        plans_by_sku[p.sku] = plan.model_dump()
        items_by_sku[p.sku] = plan.item
        if plan.item:
            distinct_items[plan.item].append(p.sku)

    print(f"Generated plans: {len(distinct_items)} distinct physical items across {len(products)} products.")
    null_items_count = sum(1 for item in items_by_sku.values() if item is None)
    print(f"Products with item=null (vague names, placeholder fallback): {null_items_count}")

    # Persist plans to product_image_plans table if not dry_run
    if not dry_run:
        async with async_session_factory() as session:
            for p in products:
                plan_data = plans_by_sku[p.sku]
                stmt = (
                    pg_insert(ProductImagePlan)
                    .values(
                        product_id=p.id,
                        item=plan_data["item"],
                        queries=plan_data["queries"],
                        must_show=plan_data["must_show"],
                        must_not_show=plan_data["must_not_show"],
                        people_ok=plan_data["people_ok"],
                        status="planned",
                    )
                    .on_conflict_do_update(
                        index_elements=["product_id"],
                        set_={
                            "item": plan_data["item"],
                            "queries": plan_data["queries"],
                            "must_show": plan_data["must_show"],
                            "must_not_show": plan_data["must_not_show"],
                            "people_ok": plan_data["people_ok"],
                            "status": "planned",
                            "updated_at": datetime.now(timezone.utc),
                        },
                    )
                )
                await session.execute(stmt)
            await session.commit()
            print("Successfully persisted plans to `product_image_plans` table.")

    # DRY RUN REPORTING & COST ESTIMATE
    if dry_run:
        print("\n" + "=" * 50)
        print("DRY RUN SUMMARY & COST ESTIMATE")
        print("=" * 50)
        print(f"Total Products Analyzed: {len(products)}")
        print(f"Distinct Items: {len(distinct_items)}")
        print(f"Products with Null Item: {null_items_count}")
        print("\nTop Items with Product Counts:")
        for it, skus in sorted(distinct_items.items(), key=lambda x: -len(x[1]))[:15]:
            print(f"  - '{it}': {len(skus)} products")

        print("\nSample 30 Product Names & Planned Queries:")
        sample_products = products[:30]
        for sp in sample_products:
            p_plan = plans_by_sku.get(sp.sku, {})
            print(f"  • {sp.sku}: '{sp.name_en}' -> Item: '{p_plan.get('item')}' | Queries: {p_plan.get('queries')}")

        planned_candidates_fetch = len(distinct_items)
        # Vision calls estimate: up to 5 candidates evaluated per item
        est_vision_calls = len(distinct_items) * 4
        # Cost per 1,000 requests on Groq Llama 3.2 Vision (~$0.05 per 1,000 tokens / ~$0.0001 per image)
        est_cost_usd = est_vision_calls * 0.0001
        print("\nEstimated API Calls & Cost:")
        print(f"  - Pixabay API Searches Planned: {planned_candidates_fetch}")
        print(f"  - Estimated Vision Judge Calls: {est_vision_calls}")
        print(f"  - Estimated Groq Vision Cost: ${est_cost_usd:.4f} USD")
        print("\n[DRY RUN COMPLETE] No network downloads or image table mutations performed.")
        return

    # Check API key before proceeding with real network pipeline
    if provider.name == "pixabay" and not os.getenv("PIXABAY_API_KEY"):
        print("\n[NOTICE] PIXABAY_API_KEY is not configured in environment.")
        print("The pipeline will cleanly keep products on the SVG placeholder.")
        print("To enable Pixabay downloads, set PIXABAY_API_KEY in backend/.env")
        # Proceed with empty candidates so assigner marks items as missing/placeholder cleanly
        pass

    # Group products category by category
    categories_map = defaultdict(list)
    for p in products:
        categories_map[p.category].append(p)

    vision_calls_made = 0
    total_assigned_count = 0

    print(f"\nProcessing {len(categories_map)} categories category-by-category...")

    for category_name, cat_products in categories_map.items():
        print(f"\n--- Processing Category: '{category_name}' ({len(cat_products)} products) ---")
        cat_items = set()
        for p in cat_products:
            item = items_by_sku.get(p.sku)
            if item:
                cat_items.add(item)

        # 4. Fetch Candidates per distinct item
        verified_candidates_by_item: dict[str, list[tuple[ImageCandidate, float, dict]]] = defaultdict(list)

        for item in sorted(cat_items):
            if max_vision_calls is not None and vision_calls_made >= max_vision_calls:
                break
            # Find a representative product plan for this item
            rep_plan = next(
                (plans_by_sku[p.sku] for p in cat_products if items_by_sku.get(p.sku) == item),
                None,
            )
            if not rep_plan:
                continue

            search_queries = rep_plan.get("queries", [item])
            must_show = rep_plan.get("must_show", "")
            must_not_show = rep_plan.get("must_not_show", "")
            people_ok = rep_plan.get("people_ok", False)

            candidates = await provider.fetch_candidates(
                item=item,
                search_queries=search_queries,
                max_candidates=10,
            )

            # Compute dHash for candidates to filter near duplicates
            for cand in candidates:
                if not cand.dhash:
                    if skip_download or not cand.preview_url:
                        cand.dhash = hashlib.sha256(cand.id.encode("utf-8")).hexdigest()[:16]
                    else:
                        try:
                            async with httpx.AsyncClient(timeout=8.0) as client:
                                r = await client.get(cand.preview_url)
                                if r.status_code == 200:
                                    cand.dhash = compute_dhash(r.content)
                                else:
                                    cand.dhash = hashlib.sha256(cand.id.encode("utf-8")).hexdigest()[:16]
                        except Exception:
                            cand.dhash = hashlib.sha256(cand.id.encode("utf-8")).hexdigest()[:16]

            # 5. Vision Judge Verification
            for cand in candidates:
                if max_vision_calls is not None and vision_calls_made >= max_vision_calls:
                    print(f"Reached max vision calls limit ({max_vision_calls}). Halting further vision checks.")
                    break

                verdict = await judge.judge_candidate(
                    candidate=cand,
                    item=item,
                    must_show=must_show,
                    must_not_show=must_not_show,
                    people_ok=people_ok,
                )
                vision_calls_made += 1

                if verdict.is_accepted:
                    score = float(verdict.confidence * verdict.quality) if verdict.confidence and verdict.quality else float(verdict.confidence)
                    verified_candidates_by_item[item].append((cand, score, verdict.model_dump()))
                    # Early stop for this item once we have enough distinct candidates
                    item_products_count = sum(1 for p in cat_products if items_by_sku.get(p.sku) == item)
                    needed_cands = max(2, (item_products_count + 1) // 2)
                    if len(verified_candidates_by_item[item]) >= needed_cands:
                        break

        # 6. Run Deterministic Assignment for this category
        cat_assignments = assigner.assign(
            products=cat_products,
            items_by_sku=items_by_sku,
            verified_candidates_by_item=verified_candidates_by_item,
        )

        # 7. Self-Host winning images (download only winning images, convert to WebP)
        for res in cat_assignments:
            if res.status == "verified" and res.provider_photo_id and res.provider == "pixabay" and not skip_download:
                try:
                    # Find candidate object
                    target_cand = None
                    for c_list in verified_candidates_by_item.values():
                        for cand, _, _ in c_list:
                            if cand.provider_photo_id == res.provider_photo_id:
                                target_cand = cand
                                break
                        if target_cand:
                            break

                    if target_cand:
                        local_path, url_large, url_thumb = await provider.download_and_self_host(target_cand, media_dir)
                        res.local_path = local_path
                        res.image_url_large = url_large
                        res.image_url_thumb = url_thumb
                except Exception as e:
                    logger.warning("Failed to self-host image for SKU %s: %s", res.sku, e)

        # 8. Persist assignments for this category to PostgreSQL
        async with async_session_factory() as session:
            for res in cat_assignments:
                score_dec = Decimal(f"{res.score:.3f}") if res.score is not None else None
                stmt = (
                    pg_insert(ProductImage)
                    .values(
                        product_id=res.product_id,
                        provider=res.provider,
                        provider_photo_id=res.provider_photo_id,
                        source_page_url=res.page_url,
                        photographer=res.photographer,
                        photographer_url=res.photographer_url,
                        licence=res.licence,
                        credit_text=res.credit_text,
                        image_url_large=res.image_url_large,
                        image_url_thumb=res.image_url_thumb,
                        local_path=res.local_path,
                        width=res.width,
                        height=res.height,
                        phash=res.phash,
                        status=res.status,
                        score=score_dec,
                        verdict=res.verdict,
                        assigned_at=datetime.now(timezone.utc),
                    )
                    .on_conflict_do_update(
                        index_elements=["product_id"],
                        set_={
                            "provider": res.provider,
                            "provider_photo_id": res.provider_photo_id,
                            "source_page_url": res.page_url,
                            "photographer": res.photographer,
                            "photographer_url": res.photographer_url,
                            "licence": res.licence,
                            "credit_text": res.credit_text,
                            "image_url_large": res.image_url_large,
                            "image_url_thumb": res.image_url_thumb,
                            "local_path": res.local_path,
                            "width": res.width,
                            "height": res.height,
                            "phash": res.phash,
                            "status": res.status,
                            "score": score_dec,
                            "verdict": res.verdict,
                            "assigned_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc),
                        },
                    )
                )
                await session.execute(stmt)
            await session.commit()
            print(f"Persisted {len(cat_assignments)} assignments for category '{category_name}'.")
            total_assigned_count += len(cat_assignments)

        if max_vision_calls is not None and vision_calls_made >= max_vision_calls:
            print(f"Reached max vision calls ({max_vision_calls}). Halting further category runs.")
            break

    # 9. Generate review HTML contact sheet and summary markdown
    print("\n[Step 7] Generating Review Reports...")
    await generate_review()

    print("\n" + "=" * 75)
    print(f"PIPELINE RUN COMPLETED! Total assignments processed: {total_assigned_count}")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="Name-Driven Product Image Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Generate plan and cost estimate without writing DB")
    parser.add_argument("--max-vision-calls", type=int, default=None, help="Stop after N vision judge calls")
    parser.add_argument("--only-category", type=str, default=None, help="Process one specific category only")
    parser.add_argument("--only-sku", type=str, default=None, help="Process one specific SKU only")
    parser.add_argument("--rebuild", action="store_true", help="Clear caches and rebuild")
    parser.add_argument("--resume", action="store_true", help="Resume previous run")
    parser.add_argument("--skip-download", action="store_true", help="Fast mode without image downloads")

    args = parser.parse_args()
    asyncio.run(
        run_pipeline(
            dry_run=args.dry_run,
            max_vision_calls=args.max_vision_calls,
            only_category=args.only_category,
            only_sku=args.only_sku,
            rebuild=args.rebuild,
            resume=args.resume,
            skip_download=args.skip_download,
        )
    )


if __name__ == "__main__":
    main()
