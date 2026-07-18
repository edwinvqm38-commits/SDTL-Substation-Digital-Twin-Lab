from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from backend.drawing_analyzer import (
    DrawingAnalysisBuilder,
    GeometryAnalysisBuilder,
    GeometryEntity,
    VectorGeometryExtractor,
)


@pytest.fixture
def vector_drawing_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "vector_drawing.pdf"
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.draw_line((50, 50), (180, 50), color=(1, 0, 0), width=2)
    page.draw_rect(
        fitz.Rect(60, 100, 200, 180),
        color=(0, 0, 1),
        width=1.5,
    )
    shape = page.new_shape()
    shape.draw_bezier((60, 250), (100, 200), (160, 300), (220, 250))
    shape.finish(color=(0, 1, 0), width=1)
    shape.commit()
    document.save(pdf_path)
    document.close()
    return pdf_path


def test_extract_vector_geometry(vector_drawing_pdf: Path) -> None:
    entities = VectorGeometryExtractor().extract_geometry(
        vector_drawing_pdf,
        document_id="DOC-VECTOR-001",
    )

    entity_types = {entity.entity_type for entity in entities}

    assert len(entities) >= 3
    assert {"line", "rectangle", "curve"}.issubset(entity_types)
    assert all(isinstance(entity, GeometryEntity) for entity in entities)
    assert all(entity.page_number == 1 for entity in entities)
    assert all(entity.document_id == "DOC-VECTOR-001" for entity in entities)


def test_geometry_entity_coordinates_and_properties(vector_drawing_pdf: Path) -> None:
    entities = VectorGeometryExtractor().extract_geometry(vector_drawing_pdf)
    rectangle = next(entity for entity in entities if entity.entity_type == "rectangle")

    assert rectangle.geometry_id.startswith("GEO-")
    assert rectangle.coordinates["x"] == pytest.approx(60)
    assert rectangle.coordinates["y"] == pytest.approx(100)
    assert rectangle.coordinates["width"] == pytest.approx(140)
    assert rectangle.coordinates["height"] == pytest.approx(80)
    assert rectangle.properties["line_width"] == pytest.approx(1.5)
    assert rectangle.properties["stroke_color"] == pytest.approx([0, 0, 1])
    assert rectangle.confidence == 1.0


def test_build_geometry_summary(vector_drawing_pdf: Path) -> None:
    entities = VectorGeometryExtractor().extract_geometry(vector_drawing_pdf)
    summary = GeometryAnalysisBuilder().build_summary(entities)

    assert summary["total_entities"] == len(entities)
    assert summary["lines"] >= 1
    assert summary["rectangles"] == 1
    assert summary["curves"] == 1
    assert sum(
        summary[key]
        for key in ("lines", "rectangles", "polygons", "curves", "unknown")
    ) == summary["total_entities"]


def test_geometry_entity_json_serialization(vector_drawing_pdf: Path) -> None:
    entity = VectorGeometryExtractor().extract_geometry(vector_drawing_pdf)[0]
    payload = json.loads(entity.model_dump_json())

    assert payload["geometry_id"].startswith("GEO-")
    assert payload["page_number"] == 1
    assert isinstance(payload["coordinates"], dict)
    assert isinstance(payload["properties"], dict)


def test_analysis_stores_geometry_metadata(vector_drawing_pdf: Path) -> None:
    entities = VectorGeometryExtractor().extract_geometry(vector_drawing_pdf)
    summary = GeometryAnalysisBuilder().build_summary(entities)
    analysis = DrawingAnalysisBuilder().build_analysis(
        document_id="DOC-VECTOR-001",
        geometry_entities_detected=len(entities),
        geometry_metadata=summary,
    )

    assert analysis.elements_detected == 0
    assert analysis.extraction_metadata["geometry_entities_detected"] == len(entities)
    assert analysis.extraction_metadata["vector_geometry_available"] is True
    assert analysis.extraction_metadata["geometry_metadata"] == summary
    assert analysis.extraction_metadata["analyzer_version"] == "1.2"
