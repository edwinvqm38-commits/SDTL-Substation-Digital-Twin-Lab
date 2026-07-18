from __future__ import annotations

import json

import pytest

from backend.drawing_analyzer import (
    AssociationBuilder,
    DrawingAnalysisBuilder,
    ExtractedText,
    GeometryEntity,
    SpatialAssociationEngine,
    SpatialRelation,
)


def make_text(
    text_id: str,
    x: float,
    y: float,
    width: float = 20,
    height: float = 10,
) -> ExtractedText:
    return ExtractedText(
        text_id=text_id,
        document_id="DOC-SPATIAL-001",
        page_number=1,
        content=text_id,
        x=x,
        y=y,
        width=width,
        height=height,
        font_size=10,
        font_name="Helvetica",
        confidence=1.0,
    )


def make_rectangle() -> GeometryEntity:
    return GeometryEntity(
        geometry_id="GEO-RECT-001",
        document_id="DOC-SPATIAL-001",
        page_number=1,
        entity_type="rectangle",
        coordinates={
            "x": 100,
            "y": 100,
            "x1": 200,
            "y1": 200,
            "width": 100,
            "height": 100,
        },
        confidence=1.0,
    )


def test_detect_inside_relation() -> None:
    text = make_text("TXT-INSIDE", x=120, y=130)
    relations = SpatialAssociationEngine().associate([text], [make_rectangle()])

    assert len(relations) == 1
    relation = relations[0]
    assert isinstance(relation, SpatialRelation)
    assert relation.relation_type == "inside"
    assert relation.confidence == 0.95
    assert relation.overlap_ratio == pytest.approx(1.0)


def test_detect_near_relation() -> None:
    text = make_text("TXT-NEAR", x=220, y=120)
    relations = SpatialAssociationEngine(distance_threshold=100).associate(
        [text],
        [make_rectangle()],
    )

    assert len(relations) == 1
    relation = relations[0]
    assert relation.relation_type == "near"
    assert relation.confidence == 0.80
    assert relation.distance is not None
    assert relation.distance < 100
    assert relation.overlap_ratio is None


def test_detect_intersection_relation() -> None:
    text = make_text("TXT-INTERSECTS", x=195, y=120)
    relations = SpatialAssociationEngine().associate([text], [make_rectangle()])

    assert len(relations) == 1
    relation = relations[0]
    assert relation.relation_type == "intersects"
    assert relation.confidence == 0.85
    assert relation.overlap_ratio == pytest.approx(0.25)


def test_spatial_relation_json_serialization() -> None:
    relation = SpatialAssociationEngine().associate(
        [make_text("TXT-JSON", x=120, y=130)],
        [make_rectangle()],
    )[0]
    payload = json.loads(relation.model_dump_json())

    assert payload["relation_id"].startswith("SPR-")
    assert payload["text_id"] == "TXT-JSON"
    assert payload["geometry_id"] == "GEO-RECT-001"
    assert payload["metadata"]["page_number"] == 1


def test_build_association_summary() -> None:
    texts = [
        make_text("TXT-INSIDE", x=120, y=130),
        make_text("TXT-NEAR", x=220, y=120),
        make_text("TXT-INTERSECTS", x=195, y=120),
    ]
    geometries = [make_rectangle()]
    relations = SpatialAssociationEngine().associate(texts, geometries)
    summary = AssociationBuilder().build_summary(texts, geometries, relations)

    assert summary == {
        "texts_processed": 3,
        "geometry_processed": 1,
        "relations_created": 3,
        "inside_relations": 1,
        "near_relations": 1,
        "intersects_relations": 1,
    }


def test_analysis_stores_association_metadata() -> None:
    summary = {
        "texts_processed": 3,
        "geometry_processed": 1,
        "relations_created": 3,
        "inside_relations": 1,
        "near_relations": 1,
        "intersects_relations": 1,
    }
    analysis = DrawingAnalysisBuilder().build_analysis(
        document_id="DOC-SPATIAL-001",
        text_blocks_detected=3,
        geometry_entities_detected=1,
        spatial_relations_detected=3,
        association_metadata=summary,
    )

    assert analysis.extraction_metadata["spatial_relations_detected"] == 3
    assert analysis.extraction_metadata["association_metadata"] == summary
    assert analysis.extraction_metadata["analyzer_version"] == "1.3"
