from __future__ import annotations

import json

import pytest

from backend.drawing_analyzer import EngineeringCandidate
from backend.object_generation import (
    ObjectMapper,
    ObjectProposal,
    ObjectValidator,
    SDTLObjectFactory,
)
from backend.sdtl_core.entities import CableTrench, ElectricalRoom, Foundation


def make_candidate(
    possible_type: str = "electrical_room",
    *,
    confidence: float = 0.93,
    source_pdf: str | None = "SE-PI-PL-OC-700.pdf",
) -> EngineeringCandidate:
    traceability = {
        "source_pdf": source_pdf,
        "page": 2,
        "geometry_id": "GEO-ROOM-001",
        "coordinates": [[10.0, 20.0], [18.0, 26.0]],
    }
    return EngineeringCandidate(
        id="CAND-001",
        possible_type=possible_type,
        confidence=confidence,
        source_geometry=["GEO-ROOM-001"],
        evidence=[
            {"type": "geometry_match", "value": "rectangle"},
            {"type": "text_match", "value": "SALA ELECTRICA"},
            {"type": "dimension_match", "value": "DIM-001", "unit": "m"},
        ],
        scores={"geometry_score": 0.35, "text_score": 0.30, "final": confidence},
        traceability=traceability,
        metadata={"catalog_code": possible_type.upper()},
    )


def test_candidate_is_converted_to_object_proposal() -> None:
    proposal = SDTLObjectFactory().create_proposal(make_candidate())

    assert isinstance(proposal, ObjectProposal)
    assert proposal.candidate_source == "CAND-001"
    assert proposal.object_type == "ElectricalRoom"
    assert proposal.confidence == 0.93


def test_low_confidence_candidate_is_rejected() -> None:
    with pytest.raises(ValueError, match="semantic"):
        SDTLObjectFactory().create_proposal(make_candidate(confidence=0.84))


def test_candidate_without_pdf_is_rejected() -> None:
    with pytest.raises(ValueError, match="traceability"):
        SDTLObjectFactory().create_proposal(make_candidate(source_pdf=None))


def test_electrical_room_is_created() -> None:
    factory = SDTLObjectFactory()
    room = factory.create_object(factory.create_proposal(make_candidate()))

    assert isinstance(room, ElectricalRoom)
    assert room.type == "ElectricalRoom"


def test_foundation_is_created() -> None:
    factory = SDTLObjectFactory()
    foundation = factory.create_object(
        factory.create_proposal(make_candidate("foundation"))
    )

    assert isinstance(foundation, Foundation)
    assert foundation.type == "Foundation"


def test_cable_trench_is_created() -> None:
    factory = SDTLObjectFactory()
    trench = factory.create_object(
        factory.create_proposal(make_candidate("cable_trench"))
    )

    assert isinstance(trench, CableTrench)
    assert trench.type == "CableTrench"


def test_generated_object_starts_as_pending_proposal() -> None:
    factory = SDTLObjectFactory()
    room = factory.create_object(factory.create_proposal(make_candidate()))

    assert room.state == "proposal"
    assert room.review.required is True
    assert room.review.approved is False
    assert room.review.reviewer is None


def test_proposal_is_json_serializable() -> None:
    proposal = SDTLObjectFactory().create_proposal(make_candidate())
    payload = json.loads(proposal.model_dump_json())

    assert payload["candidate_source"] == "CAND-001"
    assert payload["review_status"] == "pending_review"
    assert payload["review"] == {
        "required": True,
        "approved": False,
        "reviewer": None,
    }


def test_proposal_preserves_drawing_traceability() -> None:
    proposal = SDTLObjectFactory().create_proposal(make_candidate())

    assert proposal.geometry_reference == "GEO-ROOM-001"
    assert proposal.traceability["source_pdf"] == "SE-PI-PL-OC-700.pdf"
    assert proposal.traceability["page"] == 2
    assert proposal.traceability["coordinates"] == [[10.0, 20.0], [18.0, 26.0]]


@pytest.mark.parametrize(
    ("candidate_type", "object_type"),
    [
        ("electrical_room", "ElectricalRoom"),
        ("cable_trench", "CableTrench"),
        ("foundation", "Foundation"),
        ("fence", "Fence"),
        ("road", "Road"),
    ],
)
def test_object_mapper(candidate_type: str, object_type: str) -> None:
    assert ObjectMapper().map_type(candidate_type) == object_type


def test_validator_reports_independent_checks() -> None:
    result = ObjectValidator().validate(make_candidate())

    assert result == {
        "valid": True,
        "checks": {
            "geometry": True,
            "semantic": True,
            "traceability": True,
        },
    }


def test_pending_object_cannot_activate_automatically() -> None:
    factory = SDTLObjectFactory()
    room = factory.create_object(factory.create_proposal(make_candidate()))

    with pytest.raises(ValueError, match="Human approval"):
        room.activate()


def test_human_approval_allows_activation() -> None:
    factory = SDTLObjectFactory()
    room = factory.create_object(factory.create_proposal(make_candidate()))

    room.approve("engineer@sdtl.local")
    assert room.state == "approved"
    assert room.review.approved is True

    room.activate()
    assert room.state == "active"
