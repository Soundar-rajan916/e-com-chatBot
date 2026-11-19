"""
Vision Judge Verification Gate
==============================
Verifies candidate stock images using a vision model (Groq Llama 3.2 Vision)
with strict Pydantic JSON output, rejection gates, and on-disk caching.
"""

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Protocol, runtime_checkable

import httpx
from pydantic import BaseModel, Field

from app.services.image_pipeline.providers import ImageCandidate

logger = logging.getLogger("app.services.image_pipeline.vision")

PROMPT_VERSION = "v2.0"


class VisionVerdict(BaseModel):
    shows_item: bool = Field(default=False, description="Is the target item present in the photo?")
    is_main_subject: bool = Field(default=False, description="Is the target item the central/main subject?")
    matches_must_show: bool = Field(default=False, description="Does the photo clearly show what must_show specifies?")
    hits_must_not_show: bool = Field(default=False, description="Does the photo show any forbidden elements from must_not_show?")
    brand_logo_or_readable_brand_text: bool = Field(default=False, description="Are visible brand logos or readable trademark texts present?")
    watermark: bool = Field(default=False, description="Are there watermarks, promotional texts, or stock badges?")
    person_dominant: bool = Field(default=False, description="Is a human person dominant in the image?")
    quality: float = Field(default=0.0, ge=0.0, le=1.0, description="Visual quality score between 0.0 and 1.0")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reason: str = Field(default="", description="Short reason explaining the verdict")
    is_accepted: bool = False
    needs_review: bool = False
    rejection_reasons: list[str] = Field(default_factory=list)


@runtime_checkable
class VisionJudge(Protocol):
    async def judge_candidate(
        self,
        candidate: ImageCandidate,
        item: str,
        must_show: str = "",
        must_not_show: str = "",
        people_ok: bool = False,
    ) -> VisionVerdict:
        ...


class BaseVisionJudge:
    def __init__(self, cache_dir: Path | str | None = None):
        if cache_dir is None:
            cache_dir = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "data"
                / "image_cache"
                / "vision"
            )
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(
        self,
        provider: str,
        photo_id: str,
        item: str,
        model_name: str,
    ) -> Path:
        raw_key = f"{provider}:{photo_id}:{item}:{PROMPT_VERSION}:{model_name}"
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
        safe_item = "".join(c if c.isalnum() else "_" for c in item)[:30]
        return self.cache_dir / f"{provider}_{safe_item}_{photo_id}_{key_hash}.json"

    def _read_cache(self, path: Path) -> VisionVerdict | None:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return VisionVerdict(**data)
            except Exception as e:
                logger.warning("Failed to read vision cache at %s: %s", path, e)
        return None

    def _write_cache(self, path: Path, verdict: VisionVerdict):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(verdict.model_dump(), f, indent=2)
        except Exception as e:
            logger.warning("Failed to write vision cache at %s: %s", path, e)

    @staticmethod
    def apply_gate(
        verdict: VisionVerdict,
        people_ok: bool,
        min_quality: float = 0.7,
        min_confidence: float = 0.8,
    ) -> VisionVerdict:
        reasons: list[str] = []

        if not verdict.shows_item:
            reasons.append("target item not shown (shows_item=False)")
        if not verdict.is_main_subject:
            reasons.append("target item is not main subject (is_main_subject=False)")
        if not verdict.matches_must_show:
            reasons.append("does not match must_show criteria")
        if verdict.hits_must_not_show:
            reasons.append("contains forbidden elements (hits_must_not_show=True)")
        if verdict.brand_logo_or_readable_brand_text:
            reasons.append("brand logo or readable brand text detected")
        if verdict.watermark:
            reasons.append("watermark or stock badge detected")
        if verdict.person_dominant and not people_ok:
            reasons.append("person is dominant but people_ok is False for this item")
        if verdict.quality < min_quality:
            reasons.append(f"quality {verdict.quality:.2f} below minimum {min_quality:.2f}")
        if verdict.reason:
            reasons.append(verdict.reason)

        passes_all_boolean = (len(reasons) == 0 or (len(reasons) == 1 and verdict.reason in reasons and verdict.shows_item and verdict.is_main_subject and verdict.matches_must_show and not verdict.hits_must_not_show and not verdict.brand_logo_or_readable_brand_text and not verdict.watermark and (not verdict.person_dominant or people_ok) and verdict.quality >= min_quality))
        if passes_all_boolean:
            if verdict.confidence >= min_confidence:
                verdict.is_accepted = True
                verdict.needs_review = False
            elif verdict.confidence >= (min_confidence - 0.15):
                verdict.is_accepted = False
                verdict.needs_review = True
                reasons.append(f"confidence {verdict.confidence:.2f} is marginal (below {min_confidence:.2f}, flagged for review)")
            else:
                verdict.is_accepted = False
                verdict.needs_review = False
                reasons.append(f"confidence {verdict.confidence:.2f} below threshold {min_confidence:.2f}")
        else:
            verdict.is_accepted = False
            verdict.needs_review = False

        verdict.rejection_reasons = reasons
        return verdict


