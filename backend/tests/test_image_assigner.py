"""
Tests for Deterministic Image Assigner
======================================
Verifies:
- Scoped to canonical `item`: never same image across different items
- Reuse never above IMAGE_MAX_REUSE (2)
- Distinct images while candidates last
- Near-duplicate hashes counted as one
- Overrides win and reject is respected
"""

from dataclasses import dataclass
from pathlib import Path
import pytest

from app.services.image_pipeline.assigner import DeterministicAssigner
from app.services.image_pipeline.providers import ImageCandidate


@dataclass
class DummyProduct:
    id: str
    sku: str
    name_en: str
    category: str


def make_cand(cand_id: str, item: str, dhash: str | None = None) -> ImageCandidate:
    return ImageCandidate(
        id=f"pixabay:{cand_id}",
        provider="pixabay",
        provider_photo_id=cand_id,
        item=item,
        url=f"https://images.example.com/{cand_id}.jpg",
        preview_url=f"https://images.example.com/{cand_id}_preview.jpg",
        thumbnail_url=f"https://images.example.com/{cand_id}_thumb.jpg",
        width=800,
        height=1200,
        photographer="Test Artist",
        photographer_url="https://example.com/artist",
        page_url=f"https://example.com/{cand_id}",
        license_url="https://example.com/lic",
        credit_text=f"Photo: Test Artist / Pixabay",
        tags=item,
        dhash=dhash,
    )


def test_assigner_never_shares_images_across_different_items():
    assigner = DeterministicAssigner(max_reuse=2)

    products = [
        DummyProduct(id="1", sku="SKU-CUFF-1", name_en="Royal Silver Cufflinks", category="Accessories"),
        DummyProduct(id="2", sku="SKU-BELT-1", name_en="Premium Braided Leather Belt", category="Accessories"),
    ]
    items_by_sku = {
        "SKU-CUFF-1": "silver cufflinks",
        "SKU-BELT-1": "braided leather belt",
    }

    c_cuff = make_cand("cuff_101", "silver cufflinks", dhash="0000000000000001")
    c_belt = make_cand("belt_202", "braided leather belt", dhash="ffffffffffffffff")

    verified_by_item = {
        "silver cufflinks": [(c_cuff, 0.95, {"shows_item": True})],
        "braided leather belt": [(c_belt, 0.95, {"shows_item": True})],
    }

    results = assigner.assign(products, items_by_sku, verified_by_item)
    assert len(results) == 2

    cuff_res = next(r for r in results if r.sku == "SKU-CUFF-1")
    belt_res = next(r for r in results if r.sku == "SKU-BELT-1")

    assert cuff_res.provider_photo_id == "cuff_101"
    assert belt_res.provider_photo_id == "belt_202"
    assert cuff_res.provider_photo_id != belt_res.provider_photo_id


def test_assigner_respects_max_reuse_and_exhausts_to_missing():
    assigner = DeterministicAssigner(max_reuse=2)

    products = [
        DummyProduct(id="1", sku="SKU-001", name_en="Cufflinks A", category="Accessories"),
        DummyProduct(id="2", sku="SKU-002", name_en="Cufflinks B", category="Accessories"),
        DummyProduct(id="3", sku="SKU-003", name_en="Cufflinks C", category="Accessories"),
    ]
    items_by_sku = {p.sku: "silver cufflinks" for p in products}

    # Only 1 candidate available
    c1 = make_cand("c1", "silver cufflinks", dhash="0000000000000001")
    verified_by_item = {"silver cufflinks": [(c1, 0.95, {"shows_item": True})]}

    results = assigner.assign(products, items_by_sku, verified_by_item)
    assert len(results) == 3

    # First two products get candidate c1 (max_reuse = 2)
    assert results[0].status == "verified"
    assert results[0].provider_photo_id == "c1"
    assert results[1].status == "verified"
    assert results[1].provider_photo_id == "c1"

    # Third product is exhausted -> stays missing (SVG fallback)
    assert results[2].status == "missing"
    assert results[2].image_url_large is None
    assert results[2].image_url.endswith("/image.svg")


def test_assigner_gives_distinct_images_while_candidates_last():
    assigner = DeterministicAssigner(max_reuse=2)

    products = [
        DummyProduct(id="1", sku="SKU-001", name_en="Shirt A", category="Formal Shirts"),
        DummyProduct(id="2", sku="SKU-002", name_en="Shirt B", category="Formal Shirts"),
    ]
    items_by_sku = {p.sku: "formal shirt" for p in products}

    c1 = make_cand("c1", "formal shirt", dhash="1111111111111111")
    c2 = make_cand("c2", "formal shirt", dhash="8888888888888888")
    verified_by_item = {"formal shirt": [(c1, 0.95, {}), (c2, 0.90, {})]}

    results = assigner.assign(products, items_by_sku, verified_by_item)
    assert len(results) == 2
    # Both products get different images!
    assert results[0].provider_photo_id != results[1].provider_photo_id


def test_assigner_filters_near_duplicates_by_dhash():
    assigner = DeterministicAssigner(max_reuse=2, hamming_threshold=6)

    c1 = make_cand("c1", "formal shirt", dhash="0000000000000000")
    # c2 has hamming distance 1 (1 bit difference) -> near-duplicate
    c2 = make_cand("c2", "formal shirt", dhash="0000000000000001")

    candidates = [(c1, 0.95, {}), (c2, 0.90, {})]
    filtered = assigner.filter_near_duplicates(candidates)

    # Near duplicate c2 is filtered out, c1 (higher score) kept
    assert len(filtered) == 1
    assert filtered[0][0].provider_photo_id == "c1"


def test_assigner_overrides_and_reject_respected(tmp_path):
    overrides_file = tmp_path / "overrides.csv"
    overrides_file.write_text(
        "sku,provider_photo_id,force,notes\n"
        "SKU-FORCE,photo_999,true,Forced override\n"
        "SKU-REJECT,reject,false,Rejected bad product\n"
    )

    assigner = DeterministicAssigner(overrides_path=overrides_file)

    products = [
        DummyProduct(id="1", sku="SKU-FORCE", name_en="Forced Product", category="Accessories"),
        DummyProduct(id="2", sku="SKU-REJECT", name_en="Rejected Product", category="Accessories"),
        DummyProduct(id="3", sku="SKU-NORMAL", name_en="Normal Product", category="Accessories"),
    ]
    items_by_sku = {p.sku: "silver cufflinks" for p in products}

    results = assigner.assign(products, items_by_sku, {})

    res_force = next(r for r in results if r.sku == "SKU-FORCE")
    res_reject = next(r for r in results if r.sku == "SKU-REJECT")
    res_normal = next(r for r in results if r.sku == "SKU-NORMAL")

    assert res_force.status == "verified"
    assert res_force.provider_photo_id == "photo_999"

    assert res_reject.status == "rejected"
    assert res_reject.image_url_large is None

    assert res_normal.status == "missing"
