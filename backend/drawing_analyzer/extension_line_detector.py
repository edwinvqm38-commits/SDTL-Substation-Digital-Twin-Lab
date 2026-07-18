from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import hypot
from typing import Any

from .geometry_entity import GeometryEntity


Point = tuple[float, float]


class ExtensionLineDetector:
    """Detect short, nearby lines perpendicular to a dimension line."""

    def __init__(
        self,
        distance_threshold: float = 10.0,
        max_length_ratio: float = 0.5,
        perpendicular_tolerance: float = 0.2,
    ) -> None:
        if distance_threshold < 0:
            raise ValueError("distance_threshold must be greater than or equal to zero")
        if max_length_ratio <= 0:
            raise ValueError("max_length_ratio must be greater than zero")
        if not 0 <= perpendicular_tolerance <= 1:
            raise ValueError("perpendicular_tolerance must be between zero and one")

        self.distance_threshold = float(distance_threshold)
        self.max_length_ratio = float(max_length_ratio)
        self.perpendicular_tolerance = float(perpendicular_tolerance)
        self.metadata: dict[str, Any] = {}

    def detect_extension_lines(
        self,
        dimension_line: GeometryEntity,
        geometries: Sequence[GeometryEntity],
    ) -> list[str]:
        dimension_points = self._line_points(dimension_line)
        if dimension_points is None:
            self.metadata = {
                "dimension_line_id": dimension_line.geometry_id,
                "reason": "dimension_line_has_no_valid_endpoints",
                "matches": [],
            }
            return []

        dimension_vector = self._vector(*dimension_points)
        dimension_length = self._length(dimension_vector)
        if dimension_length == 0:
            self.metadata = {
                "dimension_line_id": dimension_line.geometry_id,
                "reason": "dimension_line_has_zero_length",
                "matches": [],
            }
            return []

        matches: list[dict[str, Any]] = []
        for geometry in geometries:
            if (
                geometry.geometry_id == dimension_line.geometry_id
                or geometry.entity_type != "line"
                or geometry.document_id != dimension_line.document_id
                or geometry.page_number != dimension_line.page_number
            ):
                continue

            candidate_points = self._line_points(geometry)
            if candidate_points is None:
                continue
            candidate_vector = self._vector(*candidate_points)
            candidate_length = self._length(candidate_vector)
            if candidate_length == 0:
                continue

            endpoint_distance = min(
                hypot(
                    candidate_point[0] - dimension_point[0],
                    candidate_point[1] - dimension_point[1],
                )
                for candidate_point in candidate_points
                for dimension_point in dimension_points
            )
            normalized_dot = abs(
                dimension_vector[0] * candidate_vector[0]
                + dimension_vector[1] * candidate_vector[1]
            ) / (dimension_length * candidate_length)

            is_short = candidate_length <= dimension_length * self.max_length_ratio
            is_near = endpoint_distance <= self.distance_threshold
            is_perpendicular = normalized_dot <= self.perpendicular_tolerance
            if is_short and is_near and is_perpendicular:
                matches.append(
                    {
                        "geometry_id": geometry.geometry_id,
                        "length": candidate_length,
                        "endpoint_distance": endpoint_distance,
                        "normalized_dot": normalized_dot,
                    }
                )

        self.metadata = {
            "dimension_line_id": dimension_line.geometry_id,
            "candidates_checked": len(geometries),
            "extension_lines_found": len(matches),
            "distance_threshold": self.distance_threshold,
            "max_length_ratio": self.max_length_ratio,
            "perpendicular_tolerance": self.perpendicular_tolerance,
            "matches": matches,
        }
        return [match["geometry_id"] for match in matches]

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

    def _vector(self, start: Point, end: Point) -> Point:
        return end[0] - start[0], end[1] - start[1]

    def _length(self, vector: Point) -> float:
        return hypot(vector[0], vector[1])
