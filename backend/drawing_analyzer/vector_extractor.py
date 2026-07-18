from __future__ import annotations

from math import hypot
from pathlib import Path
from typing import Any
from uuid import uuid4

import fitz

from .geometry_entity import GeometryEntity


class VectorGeometryExtractor:
    """Extract native PDF vector paths without applying engineering semantics."""

    def extract_geometry(
        self,
        path: str | Path,
        document_id: str | None = None,
    ) -> list[GeometryEntity]:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"PDF document not found: {source}")

        try:
            document = fitz.open(source)
        except (fitz.FileDataError, RuntimeError) as exc:
            raise ValueError(f"Unable to open PDF document: {source}") from exc

        resolved_document_id = document_id if document_id is not None else source.stem

        with document:
            if not document.is_pdf:
                raise ValueError(f"Document is not a PDF file: {source}")
            if document.needs_pass:
                raise ValueError(f"PDF document requires a password: {source}")

            entities: list[GeometryEntity] = []
            for page_number, page in enumerate(document, start=1):
                for path_index, drawing in enumerate(page.get_drawings()):
                    entities.extend(
                        self._extract_drawing(
                            drawing=drawing,
                            path_index=path_index,
                            document_id=resolved_document_id,
                            page_number=page_number,
                        )
                    )
            return entities

    def _extract_drawing(
        self,
        drawing: dict[str, Any],
        path_index: int,
        document_id: str,
        page_number: int,
    ) -> list[GeometryEntity]:
        items = drawing.get("items", [])
        properties = self._drawing_properties(drawing, path_index)

        if self._is_closed_polygon(items, drawing):
            points = [self._point(items[0][1])]
            points.extend(self._point(item[2]) for item in items)
            if points[-1] == points[0]:
                points.pop()
            return [
                self._entity(
                    document_id,
                    page_number,
                    "polygon",
                    {
                        "points": points,
                        "bounding_box": self._points_bbox(points),
                    },
                    properties,
                )
            ]

        entities: list[GeometryEntity] = []
        for item in items:
            operation = item[0]

            if operation == "l" and len(item) >= 3:
                start = self._point(item[1])
                end = self._point(item[2])
                coordinates = {
                    "start": start,
                    "end": end,
                    "length": hypot(end["x"] - start["x"], end["y"] - start["y"]),
                }
                entity_type = "line"
            elif operation == "re" and len(item) >= 2:
                coordinates = self._rectangle(item[1])
                entity_type = "rectangle"
            elif operation == "qu" and len(item) >= 2:
                points = self._quad_points(item[1])
                coordinates = {
                    "points": points,
                    "bounding_box": self._points_bbox(points),
                }
                entity_type = "polygon"
            elif operation == "c" and len(item) >= 5:
                points = [self._point(value) for value in item[1:5]]
                coordinates = {
                    "start": points[0],
                    "control_1": points[1],
                    "control_2": points[2],
                    "end": points[3],
                    "bounding_box": self._points_bbox(points),
                }
                entity_type = "curve"
            else:
                coordinates = {
                    "operation": str(operation),
                    "values": [self._serialize_value(value) for value in item[1:]],
                }
                entity_type = "unknown"

            item_properties = dict(properties)
            item_properties["operation"] = str(operation)
            if operation == "re" and len(item) >= 3:
                item_properties["orientation"] = item[2]

            entities.append(
                self._entity(
                    document_id,
                    page_number,
                    entity_type,
                    coordinates,
                    item_properties,
                )
            )

        return entities

    def _entity(
        self,
        document_id: str,
        page_number: int,
        entity_type: str,
        coordinates: dict[str, Any],
        properties: dict[str, Any],
    ) -> GeometryEntity:
        return GeometryEntity(
            geometry_id=f"GEO-{uuid4().hex}",
            document_id=document_id,
            page_number=page_number,
            entity_type=entity_type,
            coordinates=coordinates,
            properties=properties,
            confidence=1.0,
        )

    def _drawing_properties(
        self,
        drawing: dict[str, Any],
        path_index: int,
    ) -> dict[str, Any]:
        properties: dict[str, Any] = {
            "path_index": path_index,
            "drawing_type": drawing.get("type"),
            "line_width": drawing.get("width"),
            "stroke_color": self._color(drawing.get("color")),
            "fill_color": self._color(drawing.get("fill")),
            "stroke_opacity": drawing.get("stroke_opacity"),
            "fill_opacity": drawing.get("fill_opacity"),
            "close_path": drawing.get("closePath"),
            "dashes": drawing.get("dashes"),
            "line_cap": self._serialize_value(drawing.get("lineCap")),
            "line_join": drawing.get("lineJoin"),
            "layer": drawing.get("layer"),
            "sequence_number": drawing.get("seqno"),
        }
        return {key: value for key, value in properties.items() if value is not None}

    def _is_closed_polygon(
        self,
        items: list[tuple[Any, ...]],
        drawing: dict[str, Any],
    ) -> bool:
        return (
            bool(drawing.get("closePath"))
            and len(items) >= 3
            and all(item and item[0] == "l" for item in items)
        )

    def _point(self, value: Any) -> dict[str, float]:
        return {"x": float(value.x), "y": float(value.y)}

    def _rectangle(self, value: Any) -> dict[str, float]:
        rectangle = fitz.Rect(value)
        return {
            "x": float(rectangle.x0),
            "y": float(rectangle.y0),
            "x1": float(rectangle.x1),
            "y1": float(rectangle.y1),
            "width": float(rectangle.width),
            "height": float(rectangle.height),
        }

    def _quad_points(self, value: Any) -> list[dict[str, float]]:
        quad = fitz.Quad(value)
        return [
            self._point(quad.ul),
            self._point(quad.ur),
            self._point(quad.lr),
            self._point(quad.ll),
        ]

    def _points_bbox(
        self,
        points: list[dict[str, float]],
    ) -> dict[str, float]:
        x_values = [point["x"] for point in points]
        y_values = [point["y"] for point in points]
        x0, x1 = min(x_values), max(x_values)
        y0, y1 = min(y_values), max(y_values)
        return {
            "x": x0,
            "y": y0,
            "x1": x1,
            "y1": y1,
            "width": x1 - x0,
            "height": y1 - y0,
        }

    def _color(self, value: Any) -> list[float] | None:
        if not isinstance(value, (list, tuple)):
            return None
        return [float(component) for component in value]

    def _serialize_value(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, fitz.Point):
            return self._point(value)
        if isinstance(value, fitz.Rect):
            return self._rectangle(value)
        if isinstance(value, (list, tuple)):
            return [self._serialize_value(item) for item in value]
        return str(value)
