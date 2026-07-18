from __future__ import annotations

from collections.abc import Sequence

from .geometry_entity import GeometryEntity


class GeometryAnalysisBuilder:
    """Summarize extracted vector entities by geometry type."""

    def build_summary(self, entities: Sequence[GeometryEntity]) -> dict[str, int]:
        counts = {
            "line": 0,
            "rectangle": 0,
            "polygon": 0,
            "curve": 0,
            "unknown": 0,
        }

        for entity in entities:
            entity_type = entity.entity_type
            if entity_type not in counts:
                entity_type = "unknown"
            counts[entity_type] += 1

        return {
            "total_entities": len(entities),
            "lines": counts["line"],
            "rectangles": counts["rectangle"],
            "polygons": counts["polygon"],
            "curves": counts["curve"],
            "unknown": counts["unknown"],
        }
