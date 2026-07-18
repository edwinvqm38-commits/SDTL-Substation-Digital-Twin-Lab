from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import combinations
from math import hypot
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .geometry_entity import GeometryEntity


Point = tuple[float, float]


class ArrowDetection(BaseModel):
    """Geometric arrow-head candidate detected near a dimension-line endpoint."""

    model_config = ConfigDict(extra="forbid")

    id: str
    geometry_id: str
    type: str
    direction: str
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArrowDetector:
    """Detect small triangular or converging-line arrow candidates by explicit rules."""

    def __init__(
        self,
        endpoint_distance_threshold: float = 10.0,
        max_arrow_size: float = 15.0,
    ) -> None:
        if endpoint_distance_threshold < 0 or max_arrow_size <= 0:
            raise ValueError("Arrow detection thresholds must be positive")
        self.endpoint_distance_threshold = float(endpoint_distance_threshold)
        self.max_arrow_size = float(max_arrow_size)

    def detect_arrows(
        self,
        dimension_line: GeometryEntity,
        geometries: Sequence[GeometryEntity],
    ) -> list[ArrowDetection]:
        endpoints = self._line_points(dimension_line)
        orientation = self._orientation(endpoints)
        if endpoints is None or orientation is None:
            return []

        detections = self._detect_triangles(
            dimension_line,
            geometries,
            endpoints,
            orientation,
        )
        detections.extend(
            self._detect_converging_lines(
                dimension_line,
                geometries,
                endpoints,
                orientation,
            )
        )
        return detections

    def _detect_triangles(
        self,
        dimension_line: GeometryEntity,
        geometries: Sequence[GeometryEntity],
        endpoints: tuple[Point, Point],
        orientation: str,
    ) -> list[ArrowDetection]:
        detections: list[ArrowDetection] = []
        for geometry in geometries:
            if not self._same_page(dimension_line, geometry):
                continue
            points = self._polygon_points(geometry)
            if len(points) != 3:
                continue

            width = max(point[0] for point in points) - min(point[0] for point in points)
            height = max(point[1] for point in points) - min(point[1] for point in points)
            if max(width, height) > self.max_arrow_size:
                continue

            center = (
                sum(point[0] for point in points) / 3,
                sum(point[1] for point in points) / 3,
            )
            endpoint_index, distance = self._nearest_endpoint(center, endpoints)
            if distance > self.endpoint_distance_threshold:
                continue

            detections.append(
                self._detection(
                    geometry_id=geometry.geometry_id,
                    direction=self._direction(orientation, endpoint_index),
                    confidence=0.91,
                    metadata={
                        "rule": "small_triangle_near_endpoint",
                        "endpoint_index": endpoint_index,
                        "endpoint_distance": distance,
                        "width": width,
                        "height": height,
                    },
                )
            )
        return detections

    def _detect_converging_lines(
        self,
        dimension_line: GeometryEntity,
        geometries: Sequence[GeometryEntity],
        endpoints: tuple[Point, Point],
        orientation: str,
    ) -> list[ArrowDetection]:
        detections: list[ArrowDetection] = []
        used_ids: set[str] = set()

        for endpoint_index, endpoint in enumerate(endpoints):
            candidates: list[tuple[GeometryEntity, tuple[Point, Point]]] = []
            for geometry in geometries:
                if (
                    geometry.geometry_id == dimension_line.geometry_id
                    or geometry.geometry_id in used_ids
                    or geometry.entity_type != "line"
                    or not self._same_page(dimension_line, geometry)
                ):
                    continue
                points = self._line_points(geometry)
                if points is None or self._line_length(points) > self.max_arrow_size:
                    continue
                if min(self._distance(point, endpoint) for point in points) <= 2.0:
                    candidates.append((geometry, points))

            for first, second in combinations(candidates, 2):
                if not self._lines_diverge(first[1], second[1], endpoint):
                    continue
                component_ids = [first[0].geometry_id, second[0].geometry_id]
                used_ids.update(component_ids)
                detections.append(
                    self._detection(
                        geometry_id=component_ids[0],
                        direction=self._direction(orientation, endpoint_index),
                        confidence=0.85,
                        metadata={
                            "rule": "converging_lines_near_endpoint",
                            "endpoint_index": endpoint_index,
                            "component_geometry_ids": component_ids,
                        },
                    )
                )
                break
        return detections

    def _detection(
        self,
        geometry_id: str,
        direction: str,
        confidence: float,
        metadata: dict[str, Any],
    ) -> ArrowDetection:
        return ArrowDetection(
            id=f"ARROW-{uuid4().hex}",
            geometry_id=geometry_id,
            type="dimension_arrow",
            direction=direction,
            confidence=confidence,
            metadata=metadata,
        )

    def _same_page(
        self,
        dimension_line: GeometryEntity,
        geometry: GeometryEntity,
    ) -> bool:
        return (
            geometry.document_id == dimension_line.document_id
            and geometry.page_number == dimension_line.page_number
        )

    def _polygon_points(self, geometry: GeometryEntity) -> list[Point]:
        if geometry.entity_type != "polygon":
            return []
        points = geometry.coordinates.get("points")
        if not isinstance(points, list):
            return []
        try:
            return [(float(point["x"]), float(point["y"])) for point in points]
        except (KeyError, TypeError, ValueError):
            return []

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

    def _orientation(self, points: tuple[Point, Point] | None) -> str | None:
        if points is None:
            return None
        delta_x = abs(points[1][0] - points[0][0])
        delta_y = abs(points[1][1] - points[0][1])
        if delta_x == 0 and delta_y == 0:
            return None
        return "horizontal" if delta_x >= delta_y else "vertical"

    def _nearest_endpoint(
        self,
        point: Point,
        endpoints: tuple[Point, Point],
    ) -> tuple[int, float]:
        distances = [self._distance(point, endpoint) for endpoint in endpoints]
        index = 0 if distances[0] <= distances[1] else 1
        return index, distances[index]

    def _direction(self, orientation: str, endpoint_index: int) -> str:
        if orientation == "horizontal":
            return "right" if endpoint_index == 0 else "left"
        return "down" if endpoint_index == 0 else "up"

    def _line_length(self, points: tuple[Point, Point]) -> float:
        return self._distance(points[0], points[1])

    def _distance(self, first: Point, second: Point) -> float:
        return hypot(first[0] - second[0], first[1] - second[1])

    def _lines_diverge(
        self,
        first: tuple[Point, Point],
        second: tuple[Point, Point],
        endpoint: Point,
    ) -> bool:
        first_far = max(first, key=lambda point: self._distance(point, endpoint))
        second_far = max(second, key=lambda point: self._distance(point, endpoint))
        first_vector = (first_far[0] - endpoint[0], first_far[1] - endpoint[1])
        second_vector = (second_far[0] - endpoint[0], second_far[1] - endpoint[1])
        cross_product = abs(
            first_vector[0] * second_vector[1]
            - first_vector[1] * second_vector[0]
        )
        return cross_product > 0.5
