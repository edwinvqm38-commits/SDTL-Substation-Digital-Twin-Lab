from __future__ import annotations

from math import dist, pi
from typing import Any, Callable

from ezdxf.entities import DXFEntity
from shapely.geometry import LineString

from .cad_metadata import CADEntity


class CADEntityMapper:
    """Map native ezdxf entities without changing coordinates or units."""

    SUPPORTED_TYPES = frozenset(
        {
            "LINE",
            "LWPOLYLINE",
            "POLYLINE",
            "ARC",
            "CIRCLE",
            "TEXT",
            "MTEXT",
            "INSERT",
        }
    )

    def __init__(self) -> None:
        self._mappers: dict[str, Callable[[DXFEntity], tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]] = {
            "LINE": self._map_line,
            "LWPOLYLINE": self._map_lwpolyline,
            "POLYLINE": self._map_polyline,
            "ARC": self._map_arc,
            "CIRCLE": self._map_circle,
            "TEXT": self._map_text,
            "MTEXT": self._map_mtext,
            "INSERT": self._map_insert,
        }

    def map_entity(
        self,
        entity: DXFEntity,
        document_id: str,
        entity_index: int | None = None,
    ) -> CADEntity:
        """Return a supported mapping or a generic traceable entity."""

        entity_type = entity.dxftype()
        handle = self._dxf_value(entity, "handle")
        fallback = f"INDEX-{entity_index}" if entity_index is not None else "NO-HANDLE"
        entity_id = f"{document_id}:{handle or fallback}"
        layer = str(self._dxf_value(entity, "layer", "0"))
        common_properties = self._graphic_properties(entity)
        common_attributes = {
            "handle": handle,
            "owner_handle": self._dxf_value(entity, "owner"),
            "modelspace_index": entity_index,
            "dxf_attributes": self._serialize(entity.dxfattribs()),
        }

        mapper = self._mappers.get(entity_type)
        if mapper is None:
            properties = {
                **common_properties,
                "dxf_attributes": self._serialize(entity.dxfattribs()),
            }
            return CADEntity(
                entity_id=entity_id,
                entity_type=entity_type,
                layer=layer,
                properties=self._without_none(properties),
                attributes=self._without_none(common_attributes),
                mapping_status="unsupported",
            )

        coordinates, properties, attributes = mapper(entity)
        return CADEntity(
            entity_id=entity_id,
            entity_type=entity_type,
            layer=layer,
            coordinates=coordinates,
            properties=self._without_none({**common_properties, **properties}),
            attributes=self._without_none({**common_attributes, **attributes}),
        )

    def _map_line(
        self, entity: DXFEntity
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        start = self._point(entity.dxf.start)
        end = self._point(entity.dxf.end)
        derived = self._linear_properties([start, end])
        derived["length_3d"] = dist(self._point_values(start), self._point_values(end))
        return {"start": start, "end": end}, derived, {}

    def _map_lwpolyline(
        self, entity: DXFEntity
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        elevation = float(entity.dxf.get("elevation", 0.0))
        points = [
            {
                "x": float(x),
                "y": float(y),
                "z": elevation,
                "start_width": float(start_width),
                "end_width": float(end_width),
                "bulge": float(bulge),
            }
            for x, y, start_width, end_width, bulge in entity.get_points("xyseb")
        ]
        properties: dict[str, Any] = {
            "closed": bool(entity.closed),
            "elevation": elevation,
            "constant_width": float(entity.dxf.get("const_width", 0.0)),
            "vertex_count": len(points),
        }
        if points and all(point["bulge"] == 0.0 for point in points):
            properties.update(self._linear_properties(points, closed=bool(entity.closed)))
        return {"points": points}, properties, {}

    def _map_polyline(
        self, entity: DXFEntity
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        points = [
            {
                **self._point(vertex.dxf.location),
                "start_width": float(vertex.dxf.get("vtx0", 0.0)),
                "end_width": float(vertex.dxf.get("vtx1", 0.0)),
                "bulge": float(vertex.dxf.get("bulge", 0.0)),
                "flags": int(vertex.dxf.get("flags", 0)),
            }
            for vertex in entity.vertices
        ]
        properties: dict[str, Any] = {
            "closed": bool(entity.is_closed),
            "flags": int(entity.dxf.get("flags", 0)),
            "vertex_count": len(points),
            "is_2d_polyline": bool(entity.is_2d_polyline),
            "is_3d_polyline": bool(entity.is_3d_polyline),
            "is_polygon_mesh": bool(entity.is_polygon_mesh),
            "is_poly_face_mesh": bool(entity.is_poly_face_mesh),
            "m_count": int(entity.dxf.get("m_count", 0)),
            "n_count": int(entity.dxf.get("n_count", 0)),
            "smooth_type": int(entity.dxf.get("smooth_type", 0)),
        }
        if points and all(point["bulge"] == 0.0 for point in points):
            properties.update(self._linear_properties(points, closed=bool(entity.is_closed)))
        return {"points": points}, properties, {}

    def _map_arc(
        self, entity: DXFEntity
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        return (
            {"center": self._point(entity.dxf.center)},
            {
                "radius": float(entity.dxf.radius),
                "start_angle": float(entity.dxf.start_angle),
                "end_angle": float(entity.dxf.end_angle),
                "extrusion": self._point(entity.dxf.get("extrusion", (0, 0, 1))),
            },
            {},
        )

    def _map_circle(
        self, entity: DXFEntity
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        radius = float(entity.dxf.radius)
        return (
            {"center": self._point(entity.dxf.center)},
            {
                "radius": radius,
                "circumference": 2 * pi * radius,
                "area": pi * radius * radius,
                "extrusion": self._point(entity.dxf.get("extrusion", (0, 0, 1))),
            },
            {},
        )

    def _map_text(
        self, entity: DXFEntity
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        coordinates = {"insert": self._point(entity.dxf.insert)}
        align_point = self._dxf_value(entity, "align_point")
        if align_point is not None:
            coordinates["align_point"] = self._point(align_point)
        properties = {
            "height": float(entity.dxf.height),
            "rotation": float(entity.dxf.get("rotation", 0.0)),
            "width_factor": float(entity.dxf.get("width", 1.0)),
            "oblique": float(entity.dxf.get("oblique", 0.0)),
            "style": entity.dxf.get("style", "Standard"),
            "horizontal_alignment": int(entity.dxf.get("halign", 0)),
            "vertical_alignment": int(entity.dxf.get("valign", 0)),
        }
        return coordinates, properties, {"text": entity.dxf.text}

    def _map_mtext(
        self, entity: DXFEntity
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        coordinates = {
            "insert": self._point(entity.dxf.insert),
            "text_direction": self._point(entity.dxf.get("text_direction", (1, 0, 0))),
        }
        properties = {
            "character_height": float(entity.dxf.char_height),
            "width": float(entity.dxf.get("width", 0.0)),
            "defined_height": float(entity.dxf.get("defined_height", 0.0)),
            "attachment_point": int(entity.dxf.get("attachment_point", 1)),
            "flow_direction": int(entity.dxf.get("flow_direction", 1)),
            "style": entity.dxf.get("style", "Standard"),
            "rotation": float(entity.dxf.get("rotation", 0.0)),
            "line_spacing_style": int(entity.dxf.get("line_spacing_style", 1)),
            "line_spacing_factor": float(entity.dxf.get("line_spacing_factor", 1.0)),
        }
        return coordinates, properties, {
            "text": entity.plain_text(),
            "raw_text": entity.text,
        }

    def _map_insert(
        self, entity: DXFEntity
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        attached_attributes = [
            self._without_none(
                {
                    "tag": attribute.dxf.tag,
                    "text": attribute.dxf.text,
                    "handle": self._dxf_value(attribute, "handle"),
                    "layer": self._dxf_value(attribute, "layer"),
                    "insert": self._point(attribute.dxf.insert),
                    "height": self._dxf_value(attribute, "height"),
                    "style": self._dxf_value(attribute, "style"),
                }
            )
            for attribute in entity.attribs
        ]
        properties = {
            "block_name": entity.dxf.name,
            "x_scale": float(entity.dxf.get("xscale", 1.0)),
            "y_scale": float(entity.dxf.get("yscale", 1.0)),
            "z_scale": float(entity.dxf.get("zscale", 1.0)),
            "rotation": float(entity.dxf.get("rotation", 0.0)),
            "column_count": int(entity.dxf.get("column_count", 1)),
            "row_count": int(entity.dxf.get("row_count", 1)),
            "column_spacing": float(entity.dxf.get("column_spacing", 0.0)),
            "row_spacing": float(entity.dxf.get("row_spacing", 0.0)),
        }
        return {"insert": self._point(entity.dxf.insert)}, properties, {
            "attached_attributes": attached_attributes
        }

    def _graphic_properties(self, entity: DXFEntity) -> dict[str, Any]:
        return self._without_none(
            {
                "color_index": self._dxf_value(entity, "color", 256),
                "true_color": self._dxf_value(entity, "true_color"),
                "linetype": self._dxf_value(entity, "linetype", "BYLAYER"),
                "lineweight": self._dxf_value(entity, "lineweight", -1),
                "linetype_scale": self._dxf_value(entity, "ltscale", 1.0),
                "transparency": self._dxf_value(entity, "transparency"),
                "invisible": self._dxf_value(entity, "invisible", 0),
            }
        )

    def _linear_properties(
        self, points: list[dict[str, Any]], closed: bool = False
    ) -> dict[str, Any]:
        xy_points = [(float(point["x"]), float(point["y"])) for point in points]
        if closed and len(xy_points) > 2 and xy_points[0] != xy_points[-1]:
            xy_points.append(xy_points[0])
        if len(xy_points) < 2:
            return {}
        geometry = LineString(xy_points)
        return {
            "planar_length": float(geometry.length),
            "bounds": [float(value) for value in geometry.bounds],
        }

    @staticmethod
    def _point(value: Any) -> dict[str, float]:
        if hasattr(value, "x") and hasattr(value, "y"):
            return {
                "x": float(value.x),
                "y": float(value.y),
                "z": float(getattr(value, "z", 0.0)),
            }
        values = list(value)
        return {
            "x": float(values[0]),
            "y": float(values[1]),
            "z": float(values[2]) if len(values) > 2 else 0.0,
        }

    @staticmethod
    def _point_values(point: dict[str, float]) -> tuple[float, float, float]:
        return point["x"], point["y"], point["z"]

    @staticmethod
    def _dxf_value(entity: DXFEntity, name: str, default: Any = None) -> Any:
        try:
            return entity.dxf.get(name, default)
        except (AttributeError, ValueError):
            return default

    def _serialize(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if hasattr(value, "x") and hasattr(value, "y"):
            return self._point(value)
        if isinstance(value, dict):
            return {str(key): self._serialize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._serialize(item) for item in value]
        return str(value)

    @staticmethod
    def _without_none(values: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in values.items() if value is not None}
