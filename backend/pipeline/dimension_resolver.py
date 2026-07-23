from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.drawing_analyzer import DimensionEntity
from backend.drawing_analyzer.dimension_topology_analyzer import DimensionTopology
from backend.sdtl_core.entities import CivilObject

_ORIENTATION_TO_DIMENSION = {"horizontal": "length", "vertical": "width"}

_DEFAULT_CATALOG_PATH = Path(__file__).parent / "default_dimensions.json"


class DimensionResolver:
    """Turn a civil object's dimension-id references into named numeric values.

    SDTLObjectFactory only carries dimension *references* (a dimension_id and
    its unit) onto a freshly created CivilObject, because that is all a single
    engineering candidate knows. The geometry_3d generators need named values
    (length/width/height). This resolver closes that gap using the validated
    dimension topology computed during extraction, and documents any value a
    plan view cannot express (e.g. a room's height) as an explicit default
    that still requires a reviewer's confirmation.
    """

    def __init__(self, defaults_path: str | Path | None = None) -> None:
        path = Path(defaults_path) if defaults_path else _DEFAULT_CATALOG_PATH
        with path.open(encoding="utf-8") as defaults_file:
            self._defaults: dict[str, dict[str, dict[str, Any]]] = json.load(defaults_file)

    def resolve(
        self,
        civil_object: CivilObject,
        dimensions_by_id: dict[str, DimensionEntity],
        topologies: list[DimensionTopology],
    ) -> None:
        """Mutate civil_object.dimensions/properties in place with resolved values."""

        raw_dimensions = civil_object.dimensions
        if not isinstance(raw_dimensions, list):
            return

        topology_orientation = {
            topology.dimension_id: topology.orientation
            for topology in topologies
            if topology.valid
        }

        resolved: dict[str, dict[str, Any]] = {}
        for item in raw_dimensions:
            reference = item.get("reference")
            dimension = dimensions_by_id.get(reference)
            if dimension is None or dimension.value is None:
                continue
            name = _ORIENTATION_TO_DIMENSION.get(topology_orientation.get(reference))
            if name is None or name in resolved:
                continue
            resolved[name] = {
                "name": name,
                "value": dimension.value,
                "unit": dimension.unit or "m",
                "source": "drawing",
                "dimension_id": reference,
            }

        defaults_applied: list[str] = []
        for name, default in self._defaults.get(civil_object.type, {}).items():
            if name not in resolved:
                resolved[name] = {
                    "name": name,
                    "value": default["value"],
                    "unit": default.get("unit", "m"),
                    "source": "default",
                }
                defaults_applied.append(name)

        civil_object.dimensions = list(resolved.values())
        civil_object.properties = {
            **civil_object.properties,
            "dimension_defaults_applied": defaults_applied,
        }
