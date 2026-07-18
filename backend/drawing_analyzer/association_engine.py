from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import hypot
from typing import Any
from uuid import uuid4

from .geometry_entity import GeometryEntity
from .spatial_relation import SpatialRelation
from .text_geometry import ExtractedText


BoundingBox = tuple[float, float, float, float]


class SpatialAssociationEngine:
    """Associate text and vector geometry using transparent bounding-box rules."""

    def __init__(self, distance_threshold: float = 100.0) -> None:
        if distance_threshold < 0:
            raise ValueError("distance_threshold must be greater than or equal to zero")
        self.distance_threshold = float(distance_threshold)

    def associate(
        self,
        texts: Sequence[ExtractedText],
        geometries: Sequence[GeometryEntity],
    ) -> list[SpatialRelation]:
        relations: list[SpatialRelation] = []

        for text in texts:
            text_bbox = self._text_bbox(text)
            for geometry in geometries:
                if (
                    text.document_id != geometry.document_id
                    or text.page_number != geometry.page_number
                ):
                    continue

                geometry_bbox = self._geometry_bbox(geometry)
                if geometry_bbox is None:
                    continue

                relation = self._associate_pair(
                    text=text,
                    geometry=geometry,
                    text_bbox=text_bbox,
                    geometry_bbox=geometry_bbox,
                )
                if relation is not None:
                    relations.append(relation)

        return relations

    def _associate_pair(
        self,
        text: ExtractedText,
        geometry: GeometryEntity,
        text_bbox: BoundingBox,
        geometry_bbox: BoundingBox,
    ) -> SpatialRelation | None:
        text_center = self._center(text_bbox)
        geometry_center = self._center(geometry_bbox)
        distance = hypot(
            text_center[0] - geometry_center[0],
            text_center[1] - geometry_center[1],
        )
        overlap_ratio = self._overlap_ratio(text_bbox, geometry_bbox)

        if self._contains_point(geometry_bbox, text_center):
            relation_type = "inside"
            confidence = 0.95
        elif self._intersects(text_bbox, geometry_bbox):
            relation_type = "intersects"
            confidence = 0.85
        elif distance < self.distance_threshold:
            relation_type = "near"
            confidence = 0.80
            overlap_ratio = None
        else:
            return None

        return SpatialRelation(
            relation_id=f"SPR-{uuid4().hex}",
            text_id=text.text_id,
            geometry_id=geometry.geometry_id,
            relation_type=relation_type,
            distance=distance,
            overlap_ratio=overlap_ratio,
            confidence=confidence,
            metadata={
                "document_id": text.document_id,
                "page_number": text.page_number,
                "distance_threshold": self.distance_threshold,
                "text_bbox": self._bbox_dict(text_bbox),
                "geometry_bbox": self._bbox_dict(geometry_bbox),
            },
        )

    def _text_bbox(self, text: ExtractedText) -> BoundingBox:
        return self._normalize_bbox(
            text.x,
            text.y,
            text.x + text.width,
            text.y + text.height,
        )

    def _geometry_bbox(self, geometry: GeometryEntity) -> BoundingBox | None:
        coordinates = geometry.coordinates

        nested_bbox = coordinates.get("bounding_box")
        if isinstance(nested_bbox, Mapping):
            bbox = self._bbox_from_mapping(nested_bbox)
            if bbox is not None:
                return bbox

        bbox = self._bbox_from_mapping(coordinates)
        if bbox is not None:
            return bbox

        start = coordinates.get("start")
        end = coordinates.get("end")
        if isinstance(start, Mapping) and isinstance(end, Mapping):
            try:
                return self._normalize_bbox(
                    float(start["x"]),
                    float(start["y"]),
                    float(end["x"]),
                    float(end["y"]),
                )
            except (KeyError, TypeError, ValueError):
                return None

        points = coordinates.get("points")
        if isinstance(points, list) and points:
            try:
                x_values = [float(point["x"]) for point in points]
                y_values = [float(point["y"]) for point in points]
            except (KeyError, TypeError, ValueError):
                return None
            return self._normalize_bbox(
                min(x_values),
                min(y_values),
                max(x_values),
                max(y_values),
            )

        return None

    def _bbox_from_mapping(
        self,
        values: Mapping[str, Any],
    ) -> BoundingBox | None:
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
        return self._normalize_bbox(x0, y0, x1, y1)

    def _normalize_bbox(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ) -> BoundingBox:
        return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

    def _center(self, bbox: BoundingBox) -> tuple[float, float]:
        x0, y0, x1, y1 = bbox
        return (x0 + x1) / 2, (y0 + y1) / 2

    def _contains_point(
        self,
        bbox: BoundingBox,
        point: tuple[float, float],
    ) -> bool:
        x0, y0, x1, y1 = bbox
        return x0 <= point[0] <= x1 and y0 <= point[1] <= y1

    def _intersects(self, first: BoundingBox, second: BoundingBox) -> bool:
        return not (
            first[2] < second[0]
            or first[0] > second[2]
            or first[3] < second[1]
            or first[1] > second[3]
        )

    def _overlap_ratio(
        self,
        text_bbox: BoundingBox,
        geometry_bbox: BoundingBox,
    ) -> float | None:
        text_area = (text_bbox[2] - text_bbox[0]) * (
            text_bbox[3] - text_bbox[1]
        )
        if text_area <= 0:
            return None

        overlap_width = max(
            0.0,
            min(text_bbox[2], geometry_bbox[2])
            - max(text_bbox[0], geometry_bbox[0]),
        )
        overlap_height = max(
            0.0,
            min(text_bbox[3], geometry_bbox[3])
            - max(text_bbox[1], geometry_bbox[1]),
        )
        return (overlap_width * overlap_height) / text_area

    def _bbox_dict(self, bbox: BoundingBox) -> dict[str, float]:
        x0, y0, x1, y1 = bbox
        return {
            "x": x0,
            "y": y0,
            "x1": x1,
            "y1": y1,
            "width": x1 - x0,
            "height": y1 - y0,
        }
