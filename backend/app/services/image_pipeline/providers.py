"""
Image Provider Abstraction & Implementations
============================================
Fetches candidate stock images from official Pixabay API (primary) or Unsplash.
Implements rate limiting, 24-hour disk caching (per Pixabay terms), in-memory
preview inspection, and self-hosting of assigned images via Pillow WebP conversion.
"""

import asyncio
import hashlib
import io
import json
import logging
import os
import time
import urllib.parse
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import httpx
from PIL import Image
from pydantic import BaseModel, Field

logger = logging.getLogger("app.services.image_pipeline.providers")


class ImageCandidate(BaseModel):
    id: str  # e.g. pixabay:12345
    provider: str  # pixabay | unsplash | fake
    provider_photo_id: str
    item: str
    url: str  # Original URL (used strictly for temporary download upon assignment)
    preview_url: str  # Low-res preview URL used temporarily for VisionJudge
    thumbnail_url: str | None = None
    width: int
    height: int
    photographer: str
    photographer_url: str
    page_url: str
    license_url: str
    credit_text: str
    tags: str = ""
    dhash: str | None = None
    image_url_large: str | None = None  # Self-hosted /media/products/... URL
    image_url_thumb: str | None = None  # Self-hosted /media/products/... URL
    local_path: str | None = None


class TokenBucket:
    """Async token bucket rate limiter to stay within API rate limits."""

    def __init__(self, rate_per_minute: float = 90.0, capacity: float = 90.0):
        self.rate = rate_per_minute / 60.0  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

            if self.tokens < 1.0:
                needed = 1.0 - self.tokens
                wait_time = needed / self.rate
                logger.debug("Rate limit token bucket sleeping for %.2fs", wait_time)
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
                self.last_update = time.monotonic()
            else:
                self.tokens -= 1.0


@runtime_checkable
class ImageProvider(Protocol):
    name: str

    async def fetch_candidates(
        self,
        item: str,
        search_queries: list[str],
        max_candidates: int = 20,
    ) -> list[ImageCandidate]:
        ...

    async def download_and_self_host(
        self,
        candidate: ImageCandidate,
        media_dir: Path,
    ) -> tuple[str, str, str]:
        """Downloads assigned image and creates 800px and 400px WebP files."""
        ...


