from __future__ import annotations

import json

from backend.drawing_analyzer import (
    DimensionAssociation,
    DimensionAssociationBuilder,
    DimensionEntity,
    DimensionGeometryAssociationEngine,
    DrawingAnalysisBuilder,
    GeometryEntity,
    SpatialRelation,
)


def make_dimension(
    dimension_id: str,
    text_id: str,
    unit: str = "m",
) -> DimensionEntity:
    return DimensionEntity(
        dimension_id=dimension_id,
        document_id="DOC-DIM-ASSOC-001",
        page_number=1,
        dimension_type="linear",
        value=12.5,
        unit=unit,
        text_source_id=text_id,
        confidence=0.95,
        metadata={
            "text_bbox": {"x": 140, "y": 100, "width": 20, "height": 10}
        },
    )


def make_line(geometry_id: str, orientation: str) -> GeometryEntity:
    if orientation == "horizontal":
        start, end = {"x": 100, "y": 120}, {"x": 200, "y": 120}
    else:
        start, end = {"x": 160, "y": 60}, {"x": 160, "y": 180}

    return GeometryEntity(
        geometry_id=geometry_id,
        document_id="DOC-DIM-ASSOC-001",
        page_number=1,
        entity_type="line",
        coordinates={"start": start, "end": end},
        confidence=1.0,
    )


def make_spatial_relation(
    relation_id: str,
    text_id: str,
    geometry_id: str,
    distance: float,
) -> SpatialRelation:
    return SpatialRelation(
        relation_id=relation_id,
        text_id=text_id,
        geometry_id=geometry_id,
        relation_type="near",
        distance=distance,
        confidence=0.80,
    )


def test_associate_horizontal_dimension() -> None:
    dimension = make_dimension("DIM-H-001", "TXT-H-001", unit="mm")
    geometry = make_line("GEO-H-001", "horizontal")
    spatial_relation = make_spatial_relation(
        "SPR-H-001", "TXT-H-001", "GEO-H-001", distance=15
    )

    association = DimensionGeometryAssociationEngine().associate(
        [dimension],
        [geometry],
        [spatial_relation],
    )[0]

    assert isinstance(association, DimensionAssociation)
    assert association.dimension_id == "DIM-H-001"
    assert association.dimension_line_id == "GEO-H-001"
    assert association.target_geometry_id is None
    assert association.relation_type == "defines_length"
    assert association.confidence == 0.90
    assert association.metadata["unit"] == "mm"
    assert association.metadata["spatial_relation_id"] == "SPR-H-001"


def test_associate_vertical_dimension() -> None:
    dimension = make_dimension("DIM-V-001", "TXT-V-001")
    geometry = make_line("GEO-V-001", "vertical")
    spatial_relation = make_spatial_relation(
        "SPR-V-001", "TXT-V-001", "GEO-V-001", distance=12
    )

    association = DimensionGeometryAssociationEngine().associate(
        [dimension],
        [geometry],
        [spatial_relation],
    )[0]

    assert association.relation_type == "defines_height"
    assert association.confidence == 0.90
    assert association.metadata["orientation"] == "vertical"


def test_proximity_only_has_reduced_confidence() -> None:
    dimension = make_dimension("DIM-U-001", "TXT-U-001")
    geometry = GeometryEntity(
        geometry_id="GEO-RECT-001",
        document_id="DOC-DIM-ASSOC-001",
        page_number=1,
        entity_type="rectangle",
        coordinates={"x": 100, "y": 100, "width": 100, "height": 50},
        confidence=1.0,
    )
    spatial_relation = make_spatial_relation(
        "SPR-U-001", "TXT-U-001", "GEO-RECT-001", distance=8
    )

    association = DimensionGeometryAssociationEngine().associate(
        [dimension], [geometry], [spatial_relation]
    )[0]

    assert association.relation_type == "unknown"
    assert association.confidence == 0.70
    assert association.dimension_line_id is None
    assert association.target_geometry_id == "GEO-RECT-001"


def test_distance_threshold_excludes_distant_geometry() -> None:
    dimension = make_dimension("DIM-FAR-001", "TXT-FAR-001")
    geometry = make_line("GEO-FAR-001", "horizontal")
    spatial_relation = make_spatial_relation(
        "SPR-FAR-001", "TXT-FAR-001", "GEO-FAR-001", distance=120
    )

    associations = DimensionGeometryAssociationEngine(
        distance_threshold=100
    ).associate([dimension], [geometry], [spatial_relation])

    assert associations == []


def test_dimension_association_json_and_summary() -> None:
    dimensions = [
        make_dimension("DIM-H-001", "TXT-H-001"),
        make_dimension("DIM-V-001", "TXT-V-001"),
    ]
    geometries = [
        make_line("GEO-H-001", "horizontal"),
        make_line("GEO-V-001", "vertical"),
    ]
    relations = [
        make_spatial_relation("SPR-H-001", "TXT-H-001", "GEO-H-001", 10),
        make_spatial_relation("SPR-V-001", "TXT-V-001", "GEO-V-001", 10),
    ]
    associations = DimensionGeometryAssociationEngine().associate(
        dimensions,
        geometries,
        relations,
    )
    summary = DimensionAssociationBuilder().build_summary(
        dimensions,
        geometries,
        associations,
    )
    payload = json.loads(associations[0].model_dump_json())

    assert payload["association_id"].startswith("DAS-")
    assert summary == {
        "dimensions_processed": 2,
        "geometry_processed": 2,
        "associations_created": 2,
        "length_associations": 1,
        "height_associations": 1,
        "unknown_associations": 0,
    }


def test_analysis_stores_dimension_association_metadata() -> None:
    summary = {
        "dimensions_processed": 2,
        "geometry_processed": 2,
        "associations_created": 2,
        "length_associations": 1,
        "height_associations": 1,
        "unknown_associations": 0,
    }
    analysis = DrawingAnalysisBuilder().build_analysis(
        document_id="DOC-DIM-ASSOC-001",
        dimensions_found=2,
        dimension_associations_detected=2,
        dimension_association_metadata=summary,
    )

    assert analysis.extraction_metadata["dimension_associations_detected"] == 2
    assert analysis.extraction_metadata["dimension_associations_created"] == 2
    assert analysis.extraction_metadata["dimension_association_metadata"] == summary
    assert analysis.extraction_metadata["analyzer_version"] == "1.5"
