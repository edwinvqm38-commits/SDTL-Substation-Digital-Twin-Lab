from __future__ import annotations

import json

from backend.drawing_analyzer import (
    DimensionDetector,
    DimensionEntity,
    DrawingAnalysisBuilder,
    ExtractedText,
    MeasurementBuilder,
    ScaleDetector,
    ScaleInformation,
)


def make_text(text_id: str, content: str) -> ExtractedText:
    return ExtractedText(
        text_id=text_id,
        document_id="DOC-MEASURE-001",
        page_number=1,
        content=content,
        x=100,
        y=100,
        width=80,
        height=12,
        font_size=10,
        font_name="Helvetica",
        confidence=1.0,
    )


def test_detect_linear_dimension_in_metres() -> None:
    dimension = DimensionDetector().detect_dimensions(
        [make_text("TXT-DIM-001", "12.50 m")]
    )[0]

    assert isinstance(dimension, DimensionEntity)
    assert dimension.dimension_type == "linear"
    assert dimension.value == 12.50
    assert dimension.unit == "m"
    assert dimension.text_source_id == "TXT-DIM-001"
    assert dimension.confidence == 0.95


def test_detect_linear_dimension_in_millimetres() -> None:
    dimension = DimensionDetector().detect_dimensions(
        [make_text("TXT-DIM-002", "2500 mm")]
    )[0]

    assert dimension.dimension_type == "linear"
    assert dimension.value == 2500
    assert dimension.unit == "mm"


def test_detect_diameter() -> None:
    dimension = DimensionDetector().detect_dimensions(
        [make_text("TXT-DIM-003", "Ø600")]
    )[0]
    payload = json.loads(dimension.model_dump_json())

    assert dimension.dimension_type == "diameter"
    assert dimension.value == 600
    assert dimension.unit is None
    assert payload["dimension_id"].startswith("DIM-")


def test_detect_constructive_levels() -> None:
    detector = DimensionDetector()
    dimensions = detector.detect_dimensions(
        [
            make_text("TXT-LEVEL-001", "+3.20"),
            make_text("TXT-LEVEL-002", "NPT +0.50"),
        ]
    )

    assert len(dimensions) == 2
    assert all(dimension.dimension_type == "level" for dimension in dimensions)
    assert dimensions[0].value == 3.20
    assert dimensions[0].unit is None
    assert dimensions[1].value == 0.50
    assert dimensions[1].confidence == 0.95


def test_detect_drawing_scale() -> None:
    scale = ScaleDetector().detect_scales(
        [make_text("TXT-SCALE-001", "ESCALA 1:100")]
    )[0]

    assert isinstance(scale, ScaleInformation)
    assert scale.numerator == 1
    assert scale.denominator == 100
    assert scale.confidence == 0.98
    assert scale.metadata["text_source_id"] == "TXT-SCALE-001"


def test_build_measurement_summary() -> None:
    texts = [
        make_text("TXT-DIM-001", "12.50 m"),
        make_text("TXT-DIM-002", "2500 mm"),
        make_text("TXT-DIM-003", "Ø600"),
        make_text("TXT-LEVEL-001", "+3.20"),
    ]
    dimensions = DimensionDetector().detect_dimensions(texts)
    scales = ScaleDetector().detect_scales(
        [make_text("TXT-SCALE-001", "S=1:100")]
    )
    summary = MeasurementBuilder().build_summary(dimensions, scales)

    assert summary == {
        "dimensions_found": 4,
        "linear_dimensions": 2,
        "levels_found": 1,
        "scales_found": 1,
        "units": {"m": 1, "mm": 1},
    }


def test_analysis_stores_measurement_metadata() -> None:
    summary = {
        "dimensions_found": 4,
        "linear_dimensions": 2,
        "levels_found": 1,
        "scales_found": 1,
        "units": {"m": 1, "mm": 1},
    }
    analysis = DrawingAnalysisBuilder().build_analysis(
        document_id="DOC-MEASURE-001",
        dimensions_found=4,
        scales_found=1,
        measurement_metadata=summary,
    )

    assert analysis.dimensions_found == 4
    assert analysis.extraction_metadata["dimensions_found"] == 4
    assert analysis.extraction_metadata["scales_found"] == 1
    assert analysis.extraction_metadata["measurement_metadata"] == summary
    assert analysis.extraction_metadata["analyzer_version"] == "1.4"
