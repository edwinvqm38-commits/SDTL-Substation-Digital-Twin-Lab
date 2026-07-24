from __future__ import annotations

from math import hypot
from typing import Any

from backend.geometry_3d.models import Mesh, Object3D, Object3DComponent, load_material

from ._common import source_traceability, validate_source

# A conventional first-pass sag ratio (drop over horizontal span) used only
# when the input CSV doesn't give a real, engineered sag value -- flagged in
# the generated model's metadata rather than presented as measured.
_ASSUMED_SAG_RATIO = 1 / 20
_SEGMENTS = 20
# The real conductor diameter (a couple of centimeters) is invisible next to
# a span of hundreds of meters, and this pipeline has no per-conductor-type
# diameter table to render true-to-scale anyway. The ribbon width is always
# a visualization exaggeration -- proportional to the span so it stays
# visible at any zoom level, clamped so it neither disappears on short spans
# nor overwhelms the towers on long ones -- and is flagged as such in the
# generated model's metadata rather than presented as measured.
_VISUAL_WIDTH_RATIO = 1 / 60
_MIN_VISUAL_WIDTH_M = 0.5
_MAX_VISUAL_WIDTH_M = 5.0
# Fraction of tower height where the crossarm (and so the conductor
# attachment point) sits -- matches TowerGenerator's own crossarm placement.
_ATTACHMENT_HEIGHT_FRACTION = 0.85


class ConductorSpanGenerator:
    """Generate a sagging ribbon mesh between the two towers a span connects.

    Every other generator in this pipeline derives geometry purely from its
    own approved object; a span doesn't exist without both endpoint towers,
    so this generator additionally takes the imported tower lookup instead
    of trying to embed one tower's position inside the other's object.
    Sag is approximated with the standard shallow-catenary parabola
    z(t) = 4*sag*t*(1-t), accurate for the small sag-to-span ratios typical
    of transmission conductors; the conductor is rendered as a flat ribbon
    (not a round tube) since a single perpendicular offset is enough for
    visualization and avoids computing a full Frenet frame per segment. The
    ribbon's width is a deliberate visualization exaggeration -- a real
    conductor's diameter would be invisible at line-span distances -- and is
    marked "visual_width_not_to_scale" in the model's metadata.
    """

    def generate(self, source: Any, towers_by_id: dict[str, Any]) -> Object3D:
        validate_source(source, "ConductorSpan")
        try:
            start_tower = towers_by_id[source.from_tower_id]
            end_tower = towers_by_id[source.to_tower_id]
        except KeyError as error:
            raise ValueError(f"ConductorSpan references an unknown tower: {error}") from error

        start = _attachment_point(start_tower)
        end = _attachment_point(end_tower)
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        horizontal_span = hypot(dx, dy)
        if horizontal_span <= 0:
            raise ValueError("ConductorSpan towers must be at different horizontal positions")

        sag = source.sag_m
        assumed_sag = sag is None
        if assumed_sag:
            sag = horizontal_span * _ASSUMED_SAG_RATIO

        visual_width = min(
            max(horizontal_span * _VISUAL_WIDTH_RATIO, _MIN_VISUAL_WIDTH_M),
            _MAX_VISUAL_WIDTH_M,
        )
        half_width = visual_width / 2
        nx = -dy / horizontal_span * half_width
        ny = dx / horizontal_span * half_width

        vertices: list[list[float]] = []
        for step in range(_SEGMENTS + 1):
            t = step / _SEGMENTS
            x = start[0] + dx * t
            y = start[1] + dy * t
            base_z = start[2] + (end[2] - start[2]) * t
            z = base_z - 4 * sag * t * (1 - t)
            vertices.append([x - nx, y - ny, z])
            vertices.append([x + nx, y + ny, z])

        faces: list[list[int]] = []
        for step in range(_SEGMENTS):
            a, b, c, d = 2 * step, 2 * step + 1, 2 * step + 3, 2 * step + 2
            faces.append([a, b, c])
            faces.append([a, c, d])

        source_id = str(source.id)
        material = load_material("steel")
        conductor = Object3DComponent(
            id=f"CMP-{source_id}-CONDUCTOR",
            name="Conductor",
            mesh=Mesh(
                id=f"MESH-{source_id}-CONDUCTOR",
                vertices=vertices,
                faces=faces,
                metadata={"component_role": "Conductor"},
            ),
            material=material,
        )

        return Object3D(
            id=f"3D-{source_id}",
            type="ConductorSpan",
            components=[conductor],
            source_sdtl_object=source_id,
            traceability=source_traceability(source),
            metadata={
                "generator": self.__class__.__name__,
                "coordinate_system": "right-handed-z-up",
                "horizontal_span_m": horizontal_span,
                "sag_m": sag,
                "sag_assumed": assumed_sag,
                "visual_width_m": visual_width,
                "visual_width_not_to_scale": True,
                "conductors_per_phase": source.conductors_per_phase,
                "material": material.name,
                "state": source.state,
            },
        )


def _attachment_point(tower: Any) -> tuple[float, float, float]:
    position = tower.properties.get("position")
    if not isinstance(position, (list, tuple)) or len(position) != 3:
        raise ValueError(
            f"Tower {tower.id} has no projected local position; run the "
            "line's geo projection before generating span geometry"
        )
    east, north, up = position
    return (east, north, up + tower.height_m * _ATTACHMENT_HEIGHT_FRACTION)
