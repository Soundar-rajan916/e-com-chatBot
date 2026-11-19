"""
Tests for Product Image API Serving & Attribution
=================================================
Verifies:
- Product image SVG fallback when no verified photo exists (200 with SVG, Cache-Control, ETag, 304 on If-None-Match)
- 302 redirect to self-hosted image URL when photo is verified
- Additive fields: image_credit and image_status in product list and detail API responses
"""

import uuid
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, ProductImage


@pytest.mark.asyncio
async def test_product_image_svg_fallback(client: AsyncClient, db_session: AsyncSession):
    # Create product without verified image
    p = Product(
        sku=f"SKU-TEST-SVG-{uuid.uuid4().hex[:6]}",
        name_en="Test Cufflinks Without Photo",
        name_ta="டெஸ்ட்",
        category="accessories",
        description_en="Description",
        description_ta="விளக்கம்",
        price=Decimal("1500.00"),
        stock_qty=10,
        content_hash="abc",
        embedding=[0.0] * 384,
    )
    db_session.add(p)
    await db_session.commit()

    resp = await client.get(f"/products/{p.id}/image.svg")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/svg+xml")
    assert "public, max-age=86400" in resp.headers["cache-control"]
    assert "ETag" in resp.headers

    # Test 304 Not Modified
    etag = resp.headers["ETag"]
    resp304 = await client.get(f"/products/{p.id}/image.svg", headers={"If-None-Match": etag})
    assert resp304.status_code == 304


@pytest.mark.asyncio
async def test_product_image_302_redirect_when_verified(client: AsyncClient, db_session: AsyncSession):
    # Create product with verified image
    p = Product(
        sku=f"SKU-TEST-VER-{uuid.uuid4().hex[:6]}",
        name_en="Test Oxford Shoes Verified",
        name_ta="டெஸ்ட்",
        category="footwear",
        description_en="Description",
        description_ta="விளக்கம்",
        price=Decimal("3500.00"),
        stock_qty=5,
        content_hash="abc2",
        embedding=[0.0] * 384,
    )
    db_session.add(p)
    await db_session.flush()

    img = ProductImage(
        product_id=p.id,
        provider="pixabay",
        provider_photo_id="12345",
        image_url_large="/media/products/test_shoes_800.webp",
        image_url_thumb="/media/products/test_shoes_400.webp",
        status="verified",
        photographer="Jane Doe",
        photographer_url="https://pixabay.com/users/janedoe",
        score=Decimal("0.95"),
    )
    db_session.add(img)
    await db_session.commit()

    # Request without following redirects
    resp = await client.get(f"/products/{p.id}/image.svg", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/media/products/test_shoes_800.webp"
    assert "ETag" in resp.headers
    assert "public, max-age=86400" in resp.headers["cache-control"]


@pytest.mark.asyncio
async def test_product_detail_and_list_contain_image_credit_and_status(client: AsyncClient, db_session: AsyncSession):
    p = Product(
        sku=f"SKU-TEST-ATTR-{uuid.uuid4().hex[:6]}",
        name_en="Test Attributed Blazer",
        name_ta="டெஸ்ட்",
        category="blazers_suits",
        description_en="Description",
        description_ta="விளக்கம்",
        price=Decimal("7500.00"),
        stock_qty=2,
        content_hash="abc3",
        embedding=[0.0] * 384,
    )
    db_session.add(p)
    await db_session.flush()

    img = ProductImage(
        product_id=p.id,
        provider="pixabay",
        provider_photo_id="999",
        image_url_large="/media/products/test_blazer_800.webp",
        image_url_thumb="/media/products/test_blazer_400.webp",
        status="verified",
        photographer="John Smith",
        photographer_url="https://pixabay.com/users/johnsmith",
        score=Decimal("0.98"),
    )
    db_session.add(img)
    await db_session.commit()

    # Detail API
    resp = await client.get(f"/products/{p.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["image_status"] == "verified"
    assert data["image_url"] == "/media/products/test_blazer_800.webp"
    assert "John Smith" in (data.get("image_credit") or "")

    # List API
    list_resp = await client.get("/products?category=blazers_suits")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    found = next((item for item in items if item["sku"] == p.sku), None)
    assert found is not None
    assert found["image_status"] == "verified"
    assert found["image_url"] == "/media/products/test_blazer_800.webp"
    assert "John Smith" in (found.get("image_credit") or "")
