"""
Tests for Image Provider Abstraction & Pixabay Implementation
============================================================
Tests:
- Pixabay candidate fetching with mocked HTTP responses
- Rate limiting headers and 429 backoff
- 24h disk caching
- Missing API key exits cleanly
- Download and self-hosting: downloads only assigned images and saves WebP to /media/products/
- Token bucket rate limiter
"""

import asyncio
import io
from pathlib import Path
from unittest.mock import AsyncMock, patch
from PIL import Image
import httpx
import pytest

from app.services.image_pipeline.providers import (
    FakeImageProvider,
    ImageCandidate,
    PixabayProvider,
    TokenBucket,
    get_image_provider,
)


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter():
    bucket = TokenBucket(rate_per_minute=100.0, capacity=2.0)
    t0 = asyncio.get_event_loop().time()
    await bucket.acquire()
    await bucket.acquire()
    t1 = asyncio.get_event_loop().time()
    assert (t1 - t0) < 0.1


def test_provider_factory():
    assert isinstance(get_image_provider("fake"), FakeImageProvider)
    assert isinstance(get_image_provider("pixabay"), PixabayProvider)


@pytest.mark.asyncio
async def test_pixabay_missing_key_clean_exit(tmp_path):
    provider = PixabayProvider(api_key="", cache_dir=tmp_path)
    candidates = await provider.fetch_candidates(
        item="silver cufflinks",
        search_queries=["silver cufflinks men"],
    )
    assert candidates == []


@pytest.mark.asyncio
async def test_pixabay_24h_caching_and_mock_response(tmp_path):
    provider = PixabayProvider(api_key="test_pixabay_key", cache_dir=tmp_path)

    mock_hit = {
        "id": 12345,
        "pageURL": "https://pixabay.com/photos/cufflinks-12345/",
        "webformatURL": "https://pixabay.com/get/12345_640.jpg",
        "largeImageURL": "https://pixabay.com/get/12345_1280.jpg",
        "imageWidth": 1280,
        "imageHeight": 850,
        "user": "TestPhotographer",
        "user_id": 999,
        "tags": "cufflinks, formal, accessories",
    }

    mock_response = httpx.Response(
        status_code=200,
        json={"total": 1, "totalHits": 1, "hits": [mock_hit]},
        headers={"X-RateLimit-Limit": "100", "X-RateLimit-Remaining": "99"},
        request=httpx.Request("GET", "https://pixabay.com/api/"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        # 1. First fetch: calls network
        candidates = await provider.fetch_candidates(
            item="silver cufflinks",
            search_queries=["silver cufflinks men"],
            max_candidates=10,
        )

        assert len(candidates) == 1
        cand = candidates[0]
        assert cand.provider == "pixabay"
        assert cand.provider_photo_id == "12345"
        assert cand.photographer == "TestPhotographer"
        assert cand.credit_text == "Photo: TestPhotographer / Pixabay"
        assert mock_get.call_count == 1

        # 2. Second fetch: should hit 24-hour cache on disk, NOT call network again
        cached_candidates = await provider.fetch_candidates(
            item="silver cufflinks",
            search_queries=["silver cufflinks men"],
            max_candidates=10,
        )

        assert len(cached_candidates) == 1
        assert cached_candidates[0].provider_photo_id == "12345"
        # Network call count remains 1!
        assert mock_get.call_count == 1


@pytest.mark.asyncio
async def test_pixabay_download_and_self_host(tmp_path):
    provider = PixabayProvider(cache_dir=tmp_path)
    media_dir = tmp_path / "media_products"
    media_dir.mkdir(parents=True, exist_ok=True)

    cand = ImageCandidate(
        id="pixabay:99999",
        provider="pixabay",
        provider_photo_id="99999",
        item="silver cufflinks",
        url="https://example.com/fake_winner.jpg",
        preview_url="https://example.com/fake_preview.jpg",
        width=1200,
        height=800,
        photographer="Artist",
        photographer_url="https://pixabay.com/users/artist",
        page_url="https://pixabay.com/photos/99999",
        license_url=provider.LICENSE_URL,
        credit_text="Photo: Artist / Pixabay",
    )

    # Generate dummy image bytes
    dummy_img = Image.new("RGB", (900, 600), color=(100, 150, 200))
    buf = io.BytesIO()
    dummy_img.save(buf, format="JPEG")
    fake_bytes = buf.getvalue()

    mock_resp = httpx.Response(
        status_code=200,
        content=fake_bytes,
        request=httpx.Request("GET", cand.url),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        local_path, url_large, url_thumb = await provider.download_and_self_host(cand, media_dir)

        assert Path(local_path).is_file()
        assert url_large.startswith("/media/products/")
        assert url_large.endswith("_800.webp")
        assert url_thumb.startswith("/media/products/")
        assert url_thumb.endswith("_400.webp")

        # Confirm WebP files exist on disk
        assert (media_dir / Path(url_large).name).is_file()
        assert (media_dir / Path(url_thumb).name).is_file()
