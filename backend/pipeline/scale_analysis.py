from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from backend.drawing_analyzer import (
    DimensionEntity,
    ExtractedText,
    GeometryEntity,
    ScaleDetector,
    UnitNormalizer,
)
from backend.drawing_analyzer.dimension_topology_analyzer import DimensionTopology


@dataclass
class ScaleAnalysis:
    """Honest answer to "does the app understand the drawing's scale":

    - declared_scale/declared_scale_confidence: a printed "ESCALA 1:N" (or
      similar) annotation, if the sheet has one -- surfaced for a human to
      see and cross-check, never used to place geometry.
    - meters_per_pdf_unit: an EMPIRICAL ratio derived from the sheet's own
      written dimension callouts (e.g. "20 m" next to a line that measures
      200 PDF units on this sheet), used to place objects at their true
      relative position. A callout is authoritative regardless of scale;
      trusting the declared ratio instead would require assuming the PDF's
      physical page size and print DPI, which this analyzer does not do.
    - sample_size: how many independent callout/geometry pairs the
      empirical ratio came from (0 means positions fall back to the
      origin, same as before this existed, rather than guessing).
    """

    declared_scale: str | None
    declared_scale_confidence: float | None
    meters_per_pdf_unit: float | None
    sample_size: int


class ScaleAnalyzer:
    """Detect a sheet's declared scale annotation and derive an empirical
    paper-to-real-world ratio from its own validated dimension callouts."""

    def __init__(self, unit_normalizer: UnitNormalizer | None = None) -> None:
        self.unit_normalizer = unit_normalizer or UnitNormalizer()

    def analyze(
        self,
        texts: list[ExtractedText],
        dimensions_by_id: dict[str, DimensionEntity],
        topologies: list[DimensionTopology],
        geometries_by_id: dict[str, GeometryEntity],
    ) -> ScaleAnalysis:
        declared = self._detect_declared_scale(texts)
        empirical_ratios = self._empirical_ratios(dimensions_by_id, topologies, geometries_by_id)

        declared_scale = None
        if declared is not None and declared.paper_units:
            declared_scale = f"1:{declared.real_units / declared.paper_units:g}"

        return ScaleAnalysis(
            declared_scale=declared_scale,
            declared_scale_confidence=declared.confidence if declared is not None else None,
            meters_per_pdf_unit=median(empirical_ratios) if empirical_ratios else None,
            sample_size=len(empirical_ratios),
        )

    @staticmethod
    def _detect_declared_scale(texts: list[ExtractedText]):
        scales = ScaleDetector().detect_drawing_scales(texts)
        if not scales:
            return None
        return max(scales, key=lambda scale: scale.confidence)

    def _empirical_ratios(
        self,
        dimensions_by_id: dict[str, DimensionEntity],
        topologies: list[DimensionTopology],
        geometries_by_id: dict[str, GeometryEntity],
    ) -> list[float]:
        ratios: list[float] = []
        for topology in topologies:
            if not topology.valid or topology.dimension_line is None:
                continue
            dimension = dimensions_by_id.get(topology.dimension_id)
            line = geometries_by_id.get(topology.dimension_line)
            if dimension is None or dimension.value is None or dimension.unit is None or line is None:
                continue

            paper_length = self._line_length(line)
            if paper_length <= 0:
                continue
            try:
                normalized = self.unit_normalizer.normalize(
                    dimension.value, dimension.unit, target_unit="m"
                )
            except ValueError:
                continue
            ratios.append(normalized.value / paper_length)
        return ratios

    @staticmethod
    def _line_length(geometry: GeometryEntity) -> float:
        start, end = geometry.coordinates.get("start"), geometry.coordinates.get("end")
        if not isinstance(start, dict) or not isinstance(end, dict):
            return 0.0
        return ((end["x"] - start["x"]) ** 2 + (end["y"] - start["y"]) ** 2) ** 0.5
