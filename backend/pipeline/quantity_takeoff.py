from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.sdtl_core.entities import CivilObject


@dataclass
class TypeQuantities:
    object_type: str
    count: int = 0
    total_length_m: float = 0.0
    total_area_m2: float = 0.0
    total_volume_m3: float = 0.0
    objects_missing_dimensions: list[str] = field(default_factory=list)


class QuantityTakeoffBuilder:
    """Aggregate lengths, areas, volumes, and counts per object type across a
    project -- the "metrado" the per-entity measurements in drawing_analyzer
    do not provide on their own (they only measure one geometry at a time).

    Only objects that reached at least "approved" state are counted, since a
    proposal's geometry/dimensions are not yet confirmed by a human reviewer.
    """

    _COUNTABLE_STATES = {"approved", "active", "modified"}

    def build(self, objects: list[CivilObject]) -> dict[str, Any]:
        by_type: dict[str, TypeQuantities] = {}

        for civil_object in objects:
            if civil_object.state not in self._COUNTABLE_STATES:
                continue

            quantities = by_type.setdefault(
                civil_object.type, TypeQuantities(object_type=civil_object.type)
            )
            quantities.count += 1

            dimensions = self._named_dimensions(civil_object)
            if not dimensions:
                quantities.objects_missing_dimensions.append(civil_object.id)
                continue

            length = dimensions.get("length")
            width = dimensions.get("width")
            height = dimensions.get("height", dimensions.get("depth"))

            if length is not None:
                quantities.total_length_m += length
            if length is not None and width is not None:
                quantities.total_area_m2 += length * width
            if length is not None and width is not None and height is not None:
                quantities.total_volume_m3 += length * width * height

        return {
            "quantity_takeoff": {
                object_type: {
                    "count": quantities.count,
                    "total_length_m": round(quantities.total_length_m, 3),
                    "total_area_m2": round(quantities.total_area_m2, 3),
                    "total_volume_m3": round(quantities.total_volume_m3, 3),
                    "objects_missing_dimensions": quantities.objects_missing_dimensions,
                }
                for object_type, quantities in by_type.items()
            }
        }

    @staticmethod
    def _named_dimensions(civil_object: CivilObject) -> dict[str, float]:
        raw = civil_object.dimensions
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, list):
            return {
                item["name"]: item["value"]
                for item in raw
                if isinstance(item, dict) and "name" in item and "value" in item
            }
        return {}