class GroqVisionJudge(BaseVisionJudge):
    """Evaluates images using Groq's Vision API with strict Pydantic JSON."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        min_quality: float = 0.7,
        min_confidence: float = 0.8,
        cache_dir: Path | str | None = None,
    ):
        super().__init__(cache_dir=cache_dir)
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("VISION_MODEL", "qwen/qwen3.8-27b")
        self.min_quality = float(os.getenv("IMAGE_MIN_QUALITY", str(min_quality)))
        self.min_confidence = float(os.getenv("IMAGE_MIN_CONFIDENCE", str(min_confidence)))

    async def judge_candidate(
        self,
        candidate: ImageCandidate,
        item: str,
        must_show: str = "",
        must_not_show: str = "",
        people_ok: bool = False,
    ) -> VisionVerdict:
        cache_path = self._get_cache_path(
            candidate.provider,
            candidate.provider_photo_id,
            item,
            self.model,
        )
        cached_verdict = self._read_cache(cache_path)
        if cached_verdict is not None:
            return self.apply_gate(
                cached_verdict,
                people_ok=people_ok,
                min_quality=self.min_quality,
                min_confidence=self.min_confidence,
            )

        if not self.api_key:
            logger.debug("GROQ_API_KEY not configured. Falling back to default rejection verdict.")
            verdict = VisionVerdict(
                shows_item=False,
                is_main_subject=False,
                matches_must_show=False,
                hits_must_not_show=False,
                brand_logo_or_readable_brand_text=False,
                watermark=False,
                person_dominant=False,
                quality=0.0,
                confidence=0.0,
                reason="GROQ_API_KEY not configured",
                rejection_reasons=["GROQ_API_KEY not configured"],
                is_accepted=False,
            )
            return verdict

        prompt_text = f"""You are an expert e-commerce catalog image verification system.
Evaluate the attached photo for the physical product item described below:
Target Canonical Item: "{item}"
Must show: "{must_show}"
Must NOT show: "{must_not_show}"
Are people acceptable: {"YES" if people_ok else "NO (MUST BE STANDALONE PRODUCT ONLY)"}

