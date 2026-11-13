from pathlib import Path

from app.config import get_settings


def test_policy_files_consistency():
    settings = get_settings()
    policy_dir = Path(__file__).resolve().parent.parent / "data" / "policy"

    en_policy = (policy_dir / "returns_policy_en.md").read_text(encoding="utf-8")
    ta_policy = (policy_dir / "returns_policy_ta.md").read_text(encoding="utf-8")

    # Verify return window matches config (default 7 days)
    assert (
        f"{settings.RETURN_WINDOW_DAYS}-day return window" in en_policy
        or f"{settings.RETURN_WINDOW_DAYS} calendar days" in en_policy
    )
    assert f"{settings.RETURN_WINDOW_DAYS} நாட்கள்" in ta_policy

    # Verify refund auto-approval limit matches config (default 2000 INR)
    limit_str = f"{settings.REFUND_AUTO_APPROVE_LIMIT_INR:,}"
    assert f"INR {limit_str}" in en_policy or f"₹{limit_str}" in en_policy
    assert f"INR {limit_str}" in ta_policy or f"₹{limit_str}" in ta_policy

    # Verify key operational headings are present
    expected_headings = [
        "Returns and refund window",
        "Refund amounts and approval",
        "Refund timelines and mode",
        "Non-returnable items",
        "Damaged or wrong item",
        "Order cancellation",
        "Shipping and delivery timelines",
        "Payments and COD",
    ]
    for heading in expected_headings:
        assert f"## {heading}" in en_policy
        assert f"## {heading}" in ta_policy
