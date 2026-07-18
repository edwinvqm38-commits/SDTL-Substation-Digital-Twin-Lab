from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import hypot
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ..dimension_entity import DimensionEntity
from ..geometry_entity import GeometryEntity
from ..text_geometry import ExtractedText


Point = tuple[float, float]


class GeometryFeature(BaseModel):
    """Calculated geometric characteristics derived from one validated geometry."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source_geometry: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeometryFeatureExtractor:
    """Convert validated geometry into deterministic shape and proximity features."""

    def __init__(self, proximity_threshold: float = 100.0) -> None:
        if proximity_threshold < 0:
            raise ValueError("proximity_threshold must be greater than or equal to zero")
        self.proximity_threshold = float(proximity_threshold)

    def extract_feature(
        self,
        geometry: GeometryEntity,
        texts: Sequence[ExtractedText] = (),
        dimensions: Sequence[DimensionEntity] = (),
    ) -> GeometryFeature:
        points = self._points(geometry)
        bounds = self._bounds(geometry, points)
        width = bounds[2] - bounds[0] if bounds is not None else 0.0
        height = bounds[3] - bounds[1] if bounds is not None else 0.0
        length = max(width, height)
        short_width = min(width, height)
        closed = geometry.entity_type in {"rectangle", "polygon"} or bool(
            geometry.properties.get("close_path")
        )

        if geometry.entity_type == "rectangle":
            area = width * height
            perimeter = 2 * (width + height)
        elif geometry.entity_type == "polygon" and len(points) >= 3:
            area = self._polygon_area(points)
            perimeter = self._polygon_perimeter(points, closed=True)
        elif geometry.entity_type == "line" and len(points) == 2:
            area = 0.0
            perimeter = 0.0
            length = self._distance(points[0], points[1])
            short_width = 0.0
        else:
            area = width * height if closed else 0.0
            perimeter = 2 * (width + height) if closed else 0.0

        center = self._center(bounds)
        text_distances = [
            self._distance(center, self._text_center(text))
            for text in texts
            if center is not None
            and text.document_id == geometry.document_id
            and text.page_number == geometry.page_number
        ]
        dimension_distances = [
            distance
            for dimension in dimensions
            if dimension.document_id == geometry.document_id
            and dimension.page_number == geometry.page_number
            and (
                distance := self._dimension_distance(dimension, geometry, center)
            )
            is not None
        ]

        properties: dict[str, Any] = {
            "closed": closed,
            "area": area,
            "perimeter": perimeter,
            "width": short_width,
            "length": length,
            "aspect_ratio": (
                length / short_width if short_width > 0 else None
            ),
            "orientation": (
                None
                if bounds is None
                else "horizontal"
                if width >= height
                else "vertical"
            ),
            "bounds": self._bounds_dict(bounds),
            "unit": geometry.properties.get("unit"),
            "nearby_text_count": sum(
                distance <= self.proximity_threshold for distance in text_distances
            ),
            "nearest_text_distance": min(text_distances) if text_distances else None,
            "nearby_dimension_count": sum(
                distance <= self.proximity_threshold
                for distance in dimension_distances
            ),
            "nearest_dimension_distance": (
                min(dimension_distances) if dimension_distances else None
            ),
        }

        return GeometryFeature(
            id=f"GF-{uuid4().hex}",
            source_geometry=geometry.geometry_id,
            type=geometry.entity_type,
            properties=properties,
            metadata={
                "document_id": geometry.document_id,
                "page_number": geometry.page_number,
                "source_confidence": geometry.confidence,
                "proximity_threshold": self.proximity_threshold,
            },
        )

    def extract_features(
        self,
        geometries: Sequence[GeometryEntity],
        texts: Sequence[ExtractedText] = (),
        dimensions: Sequence[DimensionEntity] = (),
    ) -> list[GeometryFeature]:
        return [
            self.extract_feature(geometry, texts=texts, dimensions=dimensions)
            for geometry in geometries
        ]

    def _points(self, geometry: GeometryEntity) -> list[Point]:
        coordinates = geometry.coordinates
        start = coordinates.get("start")
        end = coordinates.get("end")
        if isinstance(start, Mapping) and isinstance(end, Mapping):
            try:
                return [
                    (float(start["x"]), float(start["y"])),
                    (float(end["x"]), float(end["y"])),
                ]
            except (KeyError, TypeError, ValueError):
                return []

        points = coordinates.get("points")
        if isinstance(points, list):
            try:
                return [
                    (float(point["x"]), float(point["y"])) for point in points
                ]
            except (KeyError, TypeError, ValueError):
                return []
        return []

    def _bounds(
        self,
        geometry: GeometryEntity,
        points: list[Point],
    ) -> tuple[float, float, float, float] | None:
        values = geometry.coordinates.get("bounding_box", geometry.coordinates)
        if isinstance(values, Mapping):
            try:
                x0 = float(values["x"])
                y0 = float(values["y"])
                if "x1" in values and "y1" in values:
                    x1, y1 = float(values["x1"]), float(values["y1"])
                elif "width" in values and "height" in values:
                    x1 = x0 + float(values["width"])
                    y1 = y0 + float(values["height"])
                else:
                    raise KeyError
                return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
            except (KeyError, TypeError, ValueError):
                pass

        if points:
            return (
                min(point[0] for point in points),
                min(point[1] for point in points),
                max(point[0] for point in points),
                max(point[1] for point in points),
            )
        return None

    def _center(
        self,
        bounds: tuple[float, float, float, float] | None,
    ) -> Point | None:
        if bounds is None:
            return None
        return (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2

    def _text_center(self, text: ExtractedText) -> Point:
        return text.x + text.width / 2, text.y + text.height / 2

    def _dimension_distance(
        self,
        dimension: DimensionEntity,
        geometry: GeometryEntity,
        geometry_center: Point | None,
    ) -> float | None:
        if dimension.geometry_reference_id == geometry.geometry_id:
            return 0.0
        bbox = dimension.metadata.get("text_bbox")
        if not isinstance(bbox, Mapping) or geometry_center is None:
            return None
        try:
            center = (
                float(bbox["x"]) + float(bbox["width"]) / 2,
                float(bbox["y"]) + float(bbox["height"]) / 2,
            )
        except (KeyError, TypeError, ValueError):
            return None
        return self._distance(geometry_center, center)

    def _polygon_area(self, points: list[Point]) -> float:
        return abs(
            sum(
                first[0] * second[1] - second[0] * first[1]
                for first, second in zip(points, points[1:] + points[:1])
            )
        ) / 2

    def _polygon_perimeter(self, points: list[Point], closed: bool) -> float:
        pairs = list(zip(points, points[1:]))
        if closed:
            pairs.append((points[-1], points[0]))
        return sum(self._distance(first, second) for first, second in pairs)

    def _distance(self, first: Point | None, second: Point) -> float:
        if first is None:
            return float("inf")
        return hypot(first[0] - second[0], first[1] - second[1])

    def _bounds_dict(
        self,
        bounds: tuple[float, float, float, float] | None,
    ) -> dict[str, float] | None:
        if bounds is None:
            return None
        return {
            "x": bounds[0],
            "y": bounds[1],
            "x1": bounds[2],
            "y1": bounds[3],
            "width": bounds[2] - bounds[0],
            "height": bounds[3] - bounds[1],
        }
