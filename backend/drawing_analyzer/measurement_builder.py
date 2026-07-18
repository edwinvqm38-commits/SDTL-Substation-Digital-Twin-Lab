from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from .dimension_entity import DimensionEntity
from .scale_detector import ScaleInformation


class MeasurementBuilder:
    """Build aggregate counts for detected dimensions, levels, scales, and units."""

    def build_summary(
        self,
        dimensions: Sequence[DimensionEntity],
        scales: Sequence[ScaleInformation],
    ) -> dict[str, int | dict[str, int]]:
        units = Counter(
            dimension.unit for dimension in dimensions if dimension.unit is not None
        )

        return {
            "dimensions_found": len(dimensions),
            "linear_dimensions": sum(
                dimension.dimension_type == "linear" for dimension in dimensions
            ),
            "levels_found": sum(
                dimension.dimension_type == "level" for dimension in dimensions
            ),
            "scales_found": len(scales),
            "units": dict(units),
        }
