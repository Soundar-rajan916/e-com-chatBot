"""
Perceptual Hashing & Image Deduplication
========================================
Implements difference hash (dHash 64-bit) with Pillow and Hamming distance comparison
to enforce zero cross-type duplicate images and limit within-type duplicate reuse.
"""

import io
import logging
from typing import BinaryIO

from PIL import Image

logger = logging.getLogger("app.services.image_pipeline.dedup")

DEFAULT_HAMMING_THRESHOLD = 6


def compute_dhash(image_input: bytes | BinaryIO | Image.Image) -> str:
    """
    Computes a 64-bit difference hash (dHash) represented as a 16-character hex string.
    1. Grayscale
    2. Resize to 9x8
    3. Compare adjacent pixels horizontally
    """
    if isinstance(image_input, (bytes, bytearray)):
        img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, Image.Image):
        img = image_input
    else:
        img = Image.open(image_input)

    # Convert to grayscale
    gray = img.convert("L")
    # Resize to 9 columns by 8 rows
    resized = gray.resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(resized.getdata())

    # Build 64-bit binary sequence: row by row, is pixel[col] > pixel[col+1]?
    diff = []
    for row in range(8):
        row_offset = row * 9
        for col in range(8):
            left = pixels[row_offset + col]
            right = pixels[row_offset + col + 1]
            diff.append(1 if left > right else 0)

    # Convert 64 bits to hex
    decimal_val = 0
    for bit in diff:
        decimal_val = (decimal_val << 1) | bit

    return f"{decimal_val:016x}"


def hamming_distance(hash1: str, hash2: str) -> int:
    """Calculates the Hamming distance (number of bit differences) between two 16-character hex hashes."""
    if not hash1 or not hash2:
        return 64
    try:
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
        xor_result = val1 ^ val2
        return bin(xor_result).count("1")
    except ValueError:
        return 64


class PerceptualDedupIndex:
    """
    Tracks accepted candidates across types to strictly prevent cross-type collisions
    and manage within-type near-duplicates.
    """

    def __init__(self, hamming_threshold: int = DEFAULT_HAMMING_THRESHOLD):
        self.hamming_threshold = hamming_threshold
        # type_id -> list of (candidate_id, dhash, confidence, resolution)
        self.accepted_by_type: dict[str, list[dict]] = {}
        # candidate_id -> record
        self.all_candidates: dict[str, dict] = {}

    def check_candidate(
        self,
        candidate_id: str,
        dhash: str,
        target_type: str,
    ) -> tuple[bool, str | None]:
        """
        Validates if candidate is acceptable or duplicates an existing accepted image.
        Returns: (is_acceptable, rejection_reason or None)
        """
        if not dhash:
            return True, None

        # 1. Check for cross-type collision across ALL other types
        for other_type, items in self.accepted_by_type.items():
            if other_type == target_type:
                continue
            for item in items:
                dist = hamming_distance(dhash, item["dhash"])
                if dist <= self.hamming_threshold:
                    return False, (
                        f"Cross-type collision (distance {dist} <= {self.hamming_threshold}) "
                        f"with {item['candidate_id']} in type '{other_type}'"
                    )

        # 2. Check within-type duplicate collision
        if target_type in self.accepted_by_type:
            for item in self.accepted_by_type[target_type]:
                dist = hamming_distance(dhash, item["dhash"])
                if dist <= self.hamming_threshold:
                    return False, (
                        f"Within-type duplicate (distance {dist} <= {self.hamming_threshold}) "
                        f"with {item['candidate_id']}"
                    )

        return True, None

    def register_candidate(
        self,
        candidate_id: str,
        dhash: str,
        target_type: str,
        confidence: float = 1.0,
        resolution: int = 0,
    ):
        record = {
            "candidate_id": candidate_id,
            "dhash": dhash,
            "target_type": target_type,
            "confidence": confidence,
            "resolution": resolution,
        }
        self.all_candidates[candidate_id] = record
        if target_type not in self.accepted_by_type:
            self.accepted_by_type[target_type] = []
        self.accepted_by_type[target_type].append(record)
