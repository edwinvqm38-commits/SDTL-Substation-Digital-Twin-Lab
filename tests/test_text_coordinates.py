from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from backend.drawing_analyzer import (
    CoordinateTextExtractor,
    DrawingAnalysisBuilder,
    ExtractedText,
    PDFTextExtractor,
)


@pytest.fixture
def coordinate_text_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "coordinate_text.pdf"
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text(
        (100, 150),
        "Transformer TR01",
        fontsize=12,
        fontname="helv",
    )
    page.insert_text(
        (200, 300),
        "Elevation +3.50 m",
        fontsize=10,
        fontname="helv",
    )
    document.save(pdf_path)
    document.close()
    return pdf_path


def test_extract_text_with_coordinates(coordinate_text_pdf: Path) -> None:
    extracted = CoordinateTextExtractor().extract_text(
        coordinate_text_pdf,
        document_id="DOC-COORD-001",
    )

    assert len(extracted) == 2
    assert all(isinstance(item, ExtractedText) for item in extracted)

    first = extracted[0]
    assert first.document_id == "DOC-COORD-001"
    assert first.page_number == 1
    assert first.content == "Transformer TR01"
    assert first.x == pytest.approx(100)
    assert first.y > 0
    assert first.width > 0
    assert first.height > 0
    assert first.font_size == pytest.approx(12)
    assert first.font_name == "Helvetica"
    assert first.confidence == 1.0


def test_pdf_text_extractor_preserves_v1_api(coordinate_text_pdf: Path) -> None:
    extractor = PDFTextExtractor()

    pages = extractor.extract_text(coordinate_text_pdf)
    positioned = extractor.extract_text_with_coordinates(coordinate_text_pdf)

    assert pages[0]["page"] == 1
    assert "Transformer TR01" in pages[0]["text"]
    assert positioned[0].document_id == "coordinate_text"


def test_extracted_text_json_serialization(coordinate_text_pdf: Path) -> None:
    extracted = PDFTextExtractor().extract_text_with_coordinates(
        coordinate_text_pdf,
        document_id="DOC-COORD-001",
    )[0]

    payload = json.loads(extracted.model_dump_json())

    assert payload["text_id"].startswith("TXT-")
    assert payload["content"] == "Transformer TR01"
    assert payload["page_number"] == 1
    assert payload["width"] > 0
    assert payload["font_size"] == pytest.approx(12)


def test_analysis_stores_coordinate_text_count(coordinate_text_pdf: Path) -> None:
    extracted = PDFTextExtractor().extract_text_with_coordinates(coordinate_text_pdf)
    analysis = DrawingAnalysisBuilder().build_analysis(
        document_id="DOC-COORD-001",
        text_blocks_detected=len(extracted),
        coordinates_available=bool(extracted),
    )

    assert analysis.elements_detected == 0
    assert analysis.extraction_metadata["text_blocks_detected"] == 2
    assert analysis.extraction_metadata["coordinates_available"] is True
    assert analysis.extraction_metadata["analyzer_version"] == "1.1"
