from __future__ import annotations

import json

import pytest

from backend.drawing_analyzer import (
    ArrowDetector,
    DimensionEntity,
    DimensionGeometryLink,
    DimensionTopology,
    DimensionTopologyAnalyzer,
    DrawingAnalysisBuilder,
    DrawingCoordinateSystemBuilder,
    DrawingScale,
    ExtractedText,
    GeometryEntity,
    ScaleDetector,
    TraceabilityMap,
    UnitNormalizer,
)


DOCUMENT_ID = "DOC-TOPOLOGY-001"


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
        geometry_id="GEO-TARGET-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="rectangle",
        coordinates={"x": 100, "y": 100, "width": 100, "height": 60},
        confidence=1.0,
    )


def make_dimension(dimension_id: str = "DIM-001") -> DimensionEntity:
    return DimensionEntity(
        dimension_id=dimension_id,
        document_id=DOCUMENT_ID,
        page_number=1,
        dimension_type="linear",
        value=8.0,
        unit="m",
        text_source_id="TXT-DIM-001",
        confidence=0.95,
    )


def make_link(
    dimension_id: str,
    dimension_line_id: str,
    relation_type: str,
) -> DimensionGeometryLink:
    return DimensionGeometryLink(
        link_id=f"DGL-{dimension_id}",
        dimension_id=dimension_id,
        dimension_line_id=dimension_line_id,
        target_geometry_id="GEO-TARGET-001",
        relation_type=relation_type,
        confidence=0.95,
    )


def horizontal_geometry() -> list[GeometryEntity]:
    return [
        make_line("GEO-DIM-001", (100, 70), (200, 70)),
        make_line("GEO-EXT-001", (100, 70), (100, 100)),
        make_line("GEO-EXT-002", (200, 70), (200, 100)),
        make_rectangle(),
    ]


def test_horizontal_dimension_with_two_extensions() -> None:
    topology = DimensionTopologyAnalyzer().analyze(
        make_dimension(),
        make_link("DIM-001", "GEO-DIM-001", "defines_length"),
        horizontal_geometry(),
    )

    assert isinstance(topology, DimensionTopology)
    assert topology.orientation == "horizontal"
    assert topology.extension_lines == ["GEO-EXT-001", "GEO-EXT-002"]
    assert topology.target_geometry_id == "GEO-TARGET-001"
    assert topology.valid is True


def test_vertical_dimension_topology() -> None:
    dimension = make_dimension("DIM-002")
    geometries = [
        make_line("GEO-DIM-002", (70, 100), (70, 160)),
        make_line("GEO-EXT-003", (70, 100), (100, 100)),
        make_line("GEO-EXT-004", (70, 160), (100, 160)),
        make_rectangle(),
    ]
    topology = DimensionTopologyAnalyzer().analyze(
        dimension,
        make_link("DIM-002", "GEO-DIM-002", "defines_height"),
        geometries,
    )

    assert topology.orientation == "vertical"
    assert set(topology.extension_lines) == {"GEO-EXT-003", "GEO-EXT-004"}
    assert topology.valid is True


def test_dimension_arrow_heads_are_detected() -> None:
    geometries = horizontal_geometry()
    geometries.extend(
        [
            GeometryEntity(
                geometry_id="GEO-ARROW-001",
                document_id=DOCUMENT_ID,
                page_number=1,
                entity_type="polygon",
                coordinates={
                    "points": [
                        {"x": 100, "y": 70},
                        {"x": 106, "y": 67},
                        {"x": 106, "y": 73},
                    ]
                },
                confidence=1.0,
            ),
            GeometryEntity(
                geometry_id="GEO-ARROW-002",
                document_id=DOCUMENT_ID,
                page_number=1,
                entity_type="polygon",
                coordinates={
                    "points": [
                        {"x": 200, "y": 70},
                        {"x": 194, "y": 67},
                        {"x": 194, "y": 73},
                    ]
                },
                confidence=1.0,
            ),
        ]
    )
    arrows = ArrowDetector().detect_arrows(geometries[0], geometries)
    topology = DimensionTopologyAnalyzer().analyze(
        make_dimension(),
        make_link("DIM-001", "GEO-DIM-001", "defines_length"),
        geometries,
    )

    assert len(arrows) == 2
    assert {arrow.direction for arrow in arrows} == {"left", "right"}
    assert set(topology.arrow_heads) == {"GEO-ARROW-001", "GEO-ARROW-002"}
    assert topology.confidence == 0.96


def test_dimension_without_arrows_remains_traceable() -> None:
    topology = DimensionTopologyAnalyzer().analyze(
        make_dimension(),
        make_link("DIM-001", "GEO-DIM-001", "defines_length"),
        horizontal_geometry(),
    )

    assert topology.arrow_heads == []
    assert topology.valid is True
    assert topology.confidence == 0.80
    assert topology.metadata["checks"]["arrow_heads_detected"] == 0


def test_normalize_millimetres_to_metres() -> None:
    normalized = UnitNormalizer().normalize(
        value=5000,
        unit="mm",
        target_unit="m",
        original="5000 mm",
    )

    assert normalized.value == 5
    assert normalized.unit == "m"
    assert normalized.original == "5000 mm"
    assert normalized.conversion_factor == 0.001


def test_transform_pdf_coordinates() -> None:
    scale = DrawingScale(
        document_id=DOCUMENT_ID,
        page_number=1,
        paper_units=1,
        real_units=100,
        unit="m",
        confidence=0.98,
    )
    builder = DrawingCoordinateSystemBuilder()
    coordinate_system = builder.build(
        document_id=DOCUMENT_ID,
        page_number=1,
        page_width=10,
        page_height=20,
        scale=scale,
    )

    assert builder.transform_point(coordinate_system, 1, 2) == pytest.approx(
        (100, -200)
    )
    assert coordinate_system.unit == "m"
    assert coordinate_system.metadata["transform_type"] == "pdf_to_world_matrix"


def test_detect_drawing_scale_model() -> None:
    text = ExtractedText(
        text_id="TXT-SCALE-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        content="ESCALA 1:50",
        x=10,
        y=10,
        width=50,
        height=10,
        confidence=1.0,
    )
    scale = ScaleDetector().detect_drawing_scales([text], unit="m")[0]

    assert scale.paper_units == 1
    assert scale.real_units == 50
    assert scale.unit == "m"
    assert scale.confidence == 0.98


def test_traceability_map_json() -> None:
    traceability = TraceabilityMap(
        source_pdf="SE-PI-PL-OC-320.pdf",
        page=2,
        geometry_id="GEO-TARGET-001",
        dimension_ids=["DIM-001"],
        coordinates=[[10, 20], [15, 20]],
        topology_ids=["DT-001"],
    )
    payload = json.loads(traceability.model_dump_json())

    assert traceability.references_dimension("DIM-001") is True
    assert payload["source_pdf"] == "SE-PI-PL-OC-320.pdf"
    assert payload["coordinates"] == [[10.0, 20.0], [15.0, 20.0]]


def test_analysis_builder_stores_v165_metadata() -> None:
    analysis = DrawingAnalysisBuilder().build_analysis(
        document_id=DOCUMENT_ID,
        scale_detected=True,
        units_normalized=True,
        dimension_topology_validated=True,
    )

    assert analysis.extraction_metadata["analysis_version"] == "1.6.5"
    assert analysis.extraction_metadata["analyzer_version"] == "1.6.5"
    assert analysis.extraction_metadata["scale_detected"] is True
    assert analysis.extraction_metadata["units_normalized"] is True
    assert analysis.extraction_metadata["dimension_topology_validated"] is True
