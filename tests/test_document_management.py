from __future__ import annotations

import json

from backend.core.models import (
    DocumentAnalysis,
    DocumentSet,
    EngineeringDocument,
    EngineeringValue,
    Project,
)


def test_project_creation() -> None:
    project = Project(
        project_id="PRJ-001",
        name="Central Substation Expansion",
        project_type="substation_expansion",
        description="Expansion of the 220 kV yard",
        voltage_levels=[
            EngineeringValue(value=220_000, unit="V", description="HV level")
        ],
        document_sets=["SET-ELEC-001"],
        objects=["TR-001", "CB-001"],
        status="design",
    )

    assert project.project_id == "PRJ-001"
    assert project.voltage_levels[0].value == 220_000
    assert project.document_sets == ["SET-ELEC-001"]


def test_document_set_creation() -> None:
    document_set = DocumentSet(
        set_id="SET-ELEC-001",
        name="Electrical Drawings",
        discipline="electrical",
        description="Primary electrical engineering drawings",
        documents=["DOC-SLD-001", "DOC-LAY-001"],
    )

    assert document_set.discipline == "electrical"
    assert document_set.documents == ["DOC-SLD-001", "DOC-LAY-001"]


def test_engineering_document_creation() -> None:
    document = EngineeringDocument(
        document_id="DOC-SLD-001",
        name="220 kV Single-Line Diagram",
        document_type="PDF drawing",
        discipline="electrical",
        revision="B",
        status="approved",
        source_file="documents/SLD-220KV-RB.pdf",
        pages=3,
        metadata={"drawing_number": "SLD-220-001", "scale": "NTS"},
    )

    assert document.revision == "B"
    assert document.pages == 3
    assert document.metadata["drawing_number"] == "SLD-220-001"


def test_document_analysis_creation() -> None:
    analysis = DocumentAnalysis(
        analysis_id="AN-001",
        document_id="DOC-SLD-001",
        status="completed",
        elements_detected=24,
        dimensions_found=8,
        references_found=5,
        sections_found=2,
        extraction_metadata={"engine": "manual-baseline"},
    )

    assert analysis.document_id == "DOC-SLD-001"
    assert analysis.elements_detected == 24
    assert analysis.extraction_metadata["engine"] == "manual-baseline"


def test_document_management_json_serialization() -> None:
    document = EngineeringDocument(
        document_id="DOC-SPEC-001",
        name="Power Transformer Specification",
        document_type="technical_specification",
        discipline="electrical",
        revision="0",
        status="draft",
        pages=18,
        metadata={"language": "en", "confidential": False},
    )

    payload = json.loads(document.model_dump_json())

    assert payload["document_id"] == "DOC-SPEC-001"
    assert payload["source_file"] is None
    assert payload["metadata"]["confidential"] is False
