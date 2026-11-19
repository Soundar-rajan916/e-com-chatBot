"""
Product Types CLI and Reporting Tool
====================================
Prints summary of product types, counts of products classified per type,
and lists unclassified products.

Usage:
    python -m scripts.image_types --report
"""

import argparse
import asyncio
import sys
from collections import defaultdict
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.db import async_session_factory
from app.models import Product
from app.services.image_pipeline.classifier import ImageClassifier


async def generate_types_report():
    classifier = ImageClassifier()
    all_types = {t.id: t for t in classifier.list_types()}

    print("\n" + "=" * 70)
    print("PRODUCT TYPE NORMALIZATION REPORT")
    print("=" * 70)

    async with async_session_factory() as session:
        res = await session.execute(select(Product).order_by(Product.category, Product.name_en))
        products = res.scalars().all()

    total_products = len(products)
    type_counts = defaultdict(int)
    type_examples = defaultdict(list)
    unclassified = []

    for p in products:
        ptype, confidence, rule = classifier.classify(p.name_en, p.category, p.subcategory)
        if ptype:
            type_counts[ptype] += 1
            if len(type_examples[ptype]) < 3:
                type_examples[ptype].append(f"{p.name_en} ({p.sku})")
        else:
            unclassified.append(p)

    classified_count = total_products - len(unclassified)
    print(f"\nTotal Products: {total_products}")
    print(f"Classified: {classified_count} ({classified_count / total_products * 100:.1f}%)")
    print(f"Unclassified (Fallback to SVG): {len(unclassified)} ({len(unclassified) / total_products * 100:.1f}%)\n")

    print("-" * 70)
    print(f"{'TYPE ID':<25} | {'COUNT':<6} | {'DISPLAY NAME':<22} | SAMPLES")
    print("-" * 70)

    for type_id in sorted(all_types.keys()):
        count = type_counts[type_id]
        t = all_types[type_id]
        samples = ", ".join(type_examples[type_id][:2])
        if count > 0:
            print(f"{type_id:<25} | {count:<6} | {t.display_name:<22} | {samples}")

    if unclassified:
        print("\n" + "-" * 70)
        print(f"UNCLASSIFIED PRODUCTS ({len(unclassified)} items will retain SVG placeholder):")
        print("-" * 70)
        for p in unclassified[:15]:
            print(f"- [{p.category}] {p.name_en} ({p.sku})")
        if len(unclassified) > 15:
            print(f"... and {len(unclassified) - 15} more.")

    print("\n" + "=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Product Types Inspector & Reporter")
    parser.add_argument("--report", action="store_true", help="Generate classification report across database")
    args = parser.parse_args()

    if args.report:
        asyncio.run(generate_types_report())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
