from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import hypot
from typing import Any
from uuid import uuid4

from .dimension_association import DimensionAssociation
from .dimension_entity import DimensionEntity
from .geometry_entity import GeometryEntity
from .spatial_relation import SpatialRelation


class DimensionGeometryAssociationEngine:
    """Associate dimensions with nearby vector geometry using explicit geometric rules."""

    def __init__(self, distance_threshold: float = 100.0) -> None:
        if distance_threshold < 0:
            raise ValueError("distance_threshold must be greater than or equal to zero")
        self.distance_threshold = float(distance_threshold)

    def associate(
        self,
        dimensions: Sequence[DimensionEntity],
        geometries: Sequence[GeometryEntity],
        spatial_relations: Sequence[SpatialRelation] = (),
    ) -> list[DimensionAssociation]:
        relation_index = self._index_spatial_relations(spatial_relations)
        associations: list[DimensionAssociation] = []

        for dimension in dimensions:
            for geometry in geometries:
                if (
                    dimension.document_id != geometry.document_id
                    or dimension.page_number != geometry.page_number
                ):
                    continue

                spatial_relation = relation_index.get(
                    (dimension.text_source_id, geometry.geometry_id)
                )
                if spatial_relations and spatial_relation is None:
                    continue
                distance = self._candidate_distance(
                    dimension,
                    geometry,
                    spatial_relation,
                )
                if distance is None or distance > self.distance_threshold:
                    continue

                orientation = self._line_orientation(geometry)
                if dimension.dimension_type == "linear" and orientation == "horizontal":
                    relation_type = "defines_length"
                    confidence = 0.90
                    rule = "proximity_and_horizontal_orientation"
                elif dimension.dimension_type == "linear" and orientation == "vertical":
                    relation_type = "defines_height"
                    confidence = 0.90
                    rule = "proximity_and_vertical_orientation"
                else:
                    relation_type = "unknown"
                    confidence = 0.70
                    rule = "proximity_only"

                is_line = geometry.entity_type == "line"
                associations.append(
                    DimensionAssociation(
                        association_id=f"DAS-{uuid4().hex}",
                        dimension_id=dimension.dimension_id,
                        dimension_line_id=geometry.geometry_id if is_line else None,
                        target_geometry_id=None if is_line else geometry.geometry_id,
                        relation_type=relation_type,
                        confidence=confidence,
                        metadata={
                            "rule": rule,
                            "distance": distance,
                            "distance_threshold": self.distance_threshold,
                            "orientation": orientation,
                            "dimension_type": dimension.dimension_type,
                            "unit": dimension.unit,
                            "text_source_id": dimension.text_source_id,
                            "geometry_entity_type": geometry.entity_type,
                            "spatial_relation_id": (
                                spatial_relation.relation_id
                                if spatial_relation is not None
                                else None
                            ),
                        },
                    )
                )

        return associations

    def _index_spatial_relations(
        self,
        relations: Sequence[SpatialRelation],
    ) -> dict[tuple[str | None, str], SpatialRelation]:
        indexed: dict[tuple[str | None, str], SpatialRelation] = {}
        for relation in relations:
            key = (relation.text_id, relation.geometry_id)
            current = indexed.get(key)
            if current is None or self._distance_sort_value(
                relation.distance
            ) < self._distance_sort_value(current.distance):
                indexed[key] = relation
        return indexed

    def _candidate_distance(
        self,
        dimension: DimensionEntity,
        geometry: GeometryEntity,
        spatial_relation: SpatialRelation | None,
    ) -> float | None:
        if spatial_relation is not None and spatial_relation.distance is not None:
            return float(spatial_relation.distance)

        dimension_center = self._dimension_center(dimension)
        geometry_center = self._geometry_center(geometry)
        if dimension_center is None or geometry_center is None:
            return None
        return hypot(
            dimension_center[0] - geometry_center[0],
            dimension_center[1] - geometry_center[1],
        )

    def _dimension_center(
        self,
        dimension: DimensionEntity,
    ) -> tuple[float, float] | None:
        bbox = dimension.metadata.get("text_bbox")
        if not isinstance(bbox, Mapping):
            return None
        return self._mapping_center(bbox)

    def _geometry_center(
        self,
        geometry: GeometryEntity,
    ) -> tuple[float, float] | None:
        coordinates = geometry.coordinates
        bounding_box = coordinates.get("bounding_box")
        if isinstance(bounding_box, Mapping):
            center = self._mapping_center(bounding_box)
            if center is not None:
                return center

        center = self._mapping_center(coordinates)
        if center is not None:
            return center

        start = coordinates.get("start")
        end = coordinates.get("end")
        if isinstance(start, Mapping) and isinstance(end, Mapping):
            try:
                return (
                    (float(start["x"]) + float(end["x"])) / 2,
                    (float(start["y"]) + float(end["y"])) / 2,
                )
            except (KeyError, TypeError, ValueError):
                return None

        return None

    def _mapping_center(
        self,
        values: Mapping[str, Any],
    ) -> tuple[float, float] | None:
        try:
            x = float(values["x"])
            y = float(values["y"])
            if "x1" in values and "y1" in values:
                return (x + float(values["x1"])) / 2, (
                    y + float(values["y1"])
                ) / 2
            if "width" in values and "height" in values:
                return x + float(values["width"]) / 2, y + float(
                    values["height"]
                ) / 2
        except (KeyError, TypeError, ValueError):
            return None
        return None

    def _line_orientation(self, geometry: GeometryEntity) -> str | None:
        if geometry.entity_type != "line":
            return None

        start = geometry.coordinates.get("start")
        end = geometry.coordinates.get("end")
        if not isinstance(start, Mapping) or not isinstance(end, Mapping):
            return None

        try:
            delta_x = abs(float(end["x"]) - float(start["x"]))
            delta_y = abs(float(end["y"]) - float(start["y"]))
        except (KeyError, TypeError, ValueError):
            return None

        if delta_x == 0 and delta_y == 0:
            return None
        return "horizontal" if delta_x >= delta_y else "vertical"

    def _distance_sort_value(self, distance: float | None) -> float:
        return float("inf") if distance is None else float(distance)
