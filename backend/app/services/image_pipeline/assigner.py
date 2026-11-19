"""
Deterministic Product Image Assigner
====================================
Assigns verified candidates to products deterministically respecting manual overrides,
physical item scoping, vision ranking, perceptual hash deduplication, and maximum reuse limits (IMAGE_MAX_REUSE=2).
"""

import csv
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.image_pipeline.dedup import hamming_distance
from app.services.image_pipeline.providers import ImageCandidate

logger = logging.getLogger("app.services.image_pipeline.assigner")

DEFAULT_MAX_REUSE = 2
DEFAULT_HAMMING_THRESHOLD = 6


@dataclass
class AssignmentResult:
    product_id: str
    sku: str
    name_en: str
    category: str
    item: str | None
    image_url_large: str | None
    image_url_thumb: str | None
    local_path: str | None
    provider: str
    provider_photo_id: str | None
    photographer: str | None
    photographer_url: str | None
    page_url: str | None
    licence: str | None
    credit_text: str | None
    width: int | None = None
    height: int | None = None
    phash: str | None = None
    status: str = "missing"  # verified | needs_review | rejected | missing
    score: float | None = None
    verdict: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    @property
    def image_url(self) -> str:
        return self.image_url_large or f"/api/products/{self.product_id}/image.svg"

    @property
    def thumbnail_url(self) -> str | None:
        return self.image_url_thumb or f"/api/products/{self.product_id}/image.svg"


