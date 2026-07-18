from __future__ import annotations

from typing import Any

from backend.geometry_3d.models import Object3D, load_material

from ._common import (
    box_component,
    engineering_metadata,
    require_dimensions,
    source_traceability,
    source_transform,
    validate_source,
)


class FoundationGenerator:
    """Generate a closed footing mesh from an approved Foundation object."""

    def generate(self, source: Any) -> Object3D:
        validate_source(source, "Foundation")
        dimensions = require_dimensions(source, ("length", "width", "height"))
        source_id = str(source.id)
        material = load_material("concrete")
        footing = box_component(
            source_id,
            "Footing",
            dimensions["length"],
            dimensions["width"],
            dimensions["height"],
            material,
        )
        return Object3D(
            id=f"3D-{source_id}",
            type="Foundation",
            components=[footing],
            source_sdtl_object=source_id,
            transform=source_transform(source),
            traceability=source_traceability(source),
            metadata={
                "generator": self.__class__.__name__,
                "coordinate_system": "right-handed-z-up",
                **engineering_metadata(source, dimensions, material.name),
            },
        )
