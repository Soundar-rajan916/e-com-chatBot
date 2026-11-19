"""
Tests for Vision Judge Gate
===========================
Tests:
- Watch photo for cufflinks rejected
- Backpack for belt rejected
- Brand logo rejected
- Watermark rejected
- Person-dominant rejected unless people_ok
- Low confidence to needs_review
- Cache hit makes no second call
"""

import pytest
from app.services.image_pipeline.providers import ImageCandidate
from app.services.image_pipeline.vision import FakeVisionJudge, VisionVerdict


def make_cand(cand_id: str, tags: str = "") -> ImageCandidate:
    return ImageCandidate(
        id=cand_id,
        provider="pixabay",
        provider_photo_id=cand_id,
        item="test_item",
        url=f"https://images.example.com/{cand_id}.jpg",
        preview_url=f"https://images.example.com/{cand_id}_preview.jpg",
        width=800,
        height=1200,
        photographer="Artist",
        photographer_url="https://example.com/artist",
        page_url=f"https://example.com/{cand_id}",
        license_url="https://example.com/lic",
        credit_text="Photo: Artist / Pixabay",
        tags=tags,
    )


@pytest.mark.asyncio
async def test_vision_rejects_watch_for_cufflinks():
    judge = FakeVisionJudge()
    cand = make_cand("photo_watch_1", tags="wristwatch luxury watch time")

    verdict = await judge.judge_candidate(
        candidate=cand,
        item="silver cufflinks",
        must_show="A pair of metallic cufflinks",
        must_not_show="a wristwatch as the main subject",
        people_ok=False,
    )

    assert verdict.is_accepted is False
    assert "wristwatch" in " ".join(verdict.rejection_reasons).lower()


@pytest.mark.asyncio
async def test_vision_rejects_backpack_for_belt():
    judge = FakeVisionJudge()
    cand = make_cand("photo_backpack_1", tags="travel backpack luggage bag")

    verdict = await judge.judge_candidate(
        candidate=cand,
        item="braided leather belt",
        must_show="A braided leather waist belt",
        must_not_show="a backpack, handbag, travel luggage",
        people_ok=False,
    )

    assert verdict.is_accepted is False
    assert "backpack" in " ".join(verdict.rejection_reasons).lower()


@pytest.mark.asyncio
async def test_vision_rejects_brand_logo():
    judge = FakeVisionJudge()
    cand = make_cand("photo_brand_logo_1", tags="luxury brand logo gucci")

    verdict = await judge.judge_candidate(
        candidate=cand,
        item="leather belt",
        must_show="A leather belt",
        must_not_show="visible brand logo",
        people_ok=False,
    )

    assert verdict.is_accepted is False
    assert any("brand logo" in r for r in verdict.rejection_reasons)


@pytest.mark.asyncio
async def test_vision_rejects_watermark():
    judge = FakeVisionJudge()
    cand = make_cand("photo_watermark_1", tags="stock photo watermark sample")

    verdict = await judge.judge_candidate(
        candidate=cand,
        item="formal shirt",
        must_show="A dress shirt",
        must_not_show="watermark",
        people_ok=True,
    )

    assert verdict.is_accepted is False
    assert any("watermark" in r for r in verdict.rejection_reasons)


@pytest.mark.asyncio
async def test_vision_person_dominant_allowed_only_when_people_ok():
    judge = FakeVisionJudge()
    cand = make_cand("photo_person_dominant_1", tags="model dominant portrait person")

    # When people_ok is False (e.g. for cufflinks/belt) -> rejected
    v_no_people = await judge.judge_candidate(
        candidate=cand,
        item="silver cufflinks",
        people_ok=False,
    )
    assert v_no_people.is_accepted is False
    assert any("person is dominant" in r for r in v_no_people.rejection_reasons)

    # When people_ok is True (e.g. for clothing worn by model) -> accepted
    v_with_people = await judge.judge_candidate(
        candidate=cand,
        item="formal shirt",
        people_ok=True,
    )
    assert v_with_people.is_accepted is True


@pytest.mark.asyncio
async def test_vision_marginal_confidence_goes_to_needs_review():
    judge = FakeVisionJudge()
    cand = make_cand("photo_low_confidence_1", tags="marginal blurry")

    verdict = await judge.judge_candidate(
        candidate=cand,
        item="formal shirt",
        people_ok=True,
    )

    assert verdict.is_accepted is False
    assert verdict.needs_review is True
    assert any("needs_review" in r or "marginal" in r for r in verdict.rejection_reasons)


@pytest.mark.asyncio
async def test_vision_verdict_caching(tmp_path):
    judge = FakeVisionJudge()
    cand = make_cand("cand_normal", tags="normal matching photo")

    v1 = await judge.judge_candidate(cand, "formal shirt", people_ok=True)
    assert v1.is_accepted is True
    assert judge.call_count == 1

    # Second call for the same candidate and item should use cache
    v2 = await judge.judge_candidate(cand, "formal shirt", people_ok=True)
    assert v2.is_accepted is True
