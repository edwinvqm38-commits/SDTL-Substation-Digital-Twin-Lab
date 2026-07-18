from __future__ import annotations

from collections.abc import Sequence

from .dimension_entity import DimensionEntity
from .dimension_geometry_link import DimensionGeometryLink


class DimensionGeometryLinkBuilder:
    """Build aggregate resolution metrics for dimension target links."""

    def build_summary(
        self,
        dimensions: Sequence[DimensionEntity],
        links: Sequence[DimensionGeometryLink],
    ) -> dict[str, int | float]:
        resolved_dimension_ids = {
            link.dimension_id for link in links if link.target_geometry_id is not None
        }
        average_confidence = (
            sum(link.confidence for link in links) / len(links) if links else 0.0
        )

        return {
            "dimensions_processed": len(dimensions),
            "links_created": len(links),
            "resolved_targets": len(resolved_dimension_ids),
            "unresolved_targets": max(
                0,
                len(dimensions) - len(resolved_dimension_ids),
            ),
            "average_confidence": round(average_confidence, 4),
        }
