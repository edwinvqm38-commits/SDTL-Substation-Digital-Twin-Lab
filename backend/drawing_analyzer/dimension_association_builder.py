from __future__ import annotations

from collections.abc import Sequence

from .dimension_association import DimensionAssociation
from .dimension_entity import DimensionEntity
from .geometry_entity import GeometryEntity


class DimensionAssociationBuilder:
    """Build aggregate counts for dimension-to-geometry associations."""

    def build_summary(
        self,
        dimensions: Sequence[DimensionEntity],
        geometries: Sequence[GeometryEntity],
        associations: Sequence[DimensionAssociation],
    ) -> dict[str, int]:
        return {
            "dimensions_processed": len(dimensions),
            "geometry_processed": len(geometries),
            "associations_created": len(associations),
            "length_associations": sum(
                association.relation_type == "defines_length"
                for association in associations
            ),
            "height_associations": sum(
                association.relation_type == "defines_height"
                for association in associations
            ),
            "unknown_associations": sum(
                association.relation_type == "unknown"
                for association in associations
            ),
        }
