from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from .dimension_entity import DimensionEntity


class NormalizedMeasurement(BaseModel):
    """Measurement converted to a requested unit while preserving its original value."""

    model_config = ConfigDict(extra="forbid")

    normalization_id: str
    dimension_id: str | None = None
    value: float
    unit: str
    original: str
    original_value: float
    original_unit: str
    conversion_factor: float


class UnitNormalizer:
    """Normalize supported linear measurements using deterministic conversion factors."""

    _METRES_PER_UNIT = {
        "mm": 0.001,
        "cm": 0.01,
        "m": 1.0,
    }

    def normalize(
        self,
        value: float,
        unit: str,
        target_unit: str = "m",
        original: str | None = None,
        dimension_id: str | None = None,
    ) -> NormalizedMeasurement:
        source_unit = unit.lower()
        normalized_target = target_unit.lower()
        if source_unit not in self._METRES_PER_UNIT:
            raise ValueError(f"Unsupported source unit: {unit}")
        if normalized_target not in self._METRES_PER_UNIT:
            raise ValueError(f"Unsupported target unit: {target_unit}")

        conversion_factor = (
            self._METRES_PER_UNIT[source_unit]
            / self._METRES_PER_UNIT[normalized_target]
        )
        return NormalizedMeasurement(
            normalization_id=f"NM-{uuid4().hex}",
            dimension_id=dimension_id,
            value=float(value) * conversion_factor,
            unit=normalized_target,
            original=original or f"{value:g} {source_unit}",
            original_value=float(value),
            original_unit=source_unit,
            conversion_factor=conversion_factor,
        )

    def normalize_dimension(
        self,
        dimension: DimensionEntity,
        target_unit: str = "m",
    ) -> NormalizedMeasurement:
        if dimension.value is None or dimension.unit is None:
            raise ValueError("Dimension must contain both value and unit")
        original = dimension.metadata.get("matched_text")
        return self.normalize(
            value=dimension.value,
            unit=dimension.unit,
            target_unit=target_unit,
            original=str(original) if original else None,
            dimension_id=dimension.dimension_id,
        )

    def normalize_dimensions(
        self,
        dimensions: Sequence[DimensionEntity],
        target_unit: str = "m",
    ) -> list[NormalizedMeasurement]:
        return [
            self.normalize_dimension(dimension, target_unit=target_unit)
            for dimension in dimensions
            if dimension.value is not None and dimension.unit in self._METRES_PER_UNIT
        ]
