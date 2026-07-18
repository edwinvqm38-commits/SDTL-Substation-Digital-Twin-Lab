from __future__ import annotations

from backend.core.models import (
    CoordinateReference,
    EngineeringDocument,
    ExtractionResult,
    ObjectTraceability,
    SDTLObject,
    SpatialPosition,
)


def test_coordinate_reference_creation() -> None:
    coordinate_reference = CoordinateReference(
        reference_id="CRS-UTM-18S",
        system="UTM",
        description="UTM zone 18 south",
    )

    assert coordinate_reference.reference_id == "CRS-UTM-18S"
    assert coordinate_reference.system == "UTM"


def test_spatial_position_creation() -> None:
    coordinate_reference = CoordinateReference(
        reference_id="CRS-LOCAL-001",
        system="LOCAL",
        description="Substation construction grid",
    )
    position = SpatialPosition(
        x=125.5,
        y=88.25,
        z=3.4,
        coordinate_system=coordinate_reference,
    )

    assert position.x == 125.5
    assert position.coordinate_system is not None
    assert position.coordinate_system.system == "LOCAL"


def test_document_object_traceability_creation() -> None:
    trace = ObjectTraceability(
        trace_id="TRACE-001",
        document_id="DOC-LAY-001",
        object_id="TR-001",
        relation_type="derived_from",
        page_number=2,
        region_reference="A4:C7",
        extraction_method="manual",
    )

    assert trace.document_id == "DOC-LAY-001"
    assert trace.object_id == "TR-001"
    assert trace.page_number == 2


def test_extraction_result_creation() -> None:
    extraction = ExtractionResult(
        extraction_id="EXT-001",
        document_id="DOC-LAY-001",
        element_type="dimension",
        confidence=0.98,
        geometry_reference="PAGE-2:BOX-14",
        raw_data={"value": 15, "unit": "m"},
    )

    assert extraction.element_type == "dimension"
    assert extraction.confidence == 0.98
    assert extraction.raw_data["unit"] == "m"


def test_sdtl_object_with_traceability() -> None:
    trace = ObjectTraceability(
        trace_id="TRACE-002",
        document_id="DOC-SLD-001",
        object_id="CB-001",
        relation_type="validated_by",
        page_number=1,
        extraction_method="ocr",
    )
    position = SpatialPosition(x=10.0, y=20.0, z=0.0)
    obj = SDTLObject(
        id="CB-001",
        object_type="circuit_breaker",
        category="electrical",
        name="220 kV Circuit Breaker",
        traceability=[trace],
        spatial_position=position,
    )

    assert obj.traceability[0].document_id == "DOC-SLD-001"
    assert obj.spatial_position is not None
    assert obj.spatial_position.y == 20.0


def test_engineering_document_with_extractions() -> None:
    extraction = ExtractionResult(
        extraction_id="EXT-002",
        document_id="DOC-SLD-001",
        element_type="symbol",
        confidence=0.92,
        raw_data={"symbol_type": "circuit_breaker"},
    )
    document = EngineeringDocument(
        document_id="DOC-SLD-001",
        name="220 kV Single-Line Diagram",
        document_type="PDF drawing",
        discipline="electrical",
        revision="C",
        status="approved",
        pages=1,
        extractions=[extraction],
    )

    assert document.extractions[0].extraction_id == "EXT-002"
    assert document.extractions[0].raw_data["symbol_type"] == "circuit_breaker"