Analyze the photo carefully and respond ONLY with a strict JSON object:
{{
  "shows_item": true/false,
  "is_main_subject": true/false,
  "matches_must_show": true/false,
  "hits_must_not_show": true/false,
  "brand_logo_or_readable_brand_text": true/false,
  "watermark": true/false,
  "person_dominant": true/false,
  "quality": 0.0 to 1.0,
  "confidence": 0.0 to 1.0,
  "reason": "short explanation"
}}
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        eval_url = candidate.preview_url or candidate.url
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": eval_url}},
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": 400,
        }

        raw_verdict_data = {}
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    resp = await client.post(self.BASE_URL, headers=headers, json=payload)
                    if resp.status_code == 429:
                        wait = 2 ** (attempt + 1)
                        logger.warning("Groq Vision 429 Rate Limit hit. Backing off %ds...", wait)
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    result_json = resp.json()
                    content = result_json["choices"][0]["message"]["content"]
                    raw_verdict_data = json.loads(content)
                    break
            except Exception as e:
                logger.warning("Groq Vision API attempt %d failed for candidate %s: %s", attempt + 1, candidate.id, e)
                if attempt < 2:
                    await asyncio.sleep(1.5 * (attempt + 1))

        if not raw_verdict_data:
            verdict = VisionVerdict(
                shows_item=False,
                is_main_subject=False,
                matches_must_show=False,
                hits_must_not_show=False,
                brand_logo_or_readable_brand_text=False,
                watermark=False,
                person_dominant=False,
                quality=0.0,
                confidence=0.0,
                reason="Vision API call failed",
                rejection_reasons=["Vision API call failed"],
                is_accepted=False,
            )
            return verdict

        try:
            verdict = VisionVerdict(
                shows_item=bool(raw_verdict_data.get("shows_item", False)),
                is_main_subject=bool(raw_verdict_data.get("is_main_subject", False)),
                matches_must_show=bool(raw_verdict_data.get("matches_must_show", False)),
                hits_must_not_show=bool(raw_verdict_data.get("hits_must_not_show", False)),
                brand_logo_or_readable_brand_text=bool(raw_verdict_data.get("brand_logo_or_readable_brand_text", False)),
                watermark=bool(raw_verdict_data.get("watermark", False)),
                person_dominant=bool(raw_verdict_data.get("person_dominant", False)),
                quality=float(raw_verdict_data.get("quality", 0.0)),
                confidence=float(raw_verdict_data.get("confidence", 0.0)),
                reason=str(raw_verdict_data.get("reason", "")),
            )
        except Exception as e:
            logger.warning("Error parsing vision verdict schema for %s: %s", candidate.id, e)
            verdict = VisionVerdict(
                shows_item=False,
                is_main_subject=False,
                matches_must_show=False,
                hits_must_not_show=False,
                brand_logo_or_readable_brand_text=False,
                watermark=False,
                person_dominant=False,
                quality=0.0,
                confidence=0.0,
                reason=f"Schema parse error: {e}",
                rejection_reasons=[f"Schema parse error: {e}"],
                is_accepted=False,
            )

        verdict = self.apply_gate(
            verdict,
            people_ok=people_ok,
            min_quality=self.min_quality,
            min_confidence=self.min_confidence,
        )
        self._write_cache(cache_path, verdict)
        return verdict


