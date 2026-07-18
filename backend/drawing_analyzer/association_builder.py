from __future__ import annotations

from collections.abc import Sequence

from .geometry_entity import GeometryEntity
from .spatial_relation import SpatialRelation
from .text_geometry import ExtractedText


class AssociationBuilder:
    """Build aggregate counts for a spatial-association run."""

    def build_summary(
        self,
        texts: Sequence[ExtractedText],
        geometries: Sequence[GeometryEntity],
        relations: Sequence[SpatialRelation],
    ) -> dict[str, int]:
        return {
            "texts_processed": len(texts),
            "geometry_processed": len(geometries),
            "relations_created": len(relations),
            "inside_relations": sum(
                relation.relation_type == "inside" for relation in relations
            ),
            "near_relations": sum(
                relation.relation_type == "near" for relation in relations
            ),
            "intersects_relations": sum(
                relation.relation_type == "intersects" for relation in relations
            ),
        }
