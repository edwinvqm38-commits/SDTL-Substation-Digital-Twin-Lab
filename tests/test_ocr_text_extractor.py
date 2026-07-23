from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from backend.drawing_analyzer import OCRTextExtractor


@pytest.fixture
def rendered_text_pdf(tmp_path: Path) -> Path:
    """A PDF with real embedded text, rendered here purely so OCR has
    something unambiguous to recognize -- this test exercises the OCR
    mechanism itself (rasterize -> Tesseract -> line grouping -> coordinate
    conversion), independent of whether native text extraction would also
    have worked.
    """

    document = fitz.open()
    page = document.new_page(width=400, height=200)
    page.insert_text(fitz.Point(40, 60), "SALA ELECTRICA", fontsize=24)
    page.insert_text(fitz.Point(40, 120), "8 m", fontsize=24)
    path = tmp_path / "ocr_sample.pdf"
    document.save(path)
    document.close()
    return path


def test_recovers_text_content(rendered_text_pdf: Path) -> None:
    texts = OCRTextExtractor().extract_text(rendered_text_pdf)

    contents = [text.content for text in texts]
    assert any("SALA" in content and "ELECTRICA" in content for content in contents)
    assert any("8" in content and "m" in content for content in contents)


def test_bounding_boxes_are_in_pdf_point_space(rendered_text_pdf: Path) -> None:
    texts = OCRTextExtractor().extract_text(rendered_text_pdf)

    sala = next(text for text in texts if "SALA" in text.content)
    # The page is 400x200 pt; a correctly scaled bbox must stay within it
    # (a units bug -- e.g. forgetting to divide by the render zoom -- would
    # produce coordinates several times larger than the page).
    assert 0 <= sala.x <= 400
    assert 0 <= sala.y <= 200
    assert 0 < sala.width <= 400
    assert 0 < sala.height <= 200


def test_assigns_document_id_and_page_number(rendered_text_pdf: Path) -> None:
    texts = OCRTextExtractor().extract_text(rendered_text_pdf, document_id="DOC-OCR-001")

    assert all(text.document_id == "DOC-OCR-001" for text in texts)
    assert all(text.page_number == 1 for text in texts)


def test_confidence_is_between_zero_and_one(rendered_text_pdf: Path) -> None:
    texts = OCRTextExtractor().extract_text(rendered_text_pdf)

    assert all(0.0 <= text.confidence <= 1.0 for text in texts)


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        OCRTextExtractor().extract_text(tmp_path / "missing.pdf")


def test_rejects_non_positive_dpi() -> None:
    with pytest.raises(ValueError, match="dpi"):
        OCRTextExtractor(dpi=0)
