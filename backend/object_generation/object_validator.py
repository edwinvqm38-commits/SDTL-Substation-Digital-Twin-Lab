from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from backend.drawing_analyzer.candidate_builder import EngineeringCandidate


class ObjectValidator:
    """Validate that an engineering candidate is complete enough for review."""

    def __init__(self, minimum_confidence: float = 0.85) -> None:
        self.minimum_confidence = minimum_confidence

    def validate(self, candidate: EngineeringCandidate) -> dict[str, Any]:
        """Return independent geometry, semantic, and traceability checks."""

        dimension_evidence = self._evidence_of_type(candidate, "dimension_match")
        coordinates = candidate.traceability.get("coordinates")
        geometry_valid = bool(
            candidate.source_geometry
            and self._has_coordinates(coordinates)
            and dimension_evidence
            and any(item.get("unit") for item in dimension_evidence)
        )

        semantic_valid = bool(
            candidate.confidence >= self.minimum_confidence
            and candidate.possible_type
            and self._evidence_of_type(candidate, "text_match")
        )

        source_pdf = candidate.traceability.get("source_pdf") or candidate.traceability.get(
            "pdf"
        )
        page = candidate.traceability.get("page")
        origin = candidate.traceability.get("geometry_id") or (
            candidate.source_geometry[0] if candidate.source_geometry else None
        )
        traceability_valid = bool(
            source_pdf
            and isinstance(page, int)
            and not isinstance(page, bool)
            and page >= 1
            and origin
        )

        checks = {
            "geometry": geometry_valid,
            "semantic": semantic_valid,
            "traceability": traceability_valid,
        }
        return {"valid": all(checks.values()), "checks": checks}

    @staticmethod
    def _evidence_of_type(
        candidate: EngineeringCandidate, evidence_type: str
    ) -> list[dict[str, Any]]:
        return [
            item for item in candidate.evidence if item.get("type") == evidence_type
        ]

    @staticmethod
    def _has_coordinates(value: Any) -> bool:
        if isinstance(value, dict):
            return bool(value)
        return isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and bool(
            value
        )
