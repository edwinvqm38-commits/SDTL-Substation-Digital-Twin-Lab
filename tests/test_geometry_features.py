from __future__ import annotations

import json

import pytest

from backend.drawing_analyzer import (
    DimensionEntity,
    ExtractedText,
    GeometryEntity,
    GeometryFeature,
    GeometryFeatureExtractor,
)


DOCUMENT_ID = "DOC-FEATURE-001"


def test_rectangle_geometry_features() -> None:
    geometry = GeometryEntity(
        geometry_id="GEO-RECT-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="rectangle",
        coordinates={"x": 0, "y": 0, "width": 6, "height": 8},
        properties={"unit": "m"},
        confidence=1.0,
    )

    feature = GeometryFeatureExtractor().extract_feature(geometry)

    assert isinstance(feature, GeometryFeature)
    assert feature.properties["closed"] is True
    assert feature.properties["area"] == 48
    assert feature.properties["perimeter"] == 28
    assert feature.properties["width"] == 6
    assert feature.properties["length"] == 8
    assert feature.properties["aspect_ratio"] == pytest.approx(8 / 6)
    assert feature.properties["orientation"] == "vertical"


def test_polygon_area_and_perimeter() -> None:
    geometry = GeometryEntity(
        geometry_id="GEO-POLY-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="polygon",
        coordinates={
            "points": [
                {"x": 0, "y": 0},
                {"x": 4, "y": 0},
                {"x": 4, "y": 3},
            ]
        },
        confidence=1.0,
    )

    feature = GeometryFeatureExtractor().extract_feature(geometry)

    assert feature.properties["area"] == 6
    assert feature.properties["perimeter"] == 12
    assert feature.properties["closed"] is True


def test_line_length_and_open_state() -> None:
    geometry = GeometryEntity(
        geometry_id="GEO-LINE-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="line",
        coordinates={
            "start": {"x": 0, "y": 0},
            "end": {"x": 3, "y": 4},
        },
        confidence=1.0,
    )

    feature = GeometryFeatureExtractor().extract_feature(geometry)

    assert feature.properties["length"] == 5
    assert feature.properties["closed"] is False
    assert feature.properties["area"] == 0


def test_text_proximity_feature() -> None:
    geometry = GeometryEntity(
        geometry_id="GEO-TEXT-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="rectangle",
        coordinates={"x": 0, "y": 0, "width": 10, "height": 10},
        confidence=1.0,
    )
    text = ExtractedText(
        text_id="TXT-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        content="SALA ELECTRICA",
        x=4,
        y=4,
        width=2,
        height=2,
        confidence=1.0,
    )

    feature = GeometryFeatureExtractor(proximity_threshold=20).extract_feature(
        geometry,
        texts=[text],
    )

    assert feature.properties["nearby_text_count"] == 1
    assert feature.properties["nearest_text_distance"] == 0


def test_dimension_proximity_and_feature_serialization() -> None:
    geometry = GeometryEntity(
        geometry_id="GEO-DIM-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="rectangle",
        coordinates={"x": 0, "y": 0, "width": 8, "height": 5},
        confidence=1.0,
    )
    dimension = DimensionEntity(
        dimension_id="DIM-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        dimension_type="linear",
        value=8,
        unit="m",
        geometry_reference_id="GEO-DIM-001",
        confidence=0.95,
    )

    feature = GeometryFeatureExtractor().extract_feature(
        geometry,
        dimensions=[dimension],
    )
    payload = json.loads(feature.model_dump_json())

    assert feature.properties["nearby_dimension_count"] == 1
    assert feature.properties["nearest_dimension_distance"] == 0
    assert payload["source_geometry"] == "GEO-DIM-001"
