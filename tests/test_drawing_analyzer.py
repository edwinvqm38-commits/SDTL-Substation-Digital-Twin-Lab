from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from backend.core.models import DocumentAnalysis, ExtractionResult
from backend.drawing_analyzer import (
    DrawingAnalysisBuilder,
    DrawingMetadataExtractor,
    PDFDocumentReader,
    PDFTextExtractor,
)


@pytest.fixture
def simple_drawing_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "OC-320_demo.pdf"
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text(
        (72, 72),
        "OC-320\nVias internas Planta\nRevision B\n2026-07-17\nCivil",
    )
    document.set_metadata(
        {
            "title": "Vias internas Planta",
            "author": "SDTL Test",
        }
    )
    document.save(pdf_path)
    document.close()
    return pdf_path


def test_read_simple_pdf(simple_drawing_pdf: Path) -> None:
    result = PDFDocumentReader().read_document(simple_drawing_pdf)

    assert result["page_count"] == 1
    assert result["page_sizes"][0]["width"] == pytest.approx(595)
    assert result["page_sizes"][0]["height"] == pytest.approx(842)
    assert result["text_available"] is True
    assert result["images_available"] is False
    assert result["metadata"]["title"] == "Vias internas Planta"


def test_extract_text_by_page(simple_drawing_pdf: Path) -> None:
    pages = PDFTextExtractor().extract_text(simple_drawing_pdf)

    assert len(pages) == 1
    assert pages[0]["page"] == 1
    assert "OC-320" in pages[0]["text"]
    assert "Revision B" in pages[0]["text"]


def test_extract_conservative_drawing_metadata(simple_drawing_pdf: Path) -> None:
    pages = PDFTextExtractor().extract_text(simple_drawing_pdf)
    metadata = DrawingMetadataExtractor().extract_metadata(pages[0]["text"])

    assert metadata == {
        "title": "Vias internas Planta",
        "document_code": "OC-320",
        "revision": "B",
        "date": "2026-07-17",
        "discipline": "civil",
    }


def test_missing_drawing_metadata_returns_none() -> None:
    metadata = DrawingMetadataExtractor().extract_metadata(
        "General engineering notes without drawing identifiers"
    )

    assert metadata == {
        "title": None,
        "document_code": None,
        "revision": None,
        "date": None,
        "discipline": None,
    }


def test_build_document_analysis(simple_drawing_pdf: Path) -> None:
    document_info = PDFDocumentReader().read_document(simple_drawing_pdf)
    analysis = DrawingAnalysisBuilder().build_analysis(
        document_id="OC-320",
        extraction_metadata={
            "page_count": document_info["page_count"],
            "text_available": document_info["text_available"],
        },
    )

    assert isinstance(analysis, DocumentAnalysis)
    assert analysis.analysis_id.startswith("AN-")
    assert analysis.document_id == "OC-320"
    assert analysis.status == "completed"
    assert analysis.elements_detected == 0
    assert analysis.dimensions_found == 0
    assert analysis.extraction_metadata["advanced_detection"] is False


def test_build_extraction_result() -> None:
    extraction = DrawingAnalysisBuilder().build_extraction_result(
        document_id="OC-320",
        element_type="text",
        confidence=1.0,
        raw_data={"page": 1, "text": "OC-320"},
    )

    assert isinstance(extraction, ExtractionResult)
    assert extraction.extraction_id.startswith("EXT-")
    assert extraction.document_id == "OC-320"
    assert extraction.raw_data["page"] == 1
