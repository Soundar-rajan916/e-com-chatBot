"""
Product Type Normalization & Classifier
========================================
Normalizes marketing variations in product titles and classifies products into
canonical product types defined in data/image_types.yml.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("app.services.image_pipeline.classifier")

# Common marketing noise words and variant adjectives to strip for canonical matching
MARKETING_PREFIXES = {
    "royal", "premium", "handwoven", "artisan", "heritage", "classic", "vintage",
    "essential", "signature", "refined", "modern", "luxury", "authentic", "artisanal",
    "handcrafted", "traditional", "exclusive", "pure", "deluxe", "smart", "stylish",
    "organic", "natural", "eco-friendly", "heavyweight", "lightweight", "tailored",
}

COLORS = {
    "black", "white", "navy", "blue", "grey", "gray", "charcoal", "brown", "tan",
    "silver", "gold", "golden", "red", "maroon", "burgundy", "green", "olive",
    "khaki", "beige", "cream", "yellow", "orange", "pink", "purple", "indigo",
}

BRAND_PREFIXES = {
    "chettinadkitchen", "cholastyle", "coromandelaudio", "annamfoods", "tanjorecrafts",
    "maduraigems", "pandyanlooms", "kongutextiles", "cherahandicrafts",
}


@dataclass
class ProductType:
    id: str
    display_name: str
    allowed_categories: list[str]
    search_queries: list[str]
    synonyms: list[str]
    negative_terms: list[str] = field(default_factory=list)
    allow_person: bool = False


class ImageClassifier:
    def __init__(self, vocabulary_path: str | Path | None = None):
        if vocabulary_path is None:
            # Look in repo root / data / image_types.yml or relative to backend
            possible_paths = [
                Path(__file__).resolve().parent.parent.parent.parent / "data" / "image_types.yml",
                Path(__file__).resolve().parent.parent.parent / "data" / "image_types.yml",
                Path("data/image_types.yml"),
            ]
            for p in possible_paths:
                if p.is_file():
                    vocabulary_path = p
                    break

        if not vocabulary_path or not Path(vocabulary_path).is_file():
            raise FileNotFoundError(f"Controlled vocabulary file not found at {vocabulary_path}")

        self.vocabulary_path = Path(vocabulary_path)
        self.types: dict[str, ProductType] = {}
        self.synonym_index: list[tuple[str, str, int]] = []  # (synonym_lower, type_id, length)
        self._load_vocabulary()

    def _load_vocabulary(self):
        with open(self.vocabulary_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        raw_types = data.get("types", [])
        for item in raw_types:
            ptype = ProductType(
                id=item["id"],
                display_name=item["display_name"],
                allowed_categories=item.get("allowed_categories", []),
                search_queries=item.get("search_queries", []),
                synonyms=item.get("synonyms", []),
                negative_terms=item.get("negative_terms", []),
                allow_person=item.get("allow_person", False),
            )
            self.types[ptype.id] = ptype

            for syn in ptype.synonyms:
                self.synonym_index.append((syn.lower().strip(), ptype.id, len(syn.strip())))

        # Sort synonyms: specialized types get a priority boost, then by length
        # Generic types that should only match if no specialized type matches:
        generic_types = {"formal_dress_shirt", "casual_cotton_shirt", "chinos", "t_shirt"}
        def sort_key(item):
            syn, type_id, length = item
            is_generic = 1 if type_id in generic_types else 0
            return (is_generic, -length)

        self.synonym_index.sort(key=sort_key)

    @staticmethod
    def normalize_title(title: str) -> str:
        """Strips marketing words, colors, brand prefixes and SKU numbers."""
        text = title.lower()
        # Remove SKU patterns if present
        text = re.sub(r"\bsku-[a-z0-9-]+\b", "", text)
        # Remove punctuation except hyphens inside words
        text = re.sub(r"[^\w\s-]", " ", text)

        words = text.split()
        filtered = []
        for w in words:
            clean_w = w.strip("-")
            if clean_w in BRAND_PREFIXES:
                continue
            if clean_w in MARKETING_PREFIXES:
                continue
            if clean_w in COLORS:
                continue
            filtered.append(clean_w)

        return " ".join(filtered)

    def classify(
        self,
        name_en: str,
        category: str,
        subcategory: str | None = None,
    ) -> tuple[str | None, float, str]:
        """
        Classifies product into a canonical type.
        Returns: (type_id or None, confidence 0.0-1.0, rule_used)
        """
        cat_clean = (category or "").lower().strip()
        subcat_clean = (subcategory or "").lower().strip() if subcategory else ""
        norm_title = self.normalize_title(name_en)
        full_text = f"{norm_title} {name_en.lower()}"

        generic_types = {"formal_dress_shirt", "casual_cotton_shirt", "chinos", "t_shirt"}

        # 1. Specialized title phrase match (non-generic types)
        for syn, type_id, _ in self.synonym_index:
            if type_id in generic_types:
                continue
            ptype = self.types[type_id]
            if ptype.allowed_categories and cat_clean not in ptype.allowed_categories:
                continue
            pattern = r"\b" + re.escape(syn) + r"\b"
            if re.search(pattern, full_text):
                return type_id, 0.95, f"title_specialized_match:'{syn}'"

        # 2. Specialized subcategory match (e.g. "French Cuff", "Tuxedos", "Cufflinks")
        if subcat_clean and subcat_clean not in {"trousers & chinos", "formal shirts", "blazers & suits", "dhotis & ethnic"}:
            for syn, type_id, _ in self.synonym_index:
                if type_id in generic_types:
                    continue
                ptype = self.types[type_id]
                if ptype.allowed_categories and cat_clean not in ptype.allowed_categories:
                    continue
                pattern = r"\b" + re.escape(syn) + r"\b"
                if re.search(pattern, subcat_clean):
                    return type_id, 0.92, f"subcategory_specialized_match:'{syn}'"

        # 3. Generic title phrase match (e.g. dress shirt, chinos, cotton shirt)
        for syn, type_id, _ in self.synonym_index:
            if type_id not in generic_types:
                continue
            ptype = self.types[type_id]
            if ptype.allowed_categories and cat_clean not in ptype.allowed_categories:
                continue
            pattern = r"\b" + re.escape(syn) + r"\b"
            if re.search(pattern, full_text):
                return type_id, 0.90, f"title_generic_match:'{syn}'"

        # 4. Fallback subcategory match
        if subcat_clean:
            for syn, type_id, _ in self.synonym_index:
                ptype = self.types[type_id]
                if ptype.allowed_categories and cat_clean not in ptype.allowed_categories:
                    continue
                pattern = r"\b" + re.escape(syn) + r"\b"
                if re.search(pattern, subcat_clean):
                    return type_id, 0.85, f"subcategory_match:'{syn}'"

        # 5. Direct category-to-type fallbacks for high-confidence 1:1 categories
        direct_category_map = {
            "cufflinks": "cufflinks",
            "headphones": "headphones",
            "mechanical keyboards": "mechanical_keyboard",
            "power banks": "power_bank",
            "air fryers": "air_fryer",
            "pressure cookers": "pressure_cooker",
            "spice jars": "spice_jar",
            "cast iron kadai": "cast_iron_kadai",
            "screen protectors": "screen_protector",
            "fast chargers": "fast_charger",
            "car mounts": "car_mount",
            "phone cases": "phone_case",
        }
        for sub_kw, type_id in direct_category_map.items():
            if sub_kw in subcat_clean or sub_kw in cat_clean:
                if type_id in self.types:
                    return type_id, 0.80, f"category_direct_map:'{sub_kw}'"

        return None, 0.0, "unclassified"

    def get_type(self, type_id: str) -> ProductType | None:
        return self.types.get(type_id)

    def list_types(self) -> list[ProductType]:
        return list(self.types.values())
