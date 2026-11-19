"""
Static HTML Contact Sheet and Review Tooling
============================================
Generates reports/images/review.html and reports/images/summary.md
for human review of all product image assignments.

Usage:
    python -m scripts.images_review
"""

import asyncio
import os
import sys
from collections import defaultdict
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import async_session_factory
from app.models import Product, ProductImage, ProductImagePlan

repo_root = backend_dir.parent


async def generate_review():
    reports_dir = repo_root / "reports" / "images"
    reports_dir.mkdir(parents=True, exist_ok=True)
    html_path = reports_dir / "review.html"
    summary_path = reports_dir / "summary.md"

    print("Fetching products, plans, and image assignments from database...")
    async with async_session_factory() as session:
        res = await session.execute(
            select(Product)
            .options(selectinload(Product.image), selectinload(Product.image_plan))
            .order_by(Product.category, Product.name_en)
        )
        products = list(res.scalars().all())

    total_products = len(products)
    status_counts = defaultdict(int)
    item_counts = defaultdict(int)
    assigned_records = []
    image_usage_counts = defaultdict(list)  # (provider, photo_id) -> list of (item, sku)

    for p in products:
        item = p.image_plan.item if p.image_plan else None
        status = "missing"
        img_url = f"/api/products/{p.id}/image.svg"
        credit = "SVG Vector Fallback"
        provider = "svg"
        confidence = 0.0
        reason = ""
        photo_id = ""

        if p.image:
            status = p.image.status
            img_url = p.image.image_url_large or p.image.local_path or f"/api/products/{p.id}/image.svg"
            provider = p.image.provider
            photo_id = p.image.provider_photo_id or ""
            credit = p.image.credit_text or (f"Photo: {p.image.photographer} / {provider.capitalize()}" if p.image.photographer else "Verified")
            if p.image.score is not None:
                confidence = float(p.image.score)
            if p.image.verdict and isinstance(p.image.verdict, dict):
                reason = p.image.verdict.get("reason", "")
                if not reason and "rejection_reasons" in p.image.verdict:
                    reason = ", ".join(p.image.verdict["rejection_reasons"])
            if p.image.status == "verified" and photo_id:
                image_usage_counts[(provider, photo_id)].append((item, p.sku))

        status_counts[status] += 1
        if item:
            item_counts[item] += 1

        assigned_records.append({
            "id": str(p.id),
            "sku": p.sku,
            "name_en": p.name_en,
            "name_ta": p.name_ta,
            "category": p.category,
            "subcategory": p.subcategory or "",
            "item": item or "None (Vague/Untyped)",
            "status": status,
            "img_url": img_url,
            "credit": credit,
            "provider": provider,
            "photo_id": photo_id,
            "confidence": confidence,
            "reason": reason,
        })

    # Metrics calculation
    verified_count = status_counts["verified"]
    needs_review_count = status_counts["needs_review"]
    rejected_count = status_counts["rejected"]
    missing_count = status_counts["missing"]
    coverage_pct = (verified_count / total_products * 100) if total_products else 0.0

    distinct_images = len(image_usage_counts)
    max_reuse = max((len(skus) for skus in image_usage_counts.values()), default=0)

    # Check cross-item duplicates
    cross_item_dups = []
    for (prov, pid), usages in image_usage_counts.items():
        used_items = {it for it, _ in usages if it}
        if len(used_items) > 1:
            cross_item_dups.append({"photo": f"{prov}:{pid}", "items": list(used_items), "usages": usages})

    # Sort records: needs_review and missing first, then lowest confidence
    def sort_key(r):
        status_priority = {"needs_review": 0, "missing": 1, "rejected": 2, "verified": 3}
        return (status_priority.get(r["status"], 4), r["confidence"], r["item"], r["sku"])

    sorted_records = sorted(assigned_records, key=sort_key)

    # Group by item for the HTML contact sheet
    records_by_item = defaultdict(list)
    for r in sorted_records:
        records_by_item[r["item"]].append(r)

    # 1. Generate reports/images/summary.md
    print(f"Generating summary report at {summary_path}...")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# Product Image Pipeline - Summary Report\n\n")
        f.write(f"- **Total Products**: {total_products}\n")
        f.write(f"- **Verified Photo Assigned**: {verified_count} ({coverage_pct:.1f}%)\n")
        f.write(f"- **Needs Review (Marginal Confidence)**: {needs_review_count}\n")
        f.write(f"- **Rejected by Guardrails**: {rejected_count}\n")
        f.write(f"- **Missing / Placeholder Fallback**: {missing_count}\n")
        f.write(f"- **Distinct Verified Images**: {distinct_images}\n")
        f.write(f"- **Maximum Image Reuse**: {max_reuse} (Strict limit <= 2)\n")
        f.write(f"- **Cross-Item Duplicates**: {len(cross_item_dups)} (MUST BE 0)\n\n")

        if cross_item_dups:
            f.write("### WARNING: Cross-Item Duplicates Detected!\n")
            for dup in cross_item_dups:
                f.write(f"- Photo `{dup['photo']}` shared across items: {dup['items']}\n")
            f.write("\n")
        else:
            f.write("✅ **Zero cross-item duplicate image sharing verified.**\n\n")

        # 20 Lowest-confidence assignments
        f.write("### 20 Lowest-Confidence Assignments\n\n")
        f.write("| SKU | Product Name (EN) | Item | Status | Score | Reason |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        lowest_20 = sorted([r for r in assigned_records if r["confidence"] > 0], key=lambda x: x["confidence"])[:20]
        if not lowest_20:
            f.write("| - | No scored assignments yet | - | - | - | - |\n")
        for r in lowest_20:
            f.write(f"| `{r['sku']}` | {r['name_en']} | {r['item']} | `{r['status']}` | {r['confidence']:.2f} | {r['reason'] or '-'} |\n")
        f.write("\n")

        # Items with too few good photos
        f.write("### Items with Insufficient Photos (SVG Placeholder Fallback)\n\n")
        f.write("| Item | Total Products | Verified | Missing | Action Needed |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        items_summary = defaultdict(lambda: {"total": 0, "verified": 0, "missing": 0})
        for r in assigned_records:
            items_summary[r["item"]]["total"] += 1
            if r["status"] == "verified":
                items_summary[r["item"]]["verified"] += 1
            else:
                items_summary[r["item"]]["missing"] += 1

        for it, counts in sorted(items_summary.items(), key=lambda x: -x[1]["missing"]):
            if counts["missing"] > 0:
                action = "Expand queries, check second provider, or supply local image in `data/image_overrides.csv`"
                f.write(f"| {it} | {counts['total']} | {counts['verified']} | {counts['missing']} | {action} |\n")
        f.write("\n")

    # 2. Generate reports/images/review.html
    print(f"Generating static HTML contact sheet at {html_path}...")
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Product Image Review Contact Sheet</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #f8fafc;
      color: #0f172a;
      margin: 0;
      padding: 24px;
    }}
    header {{
      background: #ffffff;
      padding: 24px;
      border-radius: 12px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
      margin-bottom: 24px;
    }}
    h1 {{ margin: 0 0 12px 0; font-size: 24px; }}
    .stats-bar {{
      display: flex;
      gap: 20px;
      font-size: 14px;
      color: #475569;
      flex-wrap: wrap;
    }}
    .stat {{ background: #f1f5f9; padding: 6px 14px; border-radius: 6px; font-weight: 600; }}
    .override-box {{
      background: #1e293b;
      color: #e2e8f0;
      padding: 16px;
      border-radius: 8px;
      font-family: monospace;
      font-size: 13px;
      margin-top: 16px;
      overflow-x: auto;
    }}
    .item-section {{
      background: #ffffff;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 28px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }}
    .item-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid #f1f5f9;
      padding-bottom: 12px;
      margin-bottom: 16px;
    }}
    .item-title {{ font-size: 18px; font-weight: 700; color: #1e293b; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 16px;
    }}
    .card {{
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
      background: #ffffff;
      display: flex;
      flex-direction: column;
    }}
    .card.needs_review {{ border-color: #f59e0b; box-shadow: 0 0 0 2px #fef3c7; }}
    .card.missing {{ border-color: #cbd5e1; opacity: 0.9; }}
    .img-wrap {{
      width: 100%;
      height: 220px;
      background: #f1f5f9;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }}
    .img-wrap img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .card-body {{
      padding: 12px;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .sku {{ font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; }}
    .name-en {{ font-size: 14px; font-weight: 600; line-height: 1.3; }}
    .name-ta {{ font-size: 12px; color: #64748b; }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      align-self: flex-start;
    }}
    .badge.verified {{ background: #dcfce7; color: #15803d; }}
    .badge.needs_review {{ background: #fef3c7; color: #b45309; }}
    .badge.missing {{ background: #f1f5f9; color: #64748b; }}
    .badge.rejected {{ background: #fee2e2; color: #b91c1c; }}
    .reason {{ font-size: 11px; color: #dc2626; background: #fff1f2; padding: 4px 8px; border-radius: 4px; }}
    .credit {{ font-size: 10px; color: #94a3b8; margin-top: auto; padding-top: 6px; }}
  </style>
</head>
<body>
  <header>
    <h1>Product Image Review Contact Sheet</h1>
    <div class="stats-bar">
      <div class="stat">Total Products: {total_products}</div>
      <div class="stat">Verified Photos: {verified_count} ({coverage_pct:.1f}%)</div>
      <div class="stat">Needs Review: {needs_review_count}</div>
      <div class="stat">Missing / SVG: {missing_count}</div>
      <div class="stat">Distinct Photos: {distinct_images}</div>
      <div class="stat">Max Reuse: {max_reuse} (Limit: 2)</div>
      <div class="stat">Cross-Item Dups: {len(cross_item_dups)}</div>
    </div>
    <div style="margin-top: 14px; font-size: 13px; color: #64748b;">
      Copy-ready override syntax for <code>data/image_overrides.csv</code>:
      <code>sku,provider_photo_id,force,notes</code> (or <code>sku,reject,force,notes</code>).
    </div>
  </header>
"""

    for item_name, items in sorted(records_by_item.items()):
        html_content += f"""
  <div class="item-section">
    <div class="item-header">
      <div class="item-title">{item_name} ({len(items)} products)</div>
    </div>
    <div class="grid">
"""
        for it in items:
            status_cls = it["status"]
            badge_cls = it["status"]
            html_content += f"""
      <div class="card {status_cls}">
        <div class="img-wrap">
          <img src="{it['img_url']}" alt="{it['name_en']}" loading="lazy" />
        </div>
        <div class="card-body">
          <div class="sku">{it['sku']}</div>
          <div class="name-en">{it['name_en']}</div>
          <div class="name-ta">{it['name_ta']}</div>
          <span class="badge {badge_cls}">{it['status']} {f'({it["confidence"]:.2f})' if it["confidence"] else ''}</span>
          {f'<div class="reason">{it["reason"]}</div>' if it["reason"] else ''}
          <div class="credit">{it['credit']}</div>
        </div>
      </div>
"""
        html_content += """
    </div>
  </div>
"""

    html_content += """
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Review contact sheet generated successfully at {html_path}")


if __name__ == "__main__":
    asyncio.run(generate_review())
