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


class EquipmentBoxGenerator:
    """Generate a to-scale footprint box for an approved substation equipment item.

    Real transformers, breakers, disconnectors, busbars, insulators, and
    arresters each look different, but a drawing only ever gives us a 2D
    footprint and a height dimension -- there is no mechanical detail (tank
    fins, bushings, linkage geometry...) for the pipeline to derive without
    inventing it. Rendering every equipment type as its own approved
    footprint box keeps the 3D model honest to what was actually measured.
    """

    def __init__(self, expected_type: str, material_name: str) -> None:
        self.expected_type = expected_type
        self.material_name = material_name

    def generate(self, source: Any) -> Object3D:
        validate_source(source, self.expected_type)
        dimensions = require_dimensions(source, ("length", "width", "height"))
        source_id = str(source.id)
        material = load_material(self.material_name)
        body = box_component(
            source_id,
            "Body",
            dimensions["length"],
            dimensions["width"],
            dimensions["height"],
            material,
        )
        return Object3D(
            id=f"3D-{source_id}",
            type=self.expected_type,
            components=[body],
            source_sdtl_object=source_id,
            transform=source_transform(source),
            traceability=source_traceability(source),
            metadata={
                "generator": self.__class__.__name__,
                "coordinate_system": "right-handed-z-up",
                **engineering_metadata(source, dimensions, material.name),
            },
        )


TransformerGenerator = EquipmentBoxGenerator("Transformer", "steel")
CircuitBreakerGenerator = EquipmentBoxGenerator("CircuitBreaker", "steel")
DisconnectorGenerator = EquipmentBoxGenerator("Disconnector", "steel")
BusbarGenerator = EquipmentBoxGenerator("Busbar", "steel")
InsulatorStringGenerator = EquipmentBoxGenerator("InsulatorString", "porcelain")
LightningArresterGenerator = EquipmentBoxGenerator("LightningArrester", "porcelain")
