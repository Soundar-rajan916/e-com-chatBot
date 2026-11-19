"""
Product & Media Amazon S3 Sync CLI Tool
======================================
Synchronizes product images, thumbnails, category vectors, and the catalog JSON
from local repositories into Amazon S3 with CloudFront CDN acceleration,
and updates the database `product_images` table with production URLs.

Usage:
    python -m scripts.sync_products_to_s3 [OPTIONS]

Options:
    --bucket TEXT      S3 bucket name (default: from AWS_S3_BUCKET_NAME env)
    --region TEXT      AWS region (default: from AWS_REGION env or ap-south-1)
    --domain TEXT      CloudFront or custom CDN domain (e.g. d12345.cloudfront.net)
    --dry-run          Preview files and database updates without uploading
    --catalog-only     Sync only catalog/products.json
    --images-only      Sync only product images and thumbnails
    --skip-db          Do not update PostgreSQL database records
"""

import argparse
import asyncio
import json
import logging
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

load_dotenv(backend_dir / ".env", override=True)

from sqlalchemy import select, update
from app.config import get_settings
from app.db import async_session_factory
from app.models import Product, ProductImage

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("sync_products_to_s3")

ROOT_DIR = backend_dir.parent


def discover_image_assets(root: Path) -> dict[str, Path]:
    """Discovers all local product and catalog image files and maps them to their S3 keys."""
    assets: dict[str, Path] = {}

    # 1. Backend media products (supports both container /app/media and host repo /backend/media)
    backend_media_candidates = [
        backend_dir / "media" / "products",
        root / "backend" / "media" / "products",
    ]
    for backend_media in backend_media_candidates:
        if backend_media.exists():
            for p in backend_media.rglob("*"):
                if p.is_file() and p.suffix.lower() in (".webp", ".jpg", ".jpeg", ".png", ".svg"):
                    rel = p.relative_to(backend_media)
                    key = f"products/{rel.as_posix()}"
                    assets[key] = p

    # 2. Frontend public product images
    fe_products = root / "frontend" / "public" / "images" / "products"
    if fe_products.exists():
        for p in fe_products.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".webp", ".jpg", ".jpeg", ".png", ".svg"):
                rel = p.relative_to(fe_products)
                key = f"products/{rel.as_posix()}"
                if key not in assets:
                    assets[key] = p

    # 3. Frontend public category and hero images
    for sub in ("categories", "hero", "promos"):
        folder = root / "frontend" / "public" / "images" / sub
        if folder.exists():
            for p in folder.rglob("*"):
                if p.is_file() and p.suffix.lower() in (".webp", ".jpg", ".jpeg", ".png", ".svg"):
                    rel = p.relative_to(folder)
                    key = f"{sub}/{rel.as_posix()}"
                    assets[key] = p

    return assets


def get_public_url(key: str, bucket: str, region: str, domain: str | None = None) -> str:
    """Generates the public HTTPS URL for an S3 key."""
    clean_key = key.lstrip("/")
    if domain:
        clean_domain = domain.strip().rstrip("/")
        if not clean_domain.startswith("http"):
            clean_domain = f"https://{clean_domain}"
        return f"{clean_domain}/{clean_key}"
    return f"https://{bucket}.s3.{region}.amazonaws.com/{clean_key}"


