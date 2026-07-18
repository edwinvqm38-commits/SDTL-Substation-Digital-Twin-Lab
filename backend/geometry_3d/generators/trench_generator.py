from __future__ import annotations

from typing import Any

from backend.geometry_3d.models import Object3D, load_material

from ._common import (
    engineering_metadata,
    plane_component,
    resolve_dimensions,
    source_traceability,
    source_transform,
    validate_source,
)


class CableTrenchGenerator:
    """Generate an open concrete channel from an approved CableTrench object."""

    def generate(self, source: Any) -> Object3D:
        validate_source(source, "CableTrench")
        dimensions = resolve_dimensions(source)
        missing = [name for name in ("length", "width") if name not in dimensions]
        depth = dimensions.get("depth", dimensions.get("height"))
        if depth is None:
            missing.append("depth")
        if missing:
            raise ValueError(f"SDTL object is missing dimensions: {', '.join(missing)}")

        length = dimensions["length"]
        width = dimensions["width"]
        dimensions["depth"] = depth
        material = load_material("concrete")
        source_id = str(source.id)
        components = [
            plane_component(
                source_id,
                "Channel_Base",
                [[0, 0, 0], [length, 0, 0], [length, width, 0], [0, width, 0]],
                [0, 0, 1],
                material,
            ),
            plane_component(
                source_id,
                "Side_Wall_Left",
                [[0, 0, 0], [length, 0, 0], [length, 0, depth], [0, 0, depth]],
                [0, 1, 0],
                material,
            ),
            plane_component(
                source_id,
                "Side_Wall_Right",
                [
                    [length, width, 0],
                    [0, width, 0],
                    [0, width, depth],
                    [length, width, depth],
                ],
                [0, -1, 0],
                material,
            ),
        ]
        return Object3D(
            id=f"3D-{source_id}",
            type="CableTrench",
            components=components,
            source_sdtl_object=source_id,
            transform=source_transform(source),
            traceability=source_traceability(source),
            metadata={
                "generator": self.__class__.__name__,
                "open_channel": True,
                "coordinate_system": "right-handed-z-up",
                **engineering_metadata(source, dimensions, material.name),
            },
        )