class FakeVisionJudge(BaseVisionJudge):
    """Test fake for VisionJudge that returns deterministic verdicts based on candidate metadata or overrides."""

    def __init__(
        self,
        default_accept: bool = True,
        confidence: float = 0.95,
        quality: float = 0.9,
        verdicts_by_candidate_id: dict[str, VisionVerdict] | None = None,
    ):
        super().__init__()
        self.default_accept = default_accept
        self.confidence = confidence
        self.quality = quality
        self.verdicts_by_candidate_id = verdicts_by_candidate_id or {}
        self.call_count = 0

    async def judge_candidate(
        self,
        candidate: ImageCandidate,
        item: str,
        must_show: str = "",
        must_not_show: str = "",
        people_ok: bool = False,
    ) -> VisionVerdict:
        self.call_count += 1
        if candidate.id in self.verdicts_by_candidate_id:
            v = self.verdicts_by_candidate_id[candidate.id]
            return self.apply_gate(v, people_ok=people_ok)

        # Check negative simulated keywords in candidate tags / id
        cid = candidate.id.lower()
        tags = (candidate.tags or "").lower()

        if "wristwatch" in cid or "watch" in tags:
            if "cufflinks" in item.lower():
                # Rejection: watch for cufflinks
                v = VisionVerdict(
                    shows_item=False,
                    is_main_subject=False,
                    matches_must_show=False,
                    hits_must_not_show=True,
                    brand_logo_or_readable_brand_text=False,
                    watermark=False,
                    person_dominant=False,
                    quality=0.9,
                    confidence=0.9,
                    reason="Shows a wristwatch instead of cufflinks",
                )
                return self.apply_gate(v, people_ok=people_ok)

        if "backpack" in cid or "backpack" in tags:
            if "belt" in item.lower():
                # Rejection: backpack for belt
                v = VisionVerdict(
                    shows_item=False,
                    is_main_subject=False,
                    matches_must_show=False,
                    hits_must_not_show=True,
                    brand_logo_or_readable_brand_text=False,
                    watermark=False,
                    person_dominant=False,
                    quality=0.9,
                    confidence=0.9,
                    reason="Shows a backpack instead of a belt",
                )
                return self.apply_gate(v, people_ok=people_ok)

        if "brand_logo" in cid or "logo" in tags:
            v = VisionVerdict(
                shows_item=True,
                is_main_subject=True,
                matches_must_show=True,
                hits_must_not_show=False,
                brand_logo_or_readable_brand_text=True,
                watermark=False,
                person_dominant=False,
                quality=0.9,
                confidence=0.9,
                reason="Visible luxury brand logo present",
            )
            return self.apply_gate(v, people_ok=people_ok)

        if "watermark" in cid or "watermark" in tags:
            v = VisionVerdict(
                shows_item=True,
                is_main_subject=True,
                matches_must_show=True,
                hits_must_not_show=False,
                brand_logo_or_readable_brand_text=False,
                watermark=True,
                person_dominant=False,
                quality=0.9,
                confidence=0.9,
                reason="Watermark detected",
            )
            return self.apply_gate(v, people_ok=people_ok)

        if "person_dominant" in cid or "model_dominant" in tags:
            v = VisionVerdict(
                shows_item=True,
                is_main_subject=True,
                matches_must_show=True,
                hits_must_not_show=False,
                brand_logo_or_readable_brand_text=False,
                watermark=False,
                person_dominant=True,
                quality=0.9,
                confidence=0.9,
                reason="Person is dominant in photo",
            )
            return self.apply_gate(v, people_ok=people_ok)

        if "low_confidence" in cid or "marginal" in tags:
            v = VisionVerdict(
                shows_item=True,
                is_main_subject=True,
                matches_must_show=True,
                hits_must_not_show=False,
                brand_logo_or_readable_brand_text=False,
                watermark=False,
                person_dominant=False,
                quality=0.8,
                confidence=0.72,  # Marginal, should go to needs_review
                reason="Marginal confidence score",
            )
            return self.apply_gate(v, people_ok=people_ok)

        if not self.default_accept:
            v = VisionVerdict(
                shows_item=False,
                is_main_subject=False,
                matches_must_show=False,
                hits_must_not_show=False,
                brand_logo_or_readable_brand_text=False,
                watermark=False,
                person_dominant=False,
                quality=0.5,
                confidence=0.4,
                reason="Rejected by default_accept=False",
            )
            return self.apply_gate(v, people_ok=people_ok)

        v = VisionVerdict(
            shows_item=True,
            is_main_subject=True,
            matches_must_show=True,
            hits_must_not_show=False,
            brand_logo_or_readable_brand_text=False,
            watermark=False,
            person_dominant=False,
            quality=self.quality,
            confidence=self.confidence,
            reason="Verified matching item",
        )
        return self.apply_gate(v, people_ok=people_ok)


def get_vision_judge(
    judge_type: str | None = None,
    min_quality: float = 0.7,
    min_confidence: float = 0.8,
) -> VisionJudge:
    j_type = (judge_type or os.getenv("VISION_JUDGE", "groq")).lower().strip()
    if j_type == "fake":
        return FakeVisionJudge()
    return GroqVisionJudge(min_quality=min_quality, min_confidence=min_confidence)