async def sync_catalog_and_images(
    bucket: str,
    region: str,
    domain: str | None,
    dry_run: bool = False,
    catalog_only: bool = False,
    images_only: bool = False,
    skip_db: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    s3_client = None

    if not dry_run:
        try:
            import boto3
            from botocore.config import Config

            session_kwargs: dict[str, Any] = {"region_name": region}
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                session_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
                session_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

            s3_client = boto3.client(
                "s3",
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                config=Config(signature_version="s3v4"),
                **session_kwargs,
            )
        except Exception as e:
            logger.error("Failed to initialize boto3 S3 client: %s", e)
            logger.info("Tip: You can run with --dry-run to test and preview uploads without AWS credentials.")
            return {"success": False, "error": str(e)}

    stats = {
        "images_found": 0,
        "images_uploaded": 0,
        "catalog_uploaded": False,
        "db_rows_updated": 0,
    }

    # --- 1. Images Sync ---
    if not catalog_only:
        assets = discover_image_assets(ROOT_DIR)
        stats["images_found"] = len(assets)
        print(f"\nDiscovered {len(assets)} local image assets across backend and frontend.")

        for key, local_file in sorted(assets.items()):
            content_type, _ = mimetypes.guess_type(str(local_file))
            content_type = content_type or "application/octet-stream"
            file_size_kb = local_file.stat().st_size / 1024
            public_url = get_public_url(key, bucket, region, domain)

            if dry_run:
                print(f" [DRY-RUN] Would upload {key} ({file_size_kb:.1f} KB, {content_type}) -> {public_url}")
                stats["images_uploaded"] += 1
            else:
                try:
                    s3_client.upload_file(
                        str(local_file),
                        bucket,
                        key,
                        ExtraArgs={
                            "ContentType": content_type,
                            "CacheControl": "public, max-age=31536000, immutable",
                        },
                    )
                    print(f" [UPLOADED] {key} ({file_size_kb:.1f} KB) -> {public_url}")
                    stats["images_uploaded"] += 1
                except Exception as e:
                    logger.error("Failed uploading %s to S3: %s", key, e)

    # --- 2. Catalog JSON Sync ---
    if not images_only:
        catalog_path = backend_dir / "data" / "products.json"
        if catalog_path.exists():
            catalog_key = "catalog/products.json"
            catalog_url = get_public_url(catalog_key, bucket, region, domain)
            size_kb = catalog_path.stat().st_size / 1024

            if dry_run:
                print(f"\n [DRY-RUN] Would upload catalog {catalog_key} ({size_kb:.1f} KB) -> {catalog_url}")
                stats["catalog_uploaded"] = True
            else:
                try:
                    s3_client.upload_file(
                        str(catalog_path),
                        bucket,
                        catalog_key,
                        ExtraArgs={
                            "ContentType": "application/json",
                            "CacheControl": "public, max-age=300, must-revalidate",
                        },
                    )
                    print(f"\n [UPLOADED] Catalog {catalog_key} ({size_kb:.1f} KB) -> {catalog_url}")
                    stats["catalog_uploaded"] = True
                except Exception as e:
                    logger.error("Failed uploading catalog to S3: %s", e)

    # --- 3. Update PostgreSQL Database Records ---
    if not skip_db:
        print("\nUpdating PostgreSQL product_images records to point to S3 / CloudFront URLs...")
        async with async_session_factory() as session:
            stmt = select(ProductImage)
            res = await session.execute(stmt)
            images = res.scalars().all()

            updated_count = 0
            for img in images:
                # If local_path or image_url_large points to /media/products/...
                ref_path = img.image_url_large or img.local_path
                if ref_path and "/media/products/" in ref_path:
                    filename = Path(ref_path).name
                    s3_key = f"products/{filename}"
                    s3_large = get_public_url(s3_key, bucket, region, domain)

                    thumb_key = s3_key
                    if img.image_url_thumb and "/media/products/" in img.image_url_thumb:
                        thumb_name = Path(img.image_url_thumb).name
                        thumb_key = f"products/{thumb_name}"
                    s3_thumb = get_public_url(thumb_key, bucket, region, domain)

                    if dry_run:
                        updated_count += 1
                    else:
                        img.image_url_large = s3_large
                        img.image_url_thumb = s3_thumb
                        img.status = "verified"
                        updated_count += 1

            if not dry_run and updated_count > 0:
                await session.commit()

            stats["db_rows_updated"] = updated_count
            mode_prefix = "[DRY-RUN] Would update" if dry_run else "[UPDATED]"
            print(f" {mode_prefix} {updated_count} product_images rows in PostgreSQL.")

    return stats


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Synchronize products and media assets to Amazon S3")
    parser.add_argument("--bucket", default=settings.AWS_S3_BUCKET_NAME, help="Amazon S3 bucket name")
    parser.add_argument("--region", default=settings.AWS_REGION, help="AWS region (e.g. ap-south-1)")
    parser.add_argument("--domain", default=settings.AWS_S3_CUSTOM_DOMAIN, help="CloudFront or custom CDN domain")
    parser.add_argument("--dry-run", action="store_true", help="Preview sync and database changes without writing")
    parser.add_argument("--catalog-only", action="store_true", help="Sync only catalog/products.json")
    parser.add_argument("--images-only", action="store_true", help="Sync only product images")
    parser.add_argument("--skip-db", action="store_true", help="Skip updating PostgreSQL records")

    args = parser.parse_args()

    print("=" * 70)
    print("REGIONAL BAZAAR — AMAZON S3 PRODUCT SYNC")
    print("=" * 70)
    print(f"Bucket:    {args.bucket}")
    print(f"Region:    {args.region}")
    print(f"CDN Domain: {args.domain or '(Direct S3 URLs)'}")
    print(f"Dry Run:   {args.dry_run}")
    print("=" * 70)

    result = asyncio.run(
        sync_catalog_and_images(
            bucket=args.bucket,
            region=args.region,
            domain=args.domain,
            dry_run=args.dry_run,
            catalog_only=args.catalog_only,
            images_only=args.images_only,
            skip_db=args.skip_db,
        )
    )

    print("\nSync Summary:")
    print(f" - Images Discovered: {result.get('images_found', 0)}")
    print(f" - Images Synced:     {result.get('images_uploaded', 0)}")
    print(f" - Catalog Synced:    {result.get('catalog_uploaded', False)}")
    print(f" - DB Rows Updated:   {result.get('db_rows_updated', 0)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
