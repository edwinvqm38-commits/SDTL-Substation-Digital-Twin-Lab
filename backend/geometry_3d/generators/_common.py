from __future__ import annotations

from math import isfinite
from typing import Any

from backend.geometry_3d.models import (
    Material3D,
    Mesh,
    Object3DComponent,
    Transform,
)


def validate_source(source: Any, expected_type: str) -> None:
    """Validate object type and proof of human approval before generation."""

    actual_type = getattr(source, "type", None) or getattr(source, "object_type", None)
    if actual_type != expected_type:
        raise ValueError(f"{expected_type} generator cannot process {actual_type}")

    state = getattr(source, "state", None)
    if state not in {"approved", "active", "modified"}:
        raise ValueError("3D generation requires an approved SDTL object")

    review = getattr(source, "review", None)
    if review is not None:
        approved = (
            review.get("approved", False)
            if isinstance(review, dict)
            else getattr(review, "approved", False)
        )
        if not approved:
            raise ValueError("3D generation requires explicit human approval")


def resolve_dimensions(source: Any) -> dict[str, float]:
    """Resolve named dimensions from v1.8 entities or legacy Core geometry."""

    result: dict[str, float] = {}
    _collect_dimensions(result, getattr(source, "dimensions", None))

    properties = getattr(source, "properties", {}) or {}
    if isinstance(properties, dict):
        _collect_dimensions(result, properties.get("dimensions"))
        for name in ("length", "width", "height", "depth"):
            if name in properties and name not in result:
                result[name] = _numeric_dimension(name, properties[name])

    geometry = getattr(source, "geometry", None)
    if geometry is not None:
        _collect_dimensions(result, getattr(geometry, "dimensions", None))
    return result


def require_dimensions(source: Any, names: tuple[str, ...]) -> dict[str, float]:
    dimensions = resolve_dimensions(source)
    missing = [name for name in names if name not in dimensions]
    if missing:
        raise ValueError(f"SDTL object is missing dimensions: {', '.join(missing)}")
    return dimensions


def source_transform(source: Any) -> Transform:
    properties = getattr(source, "properties", {}) or {}
    properties = properties if isinstance(properties, dict) else {}

    position = properties.get("position")
    spatial_position = getattr(source, "spatial_position", None)
    if position is None and spatial_position is not None:
        position = [spatial_position.x, spatial_position.y, spatial_position.z]
    geometry = getattr(source, "geometry", None)
    geometry_position = getattr(geometry, "position", None)
    if position is None and geometry_position is not None:
        position = [geometry_position.x, geometry_position.y, geometry_position.z]

    return Transform(
        position=position or [0.0, 0.0, 0.0],
        rotation=properties.get("rotation", [0.0, 0.0, 0.0]),
        scale=properties.get("scale", [1.0, 1.0, 1.0]),
    )


def source_traceability(source: Any) -> dict[str, Any]:
    return {
        "source_geometry": getattr(source, "source_geometry", None),
        "source_pdf": getattr(source, "source_pdf", None),
        "page": getattr(source, "page", None),
    }


def engineering_metadata(
    source: Any,
    dimensions: dict[str, float],
    material: str,
) -> dict[str, Any]:
    """Collect engineering metadata without placing it inside mesh topology."""

    properties = getattr(source, "properties", {}) or {}
    properties = properties if isinstance(properties, dict) else {}
    confidence = getattr(source, "confidence", None) or properties.get("confidence")
    if confidence is None:
        scores = properties.get("semantic_scores", {})
        confidence = scores.get("final") if isinstance(scores, dict) else None
    return {
        "dimensions": dimensions,
        "unit": "m",
        "material": material,
        "state": getattr(source, "state", None),
        "confidence": confidence,
    }


def plane_component(
    source_id: str,
    name: str,
    vertices: list[list[float]],
    normal: list[float],
    material: Material3D,
) -> Object3DComponent:
    slug = name.upper().replace(" ", "_")
    return Object3DComponent(
        id=f"CMP-{source_id}-{slug}",
        name=name,
        mesh=Mesh(
            id=f"MESH-{source_id}-{slug}",
            vertices=vertices,
            faces=[[0, 1, 2], [0, 2, 3]],
            normals=[normal.copy() for _ in vertices],
            metadata={"component_role": name},
        ),
        material=material,
    )


def box_component(
    source_id: str,
    name: str,
    length: float,
    width: float,
    height: float,
    material: Material3D,
) -> Object3DComponent:
    vertices = [
        [0.0, 0.0, 0.0],
        [length, 0.0, 0.0],
        [length, width, 0.0],
        [0.0, width, 0.0],
        [0.0, 0.0, height],
        [length, 0.0, height],
        [length, width, height],
        [0.0, width, height],
    ]
    faces = [
        [0, 2, 1], [0, 3, 2],
        [4, 5, 6], [4, 6, 7],
        [0, 1, 5], [0, 5, 4],
        [1, 2, 6], [1, 6, 5],
        [2, 3, 7], [2, 7, 6],
        [3, 0, 4], [3, 4, 7],
    ]
    slug = name.upper().replace(" ", "_")
    return Object3DComponent(
        id=f"CMP-{source_id}-{slug}",
        name=name,
        mesh=Mesh(
            id=f"MESH-{source_id}-{slug}",
            vertices=vertices,
            faces=faces,
            metadata={"component_role": name},
        ),
        material=material,
    )


def _collect_dimensions(target: dict[str, float], raw: Any) -> None:
    if raw is None:
        return
    if hasattr(raw, "model_dump"):
        raw = raw.model_dump()
    if isinstance(raw, dict):
        for name, value in raw.items():
            if name in {"length", "width", "height", "depth"}:
                target[name] = _numeric_dimension(name, value)
        return
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("dimension") or item.get("type")
            if name in {"length", "width", "height", "depth"} and "value" in item:
                target[name] = _numeric_dimension(name, item["value"])


def _numeric_dimension(name: str, raw: Any) -> float:
    if isinstance(raw, dict):
        raw = raw.get("value")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"Dimension {name} must be numeric")
    value = float(raw)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"Dimension {name} must be positive")
    return value
