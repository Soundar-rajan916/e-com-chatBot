"""
Tests for Product Type Classifier and Normalizer
"""

import json
from pathlib import Path
import pytest

from app.services.image_pipeline.classifier import ImageClassifier


def test_classifier_loads_vocabulary():
    classifier = ImageClassifier()
    types = classifier.list_types()
    assert len(types) >= 30
    assert classifier.get_type("cufflinks") is not None
    assert classifier.get_type("leather_belt") is not None
    assert classifier.get_type("oxford_shoes") is not None


def test_normalize_title_strips_marketing_words():
    raw = "Royal Silver Cufflinks SKU-MW-ACC-012"
    norm = ImageClassifier.normalize_title(raw)
    assert "royal" not in norm
    assert "silver" not in norm
    assert "sku" not in norm
    assert "cufflinks" in norm


def test_golden_dataset_classification():
    fixture_path = Path(__file__).parent / "fixtures" / "golden_product_types.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    assert len(cases) >= 40

    classifier = ImageClassifier()
    mismatches = []

    for item in cases:
        ptype, conf, rule = classifier.classify(
            name_en=item["name_en"],
            category=item["category"],
            subcategory=item.get("subcategory"),
        )
        if ptype != item["expected_type"]:
            mismatches.append(
                f"Expected {item['expected_type']}, got {ptype} for '{item['name_en']}' ({item['category']})"
            )

    assert not mismatches, "Golden classification mismatches:\n" + "\n".join(mismatches)


def test_cross_category_prevented():
    classifier = ImageClassifier()
    # "cufflinks" keyword should never classify under "kitchenware" or "footwear"
    ptype, conf, rule = classifier.classify(
        name_en="Cufflinks Shaped Ceramic Plate",
        category="kitchenware",
    )
    assert ptype != "cufflinks"
