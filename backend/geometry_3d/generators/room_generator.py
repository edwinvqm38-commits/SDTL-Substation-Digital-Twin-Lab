from __future__ import annotations

from typing import Any

from backend.geometry_3d.models import Object3D, load_material

from ._common import (
    engineering_metadata,
    plane_component,
    require_dimensions,
    source_traceability,
    source_transform,
    validate_source,
)


class RoomGenerator:
    """Generate a semantic room envelope from an approved ElectricalRoom."""

    def generate(self, source: Any) -> Object3D:
        validate_source(source, "ElectricalRoom")
        dimensions = require_dimensions(source, ("length", "width", "height"))
        length = dimensions["length"]
        width = dimensions["width"]
        height = dimensions["height"]
        material = load_material("concrete")
        source_id = str(source.id)

        components = [
            plane_component(
                source_id,
                "Floor",
                [[0, 0, 0], [length, 0, 0], [length, width, 0], [0, width, 0]],
                [0, 0, 1],
                material,
            ),
            plane_component(
                source_id,
                "Wall_1",
                [[0, 0, 0], [length, 0, 0], [length, 0, height], [0, 0, height]],
                [0, -1, 0],
                material,
            ),
            plane_component(
                source_id,
                "Wall_2",
                [
                    [length, 0, 0],
                    [length, width, 0],
                    [length, width, height],
                    [length, 0, height],
                ],
                [1, 0, 0],
                material,
            ),
            plane_component(
                source_id,
                "Wall_3",
                [
                    [length, width, 0],
                    [0, width, 0],
                    [0, width, height],
                    [length, width, height],
                ],
                [0, 1, 0],
                material,
            ),
            plane_component(
                source_id,
                "Wall_4",
                [[0, width, 0], [0, 0, 0], [0, 0, height], [0, width, height]],
                [-1, 0, 0],
                material,
            ),
            plane_component(
                source_id,
                "Roof",
                [
                    [0, 0, height],
                    [length, 0, height],
                    [length, width, height],
                    [0, width, height],
                ],
                [0, 0, 1],
                material,
            ),
        ]
        return Object3D(
            id=f"3D-{source_id}",
            type="ElectricalRoom",
            components=components,
            source_sdtl_object=source_id,
            transform=source_transform(source),
            traceability=source_traceability(source),
            metadata={
                "generator": self.__class__.__name__,
                "coordinate_system": "right-handed-z-up",
                **engineering_metadata(source, dimensions, material.name),
            },
        )
