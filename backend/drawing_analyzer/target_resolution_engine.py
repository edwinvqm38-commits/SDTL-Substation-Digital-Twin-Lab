from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import hypot
from typing import Any
from uuid import uuid4

from .dimension_association import DimensionAssociation
from .dimension_entity import DimensionEntity
from .dimension_geometry_link import DimensionGeometryLink
from .extension_line_detector import ExtensionLineDetector
from .geometry_entity import GeometryEntity
from .spatial_relation import SpatialRelation


BoundingBox = tuple[float, float, float, float]
Point = tuple[float, float]


class DimensionTargetResolutionEngine:
    """Resolve measured target geometry using orientation, endpoints, and distance."""

    def __init__(
        self,
        distance_threshold: float = 100.0,
        endpoint_tolerance: float = 5.0,
        extension_line_detector: ExtensionLineDetector | None = None,
    ) -> None:
        if distance_threshold <= 0:
            raise ValueError("distance_threshold must be greater than zero")
        if endpoint_tolerance < 0:
            raise ValueError("endpoint_tolerance must be greater than or equal to zero")
        self.distance_threshold = float(distance_threshold)
        self.endpoint_tolerance = float(endpoint_tolerance)
        self.extension_line_detector = extension_line_detector or ExtensionLineDetector()

    def resolve(
        self,
        dimensions: Sequence[DimensionEntity],
        associations: Sequence[DimensionAssociation],
        geometries: Sequence[GeometryEntity],
        spatial_relations: Sequence[SpatialRelation] = (),
    ) -> list[DimensionGeometryLink]:
        dimensions_by_id = {dimension.dimension_id: dimension for dimension in dimensions}
        geometries_by_id = {geometry.geometry_id: geometry for geometry in geometries}
        spatial_index = {
            (relation.text_id, relation.geometry_id): relation
            for relation in spatial_relations
        }
        links: list[DimensionGeometryLink] = []

        for association in associations:
            dimension = dimensions_by_id.get(association.dimension_id)
            dimension_line = geometries_by_id.get(association.dimension_line_id)
            if dimension is None or dimension_line is None:
                links.append(
                    self._unresolved_link(
                        association,
                        reason="dimension_or_dimension_line_not_found",
                    )
                )
                continue

            extension_ids = self.extension_line_detector.detect_extension_lines(
                dimension_line,
                geometries,
            )
            extension_metadata = dict(self.extension_line_detector.metadata)
            excluded_ids = {dimension_line.geometry_id, *extension_ids}

            candidates: list[dict[str, Any]] = []
            for geometry in geometries:
                if (
                    geometry.geometry_id in excluded_ids
                    or geometry.document_id != dimension.document_id
                    or geometry.page_number != dimension.page_number
                ):
                    continue

                candidate = self._score_candidate(
                    dimension=dimension,
                    dimension_line=dimension_line,
                    geometry=geometry,
                    spatial_relation=spatial_index.get(
                        (dimension.text_source_id, geometry.geometry_id)
                    ),
                )
                if candidate is not None:
                    candidates.append(candidate)

            if not candidates:
                links.append(
                    self._unresolved_link(
                        association,
                        extension_ids=extension_ids,
                        reason="no_geometry_candidate_within_threshold",
                        extension_metadata=extension_metadata,
                    )
                )
                continue

            best = max(
                candidates,
                key=lambda candidate: (
                    candidate["score"],
                    -candidate["distance"],
                    candidate["geometry"].geometry_id,
                ),
            )
            geometry = best["geometry"]
            relation_type = self._relation_type(association, best["orientation"])
            confidence = self._confidence(
                best["orientation_compatible"],
                best["both_endpoints_match"],
            )

            links.append(
                DimensionGeometryLink(
                    link_id=f"DGL-{uuid4().hex}",
                    dimension_id=dimension.dimension_id,
                    dimension_line_id=dimension_line.geometry_id,
                    extension_geometry_ids=extension_ids,
                    target_geometry_id=geometry.geometry_id,
                    relation_type=relation_type,
                    confidence=confidence,
                    metadata={
                        "score": best["score"],
                        "orientation": best["orientation"],
                        "orientation_compatible": best["orientation_compatible"],
                        "endpoint_matches": best["endpoint_matches"],
                        "both_endpoints_match": best["both_endpoints_match"],
                        "distance": best["distance"],
                        "distance_threshold": self.distance_threshold,
                        "endpoint_tolerance": self.endpoint_tolerance,
                        "unit": dimension.unit,
                        "spatial_relation_id": best["spatial_relation_id"],
                        "extension_line_detection": extension_metadata,
                        "candidates_evaluated": [
                            self._candidate_metadata(candidate)
                            for candidate in candidates
                        ],
                    },
                )
            )

        return links

    def _score_candidate(
        self,
        dimension: DimensionEntity,
        dimension_line: GeometryEntity,
        geometry: GeometryEntity,
        spatial_relation: SpatialRelation | None,
    ) -> dict[str, Any] | None:
        dimension_points = self._line_points(dimension_line)
        dimension_bbox = self._geometry_bbox(dimension_line)
        target_bbox = self._geometry_bbox(geometry)
        if dimension_points is None or dimension_bbox is None or target_bbox is None:
            return None

        orientation = self._line_orientation(dimension_line)
        orientation_compatible = self._orientation_compatible(orientation, geometry)
        endpoint_matches = self._endpoint_matches(
            dimension_points,
            target_bbox,
            orientation,
        )
        both_endpoints_match = endpoint_matches == 2
        distance = self._bbox_distance(dimension_bbox, target_bbox)
        if distance > self.distance_threshold:
            return None

        orientation_score = 0.45 if orientation_compatible else 0.0
        endpoint_score = 0.35 if both_endpoints_match else 0.175 * endpoint_matches
        distance_score = 0.20 * max(
            0.0,
            1.0 - distance / self.distance_threshold,
        )
        score = orientation_score + endpoint_score + distance_score

        return {
            "geometry": geometry,
            "orientation": orientation,
            "orientation_compatible": orientation_compatible,
            "endpoint_matches": endpoint_matches,
            "both_endpoints_match": both_endpoints_match,
            "distance": distance,
            "score": score,
            "spatial_relation_id": (
                spatial_relation.relation_id if spatial_relation is not None else None
            ),
            "dimension_type": dimension.dimension_type,
        }

    def _unresolved_link(
        self,
        association: DimensionAssociation,
        extension_ids: list[str] | None = None,
        reason: str = "unresolved",
        extension_metadata: dict[str, Any] | None = None,
    ) -> DimensionGeometryLink:
        return DimensionGeometryLink(
            link_id=f"DGL-{uuid4().hex}",
            dimension_id=association.dimension_id,
            dimension_line_id=association.dimension_line_id,
            extension_geometry_ids=extension_ids or [],
            target_geometry_id=None,
            relation_type=(
                association.relation_type
                if association.relation_type
                in {"defines_length", "defines_height"}
                else "unknown"
            ),
            confidence=0.0,
            metadata={
                "reason": reason,
                "extension_line_detection": extension_metadata or {},
            },
        )

    def _relation_type(
        self,
        association: DimensionAssociation,
        orientation: str | None,
    ) -> str:
        if association.relation_type == "defines_length":
            return "defines_length"
        if association.relation_type == "defines_height":
            return "defines_height"
        if orientation == "horizontal":
            return "defines_length"
        if orientation == "vertical":
            return "defines_height"
        return "unknown"

    def _confidence(
        self,
        orientation_compatible: bool,
        both_endpoints_match: bool,
    ) -> float:
        if orientation_compatible and both_endpoints_match:
            return 0.95
        if orientation_compatible:
            return 0.85
        return 0.70

    def _orientation_compatible(
        self,
        orientation: str | None,
        geometry: GeometryEntity,
    ) -> bool:
        if orientation is None:
            return False
        if geometry.entity_type in {"rectangle", "polygon"}:
            return True
        if geometry.entity_type == "line":
            return self._line_orientation(geometry) == orientation
        return False

    def _endpoint_matches(
        self,
        dimension_points: tuple[Point, Point],
        target_bbox: BoundingBox,
        orientation: str | None,
    ) -> int:
        if orientation == "horizontal":
            dimension_values = sorted(point[0] for point in dimension_points)
            target_values = [target_bbox[0], target_bbox[2]]
        elif orientation == "vertical":
            dimension_values = sorted(point[1] for point in dimension_points)
            target_values = [target_bbox[1], target_bbox[3]]
        else:
            return 0

        return sum(
            abs(dimension_value - target_value) <= self.endpoint_tolerance
            for dimension_value, target_value in zip(
                dimension_values,
                target_values,
                strict=True,
            )
        )

    def _line_orientation(self, geometry: GeometryEntity) -> str | None:
        points = self._line_points(geometry)
        if points is None:
            return None
        delta_x = abs(points[1][0] - points[0][0])
        delta_y = abs(points[1][1] - points[0][1])
        if delta_x == 0 and delta_y == 0:
            return None
        return "horizontal" if delta_x >= delta_y else "vertical"

    def _line_points(self, geometry: GeometryEntity) -> tuple[Point, Point] | None:
        start = geometry.coordinates.get("start")
        end = geometry.coordinates.get("end")
        if not isinstance(start, Mapping) or not isinstance(end, Mapping):
            return None
        try:
            return (
                (float(start["x"]), float(start["y"])),
                (float(end["x"]), float(end["y"])),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _geometry_bbox(self, geometry: GeometryEntity) -> BoundingBox | None:
        coordinates = geometry.coordinates
        nested_bbox = coordinates.get("bounding_box")
        if isinstance(nested_bbox, Mapping):
            bbox = self._mapping_bbox(nested_bbox)
            if bbox is not None:
                return bbox

        bbox = self._mapping_bbox(coordinates)
        if bbox is not None:
            return bbox

        points = self._line_points(geometry)
        if points is not None:
            return (
                min(points[0][0], points[1][0]),
                min(points[0][1], points[1][1]),
                max(points[0][0], points[1][0]),
                max(points[0][1], points[1][1]),
            )

        polygon_points = coordinates.get("points")
        if isinstance(polygon_points, list) and polygon_points:
            try:
                x_values = [float(point["x"]) for point in polygon_points]
                y_values = [float(point["y"]) for point in polygon_points]
            except (KeyError, TypeError, ValueError):
                return None
            return min(x_values), min(y_values), max(x_values), max(y_values)
        return None

    def _mapping_bbox(self, values: Mapping[str, Any]) -> BoundingBox | None:
        try:
            x0 = float(values["x"])
            y0 = float(values["y"])
            if "x1" in values and "y1" in values:
                x1 = float(values["x1"])
                y1 = float(values["y1"])
            elif "width" in values and "height" in values:
                x1 = x0 + float(values["width"])
                y1 = y0 + float(values["height"])
            else:
                return None
        except (KeyError, TypeError, ValueError):
            return None
        return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

    def _bbox_distance(self, first: BoundingBox, second: BoundingBox) -> float:
        delta_x = max(second[0] - first[2], first[0] - second[2], 0.0)
        delta_y = max(second[1] - first[3], first[1] - second[3], 0.0)
        return hypot(delta_x, delta_y)

    def _candidate_metadata(self, candidate: dict[str, Any]) -> dict[str, Any]:
        return {
            "geometry_id": candidate["geometry"].geometry_id,
            "score": candidate["score"],
            "orientation_compatible": candidate["orientation_compatible"],
            "endpoint_matches": candidate["endpoint_matches"],
            "distance": candidate["distance"],
            "spatial_relation_id": candidate["spatial_relation_id"],
        }
