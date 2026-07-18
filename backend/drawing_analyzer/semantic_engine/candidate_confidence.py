from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CandidateConfidence(BaseModel):
    """Deterministic evidence contribution breakdown for one semantic candidate."""

    model_config = ConfigDict(extra="forbid")

    geometry_score: float
    text_score: float
    dimension_score: float
    topology_score: float
    final: float


class CandidateConfidenceCalculator:
    """Calculate bounded semantic confidence from four independent evidence groups."""

    def calculate(
        self,
        geometry_match: float,
        text_match: float,
        dimension_match: float,
        topology_match: float,
    ) -> CandidateConfidence:
        geometry_score = 0.35 * self._bounded(geometry_match)
        text_score = 0.30 * self._bounded(text_match)
        dimension_score = 0.20 * self._bounded(dimension_match)
        topology_score = 0.10 * self._bounded(topology_match)
        final = geometry_score + text_score + dimension_score + topology_score
        return CandidateConfidence(
            geometry_score=round(geometry_score, 4),
            text_score=round(text_score, 4),
            dimension_score=round(dimension_score, 4),
            topology_score=round(topology_score, 4),
            final=round(final, 4),
        )

    def _bounded(self, value: float) -> float:
        return min(1.0, max(0.0, float(value)))