class DeterministicAssigner:
    def __init__(
        self,
        overrides_path: Path | str | None = None,
        max_reuse: int = DEFAULT_MAX_REUSE,
        hamming_threshold: int = DEFAULT_HAMMING_THRESHOLD,
    ):
        if overrides_path is None:
            overrides_path = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "data"
                / "image_overrides.csv"
            )
        self.overrides_path = Path(overrides_path)
        self.max_reuse = int(os.getenv("IMAGE_MAX_REUSE", str(max_reuse)))
        self.hamming_threshold = int(os.getenv("IMAGE_DUP_HAMMING", str(hamming_threshold)))
        self.overrides = self._load_overrides()

    def _load_overrides(self) -> dict[str, dict]:
        overrides = {}
        if self.overrides_path.is_file():
            try:
                with open(self.overrides_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        sku = row.get("sku", "").strip()
                        if not sku:
                            continue
                        photo_id = row.get("provider_photo_id", "").strip() or row.get("action", "").strip()
                        force_str = str(row.get("force", "")).strip().lower()
                        force = force_str in ("true", "1", "yes")
                        img_url = row.get("image_url", "").strip()
                        overrides[sku] = {
                            "provider_photo_id": photo_id,
                            "force": force,
                            "image_url": img_url,
                            "photographer": row.get("photographer", "Verified Source").strip(),
                            "photographer_url": row.get("photographer_url", "").strip(),
                            "credit": row.get("credit", "Manual Override").strip(),
                            "notes": row.get("notes", "Manual Override").strip(),
                        }
            except Exception as e:
                logger.warning("Error reading overrides at %s: %s", self.overrides_path, e)
        return overrides

    def filter_near_duplicates(
        self,
        candidates: list[tuple[ImageCandidate, float, dict[str, Any]]],
    ) -> list[tuple[ImageCandidate, float, dict[str, Any]]]:
        """
        Deduplicates candidate list using dHash and Hamming distance.
        Keeps highest score candidate among near duplicates.
        """
        filtered = []
        seen_hashes: list[str] = []
        for cand, score, verdict in candidates:
            chash = cand.dhash
            if not chash:
                filtered.append((cand, score, verdict))
                continue

            is_dup = False
            for shash in seen_hashes:
                if hamming_distance(chash, shash) <= self.hamming_threshold:
                    is_dup = True
                    break

            if not is_dup:
                seen_hashes.append(chash)
                filtered.append((cand, score, verdict))

        return filtered

    def assign(
        self,
        products: list[Any],
        items_by_sku: dict[str, str | None],
        verified_candidates_by_item: dict[str, list[tuple[ImageCandidate, float, dict[str, Any]]]],
    ) -> list[AssignmentResult]:
        """
        Executes deterministic assignment scoped to canonical `item`.
        Returns list of AssignmentResult for all products.
        """
        results: list[AssignmentResult] = []
        products_by_item = defaultdict(list)
        untyped_products = []

        # 1. First partition products and handle overrides
        for p in products:
            sku = p.sku
            if sku in self.overrides:
                ov = self.overrides[sku]
                if ov["provider_photo_id"] == "reject":
                    results.append(
                        AssignmentResult(
                            product_id=str(p.id),
                            sku=p.sku,
                            name_en=p.name_en,
                            category=p.category,
                            item=items_by_sku.get(p.sku),
                            image_url_large=None,
                            image_url_thumb=None,
                            local_path=None,
                            provider="manual_override",
                            provider_photo_id="reject",
                            photographer=None,
                            photographer_url=None,
                            page_url=None,
                            licence=None,
                            credit_text=None,
                            status="rejected",
                            score=0.0,
                            verdict={"rejected_by_override": True},
                            notes=ov["notes"] or "Rejected by manual override",
                        )
                    )
                    continue

                if ov["image_url"] or ov["provider_photo_id"]:
                    img_url = ov["image_url"] or f"/media/products/{ov['provider_photo_id']}_800.webp"
                    thumb_url = ov["image_url"] or f"/media/products/{ov['provider_photo_id']}_400.webp"
                    results.append(
                        AssignmentResult(
                            product_id=str(p.id),
                            sku=p.sku,
                            name_en=p.name_en,
                            category=p.category,
                            item=items_by_sku.get(p.sku),
                            image_url_large=img_url,
                            image_url_thumb=thumb_url,
                            local_path=None,
                            provider="manual_override",
                            provider_photo_id=ov["provider_photo_id"],
                            photographer=ov["photographer"],
                            photographer_url=ov["photographer_url"],
                            page_url=None,
                            licence=None,
                            credit_text=ov["credit"],
                            status="verified",
                            score=1.0,
                            verdict={"manual_override": True, "force": ov["force"]},
                            notes=ov["notes"],
                        )
                    )
                    continue

            item = items_by_sku.get(p.sku)
            if not item:
                untyped_products.append(p)
            else:
                products_by_item[item].append(p)

        # Handle untyped products (item: null -> missing status, fallback to SVG)
        for p in untyped_products:
            results.append(
                AssignmentResult(
                    product_id=str(p.id),
                    sku=p.sku,
                    name_en=p.name_en,
                    category=p.category,
                    item=None,
                    image_url_large=None,
                    image_url_thumb=None,
                    local_path=None,
                    provider="svg",
                    provider_photo_id=None,
                    photographer=None,
                    photographer_url=None,
                    page_url=None,
                    licence=None,
                    credit_text=None,
                    status="missing",
                    score=None,
                    verdict={},
                    notes="No canonical physical item identified",
                )
            )

        # 2. For each canonical physical item, assign verified candidates deterministically
        for item, p_list in products_by_item.items():
            # Sort products deterministically by SKU
            p_list.sort(key=lambda x: x.sku)

            # Deduplicate near duplicates within candidate list
            raw_verified = list(verified_candidates_by_item.get(item, []))
            # Sort candidates by score desc, then candidate id asc for deterministic order
            raw_verified.sort(key=lambda x: (-x[1], x[0].id))
            verified = self.filter_near_duplicates(raw_verified)

            if not verified:
                for p in p_list:
                    results.append(
                        AssignmentResult(
                            product_id=str(p.id),
                            sku=p.sku,
                            name_en=p.name_en,
                            category=p.category,
                            item=item,
                            image_url_large=None,
                            image_url_thumb=None,
                            local_path=None,
                            provider="svg",
                            provider_photo_id=None,
                            photographer=None,
                            photographer_url=None,
                            page_url=None,
                            licence=None,
                            credit_text=None,
                            status="missing",
                            score=None,
                            verdict={},
                            notes="No verified candidates available for item",
                        )
                    )
                continue

            candidate_usage = {cand.id: 0 for cand, _, _ in verified}
            c_index = 0
            num_candidates = len(verified)

            for p in p_list:
                # Find candidate with usage < max_reuse (preferring lowest usage first so candidates are varied)
                assigned_cand = None
                assigned_score = None
                assigned_verdict = None

                # Search through candidates starting at c_index
                checked = 0
                while checked < num_candidates:
                    curr_cand, curr_score, curr_verdict = verified[c_index % num_candidates]
                    if candidate_usage[curr_cand.id] < self.max_reuse:
                        assigned_cand = curr_cand
                        assigned_score = curr_score
                        assigned_verdict = curr_verdict
                        candidate_usage[curr_cand.id] += 1
                        c_index += 1
                        break
                    c_index += 1
                    checked += 1

                if assigned_cand:
                    results.append(
                        AssignmentResult(
                            product_id=str(p.id),
                            sku=p.sku,
                            name_en=p.name_en,
                            category=p.category,
                            item=item,
                            image_url_large=assigned_cand.url,
                            image_url_thumb=assigned_cand.thumbnail_url or assigned_cand.preview_url,
                            local_path=None,
                            provider=assigned_cand.provider,
                            provider_photo_id=assigned_cand.provider_photo_id,
                            photographer=assigned_cand.photographer,
                            photographer_url=assigned_cand.photographer_url,
                            page_url=assigned_cand.page_url,
                            licence=assigned_cand.license_url,
                            credit_text=assigned_cand.credit_text,
                            width=assigned_cand.width,
                            height=assigned_cand.height,
                            phash=assigned_cand.dhash,
                            status="verified",
                            score=assigned_score,
                            verdict=assigned_verdict,
                            notes=f"Assigned verified candidate (reuse count: {candidate_usage[assigned_cand.id]}/{self.max_reuse})",
                        )
                    )
                else:
                    # Candidates exhausted for this item at max_reuse
                    results.append(
                        AssignmentResult(
                            product_id=str(p.id),
                            sku=p.sku,
                            name_en=p.name_en,
                            category=p.category,
                            item=item,
                            image_url_large=None,
                            image_url_thumb=None,
                            local_path=None,
                            provider="svg",
                            provider_photo_id=None,
                            photographer=None,
                            photographer_url=None,
                            page_url=None,
                            licence=None,
                            credit_text=None,
                            status="missing",
                            score=None,
                            verdict={},
                            notes=f"Candidate pool ({num_candidates} items) exhausted at max_reuse={self.max_reuse}",
                        )
                    )

        # Sort results by SKU for deterministic output order
        results.sort(key=lambda r: r.sku)
        return results

    @staticmethod
    def write_assignment_plan_csv(results: list[AssignmentResult], output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "sku",
                "product_name",
                "category",
                "item",
                "status",
                "image_url_large",
                "provider",
                "provider_photo_id",
                "photographer",
                "credit_text",
                "score",
                "notes",
            ])
            for r in results:
                writer.writerow([
                    r.sku,
                    r.name_en,
                    r.category,
                    r.item or "",
                    r.status,
                    r.image_url_large or "",
                    r.provider,
                    r.provider_photo_id or "",
                    r.photographer or "",
                    r.credit_text or "",
                    f"{r.score:.3f}" if r.score is not None else "",
                    r.notes,
                ])
