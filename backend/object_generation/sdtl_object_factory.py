from __future__ import annotations

from typing import Any
from uuid import uuid4

from backend.drawing_analyzer.candidate_builder import EngineeringCandidate
from backend.sdtl_core.entities import CivilObject

from .object_mapper import ObjectMapper
from .object_proposal import ObjectProposal
from .object_validator import ObjectValidator


class SDTLObjectFactory:
    """Create reviewable SDTL proposals and civil entities from valid candidates."""

    def __init__(
        self,
        validator: ObjectValidator | None = None,
        mapper: ObjectMapper | None = None,
    ) -> None:
        self.validator = validator or ObjectValidator()
        self.mapper = mapper or ObjectMapper()

    def create_proposal(self, candidate: EngineeringCandidate) -> ObjectProposal:
        """Convert a complete candidate into a pending human-review proposal."""

        validation = self.validator.validate(candidate)
        if not validation["valid"]:
            failed = [name for name, passed in validation["checks"].items() if not passed]
            raise ValueError(
                "Engineering candidate cannot become an object proposal; "
                f"failed checks: {', '.join(failed)}"
            )

        dimensions = [
            {
                "reference": item.get("value"),
                "unit": item.get("unit"),
            }
            for item in candidate.evidence
            if item.get("type") == "dimension_match"
        ]
        properties: dict[str, Any] = {
            "dimensions": dimensions,
            "semantic_scores": dict(candidate.scores),
            "candidate_metadata": dict(candidate.metadata),
        }
        return ObjectProposal(
            id=f"PROP-{uuid4().hex}",
            candidate_source=candidate.id,
            object_type=self.mapper.map_type(candidate.possible_type),
            properties=properties,
            geometry_reference=candidate.source_geometry[0],
            traceability=dict(candidate.traceability),
            confidence=candidate.confidence,
        )

    def create_from_candidate(self, candidate: EngineeringCandidate) -> ObjectProposal:
        """Compatibility alias for the candidate-to-proposal operation."""

        return self.create_proposal(candidate)

    def create_object(
        self, proposal: ObjectProposal, object_id: str | None = None
    ) -> CivilObject:
        """Materialize a proposal as a non-active SDTL civil entity."""

        entity_class = self.mapper.entity_class(proposal.object_type)
        traceability = proposal.traceability
        source_pdf = traceability.get("source_pdf") or traceability.get("pdf")
        page = traceability.get("page")
        if not source_pdf or not isinstance(page, int) or isinstance(page, bool):
            raise ValueError("Object proposal requires source PDF and page traceability")

        return entity_class(
            id=object_id or f"OBJ-{uuid4().hex}",
            source_geometry=proposal.geometry_reference,
            coordinates=traceability.get("coordinates", []),
            dimensions=proposal.properties.get("dimensions", []),
            properties={
                key: value
                for key, value in proposal.properties.items()
                if key != "dimensions"
            },
            source_pdf=str(source_pdf),
            page=page,
            state="proposal",
            review=proposal.review.model_dump(),
        )

    def create_civil_object(
        self, proposal: ObjectProposal, object_id: str | None = None
    ) -> CivilObject:
        """Descriptive alias for create_object()."""

        return self.create_object(proposal, object_id=object_id)
