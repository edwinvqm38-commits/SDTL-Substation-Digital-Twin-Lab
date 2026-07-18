from __future__ import annotations

from backend.core.models import (
    Classification,
    EngineeringValue,
    Relationship,
    SDTLObject,
)


def test_relationship_between_objects() -> None:
    relationship = Relationship(
        relationship_id="REL-001",
        source_id="TR-001",
        target_id="BAY-001",
        relationship_type="located_in",
        properties={"status": "verified"},
    )

    assert relationship.source_id == "TR-001"
    assert relationship.target_id == "BAY-001"
    assert relationship.relationship_type == "located_in"
    assert relationship.properties["status"] == "verified"


def test_bim_classification() -> None:
    classification = Classification(
        classification_id="CLASS-001",
        system="BIM",
        code="IFC_Foundation",
        description="Concrete foundation",
    )

    assert classification.system == "BIM"
    assert classification.code == "IFC_Foundation"


def test_engineering_value() -> None:
    voltage = EngineeringValue(
        value=220_000,
        unit="V",
        description="Nominal system voltage",
    )

    assert voltage.value == 220_000
    assert voltage.unit == "V"
    assert voltage.description == "Nominal system voltage"


def test_sdtl_object_with_relationships() -> None:
    relationship = Relationship(
        relationship_id="REL-002",
        source_id="CB-001",
        target_id="TR-001",
        relationship_type="protects",
    )
    classification = Classification(
        classification_id="CLASS-002",
        system="BIM",
        code="IFC_ProtectiveDevice",
        description="Circuit breaker",
    )

    obj = SDTLObject(
        id="CB-001",
        object_type="circuit_breaker",
        category="electrical",
        name="220 kV Circuit Breaker",
        relationships=[relationship],
        classifications=[classification],
    )

    assert obj.relationships[0].target_id == "TR-001"
    assert obj.relationships[0].relationship_type == "protects"
    assert obj.classifications[0].system == "BIM"
