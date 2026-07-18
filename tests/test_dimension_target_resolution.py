from __future__ import annotations

import json

import pytest

from backend.drawing_analyzer import (
    DimensionAssociation,
    DimensionEntity,
    DimensionGeometryLink,
    DimensionGeometryLinkBuilder,
    DimensionTargetResolutionEngine,
    DrawingAnalysisBuilder,
    ExtensionLineDetector,
    GeometryEntity,
)


DOCUMENT_ID = "DOC-TARGET-001"


def make_line(
    geometry_id: str,
    start: tuple[float, float],
    end: tuple[float, float],
) -> GeometryEntity:
    return GeometryEntity(
        geometry_id=geometry_id,
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="line",
        coordinates={
            "start": {"x": start[0], "y": start[1]},
            "end": {"x": end[0], "y": end[1]},
        },
        confidence=1.0,
    )


def make_rectangle() -> GeometryEntity:
    return GeometryEntity(
        geometry_id="GEO-FOUND-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="rectangle",
        coordinates={
            "x": 100,
            "y": 100,
            "x1": 200,
            "y1": 160,
            "width": 100,
            "height": 60,
        },
        confidence=1.0,
    )


def make_dimension(
    dimension_id: str,
    text_id: str,
    value: float,
) -> DimensionEntity:
    return DimensionEntity(
        dimension_id=dimension_id,
        document_id=DOCUMENT_ID,
        page_number=1,
        dimension_type="linear",
        value=value,
        unit="m",
        text_source_id=text_id,
        confidence=0.95,
    )


def test_detect_extension_lines_for_horizontal_dimension() -> None:
    dimension_line = make_line("GEO-DIM-001", (100, 70), (200, 70))
    extension_lines = [
        make_line("GEO-EXT-001", (100, 70), (100, 100)),
        make_line("GEO-EXT-002", (200, 70), (200, 100)),
    ]
    detector = ExtensionLineDetector()

    detected = detector.detect_extension_lines(
        dimension_line,
        [dimension_line, *extension_lines, make_rectangle()],
    )

    assert detected == ["GEO-EXT-001", "GEO-EXT-002"]
    assert detector.metadata["extension_lines_found"] == 2


def test_resolve_horizontal_dimension_target() -> None:
    dimension = make_dimension("DIM-001", "TXT-DIM-001", value=8.0)
    association = DimensionAssociation(
        association_id="DAS-001",
        dimension_id="DIM-001",
        dimension_line_id="GEO-DIM-001",
        relation_type="defines_length",
        confidence=0.90,
    )
    geometries = [
        make_line("GEO-DIM-001", (100, 70), (200, 70)),
        make_line("GEO-EXT-001", (100, 70), (100, 100)),
        make_line("GEO-EXT-002", (200, 70), (200, 100)),
        make_rectangle(),
    ]

    link = DimensionTargetResolutionEngine().resolve(
        [dimension],
        [association],
        geometries,
    )[0]
    payload = json.loads(link.model_dump_json())

    assert isinstance(link, DimensionGeometryLink)
    assert link.target_geometry_id == "GEO-FOUND-001"
    assert link.dimension_line_id == "GEO-DIM-001"
    assert link.extension_geometry_ids == ["GEO-EXT-001", "GEO-EXT-002"]
    assert link.relation_type == "defines_length"
    assert link.confidence == 0.95
    assert link.metadata["both_endpoints_match"] is True
    assert payload["link_id"].startswith("DGL-")


def test_resolve_vertical_dimension_target() -> None:
    dimension = make_dimension("DIM-002", "TXT-DIM-002", value=6.0)
    association = DimensionAssociation(
        association_id="DAS-002",
        dimension_id="DIM-002",
        dimension_line_id="GEO-DIM-002",
        relation_type="defines_height",
        confidence=0.90,
    )
    geometries = [
        make_line("GEO-DIM-002", (70, 100), (70, 160)),
        make_line("GEO-EXT-003", (70, 100), (100, 100)),
        make_line("GEO-EXT-004", (70, 160), (100, 160)),
        make_rectangle(),
    ]

    link = DimensionTargetResolutionEngine().resolve(
        [dimension], [association], geometries
    )[0]

    assert link.target_geometry_id == "GEO-FOUND-001"
    assert link.relation_type == "defines_height"
    assert link.confidence == 0.95
    assert set(link.extension_geometry_ids) == {"GEO-EXT-003", "GEO-EXT-004"}


def test_unresolved_dimension_without_target_geometry() -> None:
    dimension = make_dimension("DIM-003", "TXT-DIM-003", value=5.0)
    association = DimensionAssociation(
        association_id="DAS-003",
        dimension_id="DIM-003",
        dimension_line_id="GEO-DIM-003",
        relation_type="defines_length",
        confidence=0.90,
    )
    geometries = [make_line("GEO-DIM-003", (300, 300), (400, 300))]

    link = DimensionTargetResolutionEngine().resolve(
        [dimension], [association], geometries
    )[0]

    assert link.target_geometry_id is None
    assert link.confidence == 0.0
    assert link.metadata["reason"] == "no_geometry_candidate_within_threshold"


def test_dimension_geometry_link_summary() -> None:
    dimensions = [
        make_dimension("DIM-001", "TXT-001", 8.0),
        make_dimension("DIM-002", "TXT-002", 6.0),
        make_dimension("DIM-003", "TXT-003", 5.0),
    ]
    links = [
        DimensionGeometryLink(
            link_id="DGL-001",
            dimension_id="DIM-001",
            dimension_line_id="GEO-DIM-001",
            target_geometry_id="GEO-FOUND-001",
            relation_type="defines_length",
            confidence=0.95,
        ),
        DimensionGeometryLink(
            link_id="DGL-002",
            dimension_id="DIM-002",
            dimension_line_id="GEO-DIM-002",
            target_geometry_id="GEO-FOUND-001",
            relation_type="defines_height",
            confidence=0.95,
        ),
        DimensionGeometryLink(
            link_id="DGL-003",
            dimension_id="DIM-003",
            dimension_line_id="GEO-DIM-003",
            target_geometry_id=None,
            relation_type="defines_length",
            confidence=0.0,
        ),
    ]

    summary = DimensionGeometryLinkBuilder().build_summary(dimensions, links)

    assert summary == {
        "dimensions_processed": 3,
        "links_created": 3,
        "resolved_targets": 2,
        "unresolved_targets": 1,
        "average_confidence": pytest.approx(0.6333),
    }


def test_analysis_stores_dimension_target_metadata() -> None:
    summary = {
        "dimensions_processed": 3,
        "links_created": 3,
        "resolved_targets": 2,
        "unresolved_targets": 1,
        "average_confidence": 0.6333,
    }
    analysis = DrawingAnalysisBuilder().build_analysis(
        document_id=DOCUMENT_ID,
        dimensions_found=3,
        dimension_target_links_detected=3,
        dimension_target_metadata=summary,
    )

    assert analysis.extraction_metadata["dimension_target_links_detected"] == 3
    assert analysis.extraction_metadata["dimension_links_created"] == 3
    assert analysis.extraction_metadata["resolved_targets"] == 2
    assert analysis.extraction_metadata["dimension_target_metadata"] == summary
    assert analysis.extraction_metadata["analyzer_version"] == "1.6"
