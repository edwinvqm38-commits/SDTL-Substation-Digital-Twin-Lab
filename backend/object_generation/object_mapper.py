from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

from backend.sdtl_core.entities import (
    CableTrench,
    CivilObject,
    ElectricalRoom,
    Fence,
    Foundation,
    Road,
)


CivilObjectType: TypeAlias = type[CivilObject]


class ObjectMapper:
    """Map analyzer candidate types to persistent SDTL civil entity types."""

    _entity_types: dict[str, CivilObjectType] = {
        "ElectricalRoom": ElectricalRoom,
        "CableTrench": CableTrench,
        "Foundation": Foundation,
        "Fence": Fence,
        "Road": Road,
    }

    def __init__(self, catalog_path: str | Path | None = None) -> None:
        path = Path(catalog_path) if catalog_path else self._default_catalog_path()
        self._mapping = self._load_mapping(path)

    def map_type(self, candidate_type: str) -> str:
        """Return the SDTL entity name for a supported candidate type."""

        try:
            return self._mapping[candidate_type]
        except KeyError as error:
            raise ValueError(f"Unsupported engineering candidate type: {candidate_type}") from error

    def map_candidate_type(self, candidate_type: str) -> str:
        """Descriptive alias for map_type()."""

        return self.map_type(candidate_type)

    def entity_class(self, object_type: str) -> CivilObjectType:
        """Resolve the Pydantic entity class for a mapped object type."""

        try:
            return self._entity_types[object_type]
        except KeyError as error:
            raise ValueError(f"Unsupported SDTL civil object type: {object_type}") from error

    @staticmethod
    def _default_catalog_path() -> Path:
        return Path(__file__).parents[1] / "sdtl_catalog" / "civil_objects.json"

    @staticmethod
    def _load_mapping(path: Path) -> dict[str, str]:
        try:
            with path.open(encoding="utf-8") as catalog_file:
                payload = json.load(catalog_file)
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Unable to load SDTL civil object catalog: {path}") from error

        mapping = {
            item["candidate_type"]: item["object_type"]
            for item in payload.get("objects", [])
            if item.get("candidate_type") and item.get("object_type")
        }
        if not mapping:
            raise ValueError(f"SDTL civil object catalog contains no mappings: {path}")
        return mapping