class BaseProvider:
    def __init__(self, cache_dir: Path | str | None = None, rate_limit_per_min: float = 90.0):
        if cache_dir is None:
            cache_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "image_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limiter = TokenBucket(rate_per_minute=rate_limit_per_min)

    def _get_cache_path(self, provider_name: str, item: str, query: str) -> Path:
        q_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:12]
        safe_item = item.replace(" ", "_").replace("/", "_")
        return self.cache_dir / f"{provider_name}_{safe_item}_{q_hash}.json"

    def _read_cache(self, path: Path, min_valid_seconds: int = 86400) -> list[dict] | None:
        """Reads cache if present and newer than min_valid_seconds (default 24h per Pixabay terms)."""
        if path.is_file():
            try:
                mtime = path.stat().st_mtime
                if (time.time() - mtime) < min_valid_seconds:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception as e:
                logger.warning("Failed to read cache at %s: %s", path, e)
        return None

    def _write_cache(self, path: Path, data: list[dict]):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to write cache at %s: %s", path, e)

    @staticmethod
    def process_and_save_webp(image_bytes: bytes, dest_dir: Path, file_prefix: str) -> tuple[str, str, str]:
        """
        Resizes assigned image into large (800px) and thumb (400px) WebP formats.
        Returns: (local_file_path, image_url_large, image_url_thumb)
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")

        # Large: max 800px on longest side
        img_large = img.copy()
        img_large.thumbnail((800, 800), Image.Resampling.LANCZOS)
        large_filename = f"{file_prefix}_800.webp"
        large_path = dest_dir / large_filename
        img_large.save(large_path, format="WEBP", quality=85)

        # Thumb: max 400px on longest side
        img_thumb = img.copy()
        img_thumb.thumbnail((400, 400), Image.Resampling.LANCZOS)
        thumb_filename = f"{file_prefix}_400.webp"
        thumb_path = dest_dir / thumb_filename
        img_thumb.save(thumb_path, format="WEBP", quality=85)

        url_large = f"/media/products/{large_filename}"
        url_thumb = f"/media/products/{thumb_filename}"
        return str(large_path), url_large, url_thumb


class PixabayProvider(BaseProvider):
    name = "pixabay"
    BASE_URL = "https://pixabay.com/api/"
    LICENSE_URL = "https://pixabay.com/service/license-summary/"

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: Path | str | None = None,
        rate_limit_per_min: float = 90.0,
    ):
        super().__init__(cache_dir=cache_dir, rate_limit_per_min=rate_limit_per_min)
        self.api_key = api_key or os.getenv("PIXABAY_API_KEY", "")

    async def fetch_candidates(
        self,
        item: str,
        search_queries: list[str],
        max_candidates: int = 20,
    ) -> list[ImageCandidate]:
        all_candidates: list[ImageCandidate] = []
        seen_ids = set()

        for query in search_queries:
            if len(all_candidates) >= max_candidates:
                break

            # Truncate query to 100 characters per Pixabay API specification
            safe_query = query[:100].strip()
            if not safe_query:
                continue

            cache_path = self._get_cache_path(self.name, item, safe_query)
            cached_data = self._read_cache(cache_path, min_valid_seconds=86400)

            if cached_data is not None:
                for entry in cached_data:
                    c = ImageCandidate(**entry)
                    if c.provider_photo_id not in seen_ids:
                        seen_ids.add(c.provider_photo_id)
                        all_candidates.append(c)
                continue

            if not self.api_key:
                logger.debug("PIXABAY_API_KEY not configured; skipping network fetch for: %s", safe_query)
                continue

            await self.rate_limiter.acquire()
            params = {
                "key": self.api_key,
                "q": safe_query,
                "image_type": "photo",
                "orientation": "vertical",
                "safesearch": "true",
                "min_width": 400,
                "min_height": 400,
                "per_page": min(max_candidates, 50),
            }

            raw_hits = []
            for attempt in range(3):
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.get(self.BASE_URL, params=params)
                        if resp.status_code == 429:
                            reset_sec = int(resp.headers.get("X-RateLimit-Reset", "5"))
                            wait = max(reset_sec, 2 ** (attempt + 1))
                            logger.warning("Pixabay 429 Rate Limit hit. Backing off %ds...", wait)
                            await asyncio.sleep(wait)
                            continue
                        resp.raise_for_status()
                        data = resp.json()
                        raw_hits = data.get("hits", [])
                        break
                except Exception as e:
                    logger.warning("Pixabay API attempt %d error for '%s': %s", attempt + 1, safe_query, e)
                    if attempt < 2:
                        await asyncio.sleep(1.5 * (attempt + 1))

            query_candidates = []
            for hit in raw_hits:
                photo_id = str(hit.get("id"))
                img_url = hit.get("largeImageURL") or hit.get("webformatURL")
                preview_url = hit.get("previewURL") or hit.get("webformatURL") or img_url
                user_name = hit.get("user", "Pixabay Contributor")
                user_id = str(hit.get("user_id", ""))
                photographer_url = f"https://pixabay.com/users/{user_name}-{user_id}/" if user_id else "https://pixabay.com"

                cand = ImageCandidate(
                    id=f"pixabay:{photo_id}",
                    provider="pixabay",
                    provider_photo_id=photo_id,
                    item=item,
                    url=img_url,
                    preview_url=preview_url,
                    width=hit.get("imageWidth", 0),
                    height=hit.get("imageHeight", 0),
                    photographer=user_name,
                    photographer_url=photographer_url,
                    page_url=hit.get("pageURL", "https://pixabay.com"),
                    license_url=self.LICENSE_URL,
                    credit_text=f"Photo: {user_name} / Pixabay",
                    tags=hit.get("tags", ""),
                )
                query_candidates.append(cand.model_dump())
                if photo_id not in seen_ids:
                    seen_ids.add(photo_id)
                    all_candidates.append(cand)

            self._write_cache(cache_path, query_candidates)

        return all_candidates[:max_candidates]

    async def download_and_self_host(
        self,
        candidate: ImageCandidate,
        media_dir: Path,
    ) -> tuple[str, str, str]:
        """
        Downloads ONLY the assigned winning photo and converts to WebP.
        Never bulk-downloads unassigned candidates.
        """
        prefix = hashlib.sha256(f"pixabay:{candidate.provider_photo_id}".encode("utf-8")).hexdigest()[:16]
        large_path = media_dir / f"{prefix}_800.webp"
        thumb_path = media_dir / f"{prefix}_400.webp"

        if large_path.is_file() and thumb_path.is_file():
            return str(large_path), f"/media/products/{prefix}_800.webp", f"/media/products/{prefix}_400.webp"

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(candidate.url)
            resp.raise_for_status()
            image_bytes = resp.content

        return self.process_and_save_webp(image_bytes, media_dir, prefix)


class FakeImageProvider(BaseProvider):
    """Deterministic test mock for ImageProvider."""
    name = "fake"

    def __init__(self, candidates_per_item: int = 5):
        super().__init__()
        self.candidates_per_item = candidates_per_item
        self.download_calls = []

    async def fetch_candidates(
        self,
        item: str,
        search_queries: list[str],
        max_candidates: int = 20,
    ) -> list[ImageCandidate]:
        candidates = []
        for i in range(min(self.candidates_per_item, max_candidates)):
            pid = f"fake_{item.replace(' ', '_')}_{i+1}"
            candidates.append(
                ImageCandidate(
                    id=f"fake:{pid}",
                    provider="fake",
                    provider_photo_id=pid,
                    item=item,
                    url=f"https://images.example.com/{pid}.jpg",
                    preview_url=f"https://images.example.com/{pid}_preview.jpg",
                    width=800,
                    height=1200,
                    photographer="Test Artist",
                    photographer_url="https://example.com/artist",
                    page_url=f"https://example.com/photos/{pid}",
                    license_url="https://example.com/license",
                    credit_text="Photo: Test Artist / Fake",
                    tags=item,
                )
            )
        return candidates

    async def download_and_self_host(
        self,
        candidate: ImageCandidate,
        media_dir: Path,
    ) -> tuple[str, str, str]:
        self.download_calls.append(candidate.id)
        # Generate dummy 1x1 image for testing
        dummy_img = Image.new("RGB", (100, 100), color=(120, 150, 200))
        buf = io.BytesIO()
        dummy_img.save(buf, format="JPEG")
        prefix = hashlib.sha256(candidate.id.encode("utf-8")).hexdigest()[:16]
        return self.process_and_save_webp(buf.getvalue(), media_dir, prefix)


def get_image_provider(provider_name: str | None = None) -> ImageProvider:
    name = (provider_name or os.getenv("IMAGE_PROVIDER", "pixabay")).lower().strip()
    if name == "fake":
        return FakeImageProvider()
    return PixabayProvider()
