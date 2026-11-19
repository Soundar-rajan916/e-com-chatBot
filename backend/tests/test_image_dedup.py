"""
Tests for Perceptual Hashing (dHash) & Deduplication Index
"""

from PIL import Image
from app.services.image_pipeline.dedup import (
    PerceptualDedupIndex,
    compute_dhash,
    hamming_distance,
)


def test_dhash_computation():
    # Create two test images: one gradient, one solid
    img1 = Image.new("RGB", (100, 100), color=(255, 255, 255))
    h1 = compute_dhash(img1)
    assert len(h1) == 16  # 64-bit hex is 16 chars

    img2 = Image.new("RGB", (100, 100), color=(0, 0, 0))
    h2 = compute_dhash(img2)
    assert len(h2) == 16


def test_hamming_distance():
    h1 = "0000000000000000"
    h2 = "000000000000000f"  # 'f' has 4 ones
    assert hamming_distance(h1, h2) == 4

    # Identical
    assert hamming_distance(h1, h1) == 0


def test_perceptual_dedup_cross_type_rejection():
    index = PerceptualDedupIndex(hamming_threshold=6)

    # Register candidate for cufflinks with a hash
    cufflink_hash = "abcdef0123456789"
    index.register_candidate("cufflink_1", cufflink_hash, "cufflinks")

    # Near-identical hash (distance 2) presented for wristwatch
    near_hash = "abcdef012345678b"  # 1 bit difference from 9 -> b
    assert hamming_distance(cufflink_hash, near_hash) == 1

    is_ok, reason = index.check_candidate("watch_1", near_hash, "wristwatch")
    assert is_ok is False
    assert "Cross-type collision" in reason
    assert "cufflinks" in reason


def test_perceptual_dedup_distinct_images_accepted():
    index = PerceptualDedupIndex(hamming_threshold=6)

    h1 = "ffff0000ffff0000"
    index.register_candidate("shirt_1", h1, "formal_dress_shirt")

    h2 = "0000ffff0000ffff"  # distance 32
    assert hamming_distance(h1, h2) > 6

    is_ok, reason = index.check_candidate("shirt_2", h2, "formal_dress_shirt")
    assert is_ok is True
    assert reason is None
