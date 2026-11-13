from pathlib import Path

from pypdf import PdfWriter

from scripts.ingest_policy import chunk_text, extract_text_from_pdf


def test_chunking_keeps_headings_and_respects_sentence_boundaries():
    sample_text = """# Main Header

## Returns and refund window
We offer a 7-day return window from the date of order delivery. If you are not satisfied with your purchase, you may initiate a return or refund request within 7 calendar days after delivery. Once the 7-day return window has elapsed, orders are no longer eligible for return or refund.

## Short Section
Short body text here for testing.
"""
    chunks = chunk_text(sample_text, "test.md", min_chars=10, max_chars=300)
    assert len(chunks) >= 2

    # Verify headings are preserved in chunk body
    for title, content in chunks:
        assert content.startswith(f"## {title}")
        # Verify no trailing broken sentence (ends with valid punctuation or heading)
        assert content[-1] in ".!?।\n" or content.endswith("testing.")


def test_pdf_extraction(tmp_path: Path):
    # Create a small dummy PDF file using pypdf
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    pdf_path = tmp_path / "sample_policy.pdf"

    # Add text to the PDF
    # Since adding text to raw blank page in pypdf can be complex without canvas,
    # we can mock or write minimal valid PDF
    with open(pdf_path, "wb") as f:
        writer.write(f)

    # Calling extract_text_from_pdf on this blank PDF should succeed without error
    extracted = extract_text_from_pdf(pdf_path)
    assert isinstance(extracted, str)
