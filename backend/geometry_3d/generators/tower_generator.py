from __future__ import annotations

from typing import Any

from backend.geometry_3d.models import Object3D, Transform, load_material

from ._common import (
    box_component,
    source_traceability,
    source_transform,
    validate_source,
)

# Visualization-only fallback used when a tower's real base footprint isn't
# in the input data -- flagged in the generated model's metadata rather than
# silently presented as a measured value.
_DEFAULT_BASE_WIDTH_M = 2.0
_CROSSARM_HEIGHT_FRACTION = 0.85


class TowerGenerator:
    """Generate a simplified shaft + crossarm shape for an approved transmission tower.

    Real lattice towers have structural detail (leg spacing, bracing
    pattern...) this pipeline has no survey evidence for; the shaft is a
    single vertical box scaled to the tower's real height so towers place
    and scale correctly in the scene, with a crossarm box near the top so
    they stay visually distinguishable -- not an engineering-accurate
    lattice model.
    """

    def generate(self, source: Any) -> Object3D:
        validate_source(source, "Tower")
        height = source.height_m
        if not isinstance(height, (int, float)) or height <= 0:
            raise ValueError("Tower height_m must be a positive number")

        base_width = source.base_width_m
        assumed_base_width = base_width is None
        if assumed_base_width:
            base_width = _DEFAULT_BASE_WIDTH_M

        source_id = str(source.id)
        material = load_material("steel")
        shaft = box_component(source_id, "Shaft", base_width, base_width, height, material)

        crossarm_length = base_width * 4
        crossarm_height = height * _CROSSARM_HEIGHT_FRACTION
        crossarm = box_component(
            source_id, "Crossarm", crossarm_length, base_width * 0.3, base_width * 0.3, material
        )
        crossarm = crossarm.model_copy(
            update={
                "transform": Transform(
                    position=[
                        base_width / 2 - crossarm_length / 2,
                        base_width / 2 - (base_width * 0.3) / 2,
                        crossarm_height,
                    ]
                )
            }
        )

        return Object3D(
            id=f"3D-{source_id}",
            type="Tower",
            components=[shaft, crossarm],
            source_sdtl_object=source_id,
            transform=source_transform(source),
            traceability=source_traceability(source),
            metadata={
                "generator": self.__class__.__name__,
                "coordinate_system": "right-handed-z-up",
                "height_m": height,
                "base_width_m": base_width,
                "base_width_assumed": assumed_base_width,
                "material": material.name,
                "state": source.state,
            },
        )
