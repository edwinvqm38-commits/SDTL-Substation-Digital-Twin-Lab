from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import hypot
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ..geometry_entity import GeometryEntity
from ..text_geometry import ExtractedText


BoundingBox = tuple[float, float, float, float]


class TextGeometryRelation(BaseModel):
    """Deterministic proximity and containment relation between text and geometry."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text_id: str
    text: str
    geometry_id: str
    distance: float
    contained: bool
    alignment: str
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class TextGeometryRelationEngine:
    """Relate located text to geometry using centers, containment, and alignment."""

    def __init__(self, distance_threshold: float = 100.0) -> None:
        if distance_threshold <= 0:
            raise ValueError("distance_threshold must be greater than zero")
        self.distance_threshold = float(distance_threshold)

    def relate(
        self,
        texts: Sequence[ExtractedText],
        geometries: Sequence[GeometryEntity],
    ) -> list[TextGeometryRelation]:
        relations: list[TextGeometryRelation] = []
        for text in texts:
            text_center = (text.x + text.width / 2, text.y + text.height / 2)
            for geometry in geometries:
                if (
                    text.document_id != geometry.document_id
                    or text.page_number != geometry.page_number
                ):
                    continue
                bounds = self._geometry_bounds(geometry)
                if bounds is None:
                    continue
                geometry_center = (
                    (bounds[0] + bounds[2]) / 2,
                    (bounds[1] + bounds[3]) / 2,
                )
                distance = hypot(
                    text_center[0] - geometry_center[0],
                    text_center[1] - geometry_center[1],
                )
                contained = (
                    bounds[0] <= text_center[0] <= bounds[2]
                    and bounds[1] <= text_center[1] <= bounds[3]
                )
                if not contained and distance > self.distance_threshold:
                    continue

                delta_x = abs(text_center[0] - geometry_center[0])
                delta_y = abs(text_center[1] - geometry_center[1])
                alignment = (
                    "centered"
                    if delta_x <= 1.0 and delta_y <= 1.0
                    else "horizontal"
                    if delta_x >= delta_y
                    else "vertical"
                )
                confidence = (
                    0.95
                    if contained
                    else max(
                        0.60,
                        0.90 - 0.30 * (distance / self.distance_threshold),
                    )
                )
                relations.append(
                    TextGeometryRelation(
                        id=f"TGR-{uuid4().hex}",
                        text_id=text.text_id,
                        text=text.content,
                        geometry_id=geometry.geometry_id,
                        distance=distance,
                        contained=contained,
                        alignment=alignment,
                        confidence=round(confidence, 4),
                        metadata={
                            "document_id": text.document_id,
                            "page_number": text.page_number,
                            "text_center": list(text_center),
                            "geometry_center": list(geometry_center),
                            "distance_threshold": self.distance_threshold,
                        },
                    )
                )
        return relations

    def _geometry_bounds(self, geometry: GeometryEntity) -> BoundingBox | None:
        values = geometry.coordinates.get("bounding_box", geometry.coordinates)
        if isinstance(values, Mapping):
            try:
                x0, y0 = float(values["x"]), float(values["y"])
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

        start, end = geometry.coordinates.get("start"), geometry.coordinates.get("end")
        if isinstance(start, Mapping) and isinstance(end, Mapping):
            try:
                return (
                    min(float(start["x"]), float(end["x"])),
                    min(float(start["y"]), float(end["y"])),
                    max(float(start["x"]), float(end["x"])),
                    max(float(start["y"]), float(end["y"])),
                )
            except (KeyError, TypeError, ValueError):
                return None
        return None
