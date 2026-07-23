from __future__ import annotations

import json
from pathlib import Path

from backend.sdtl_core.entities import CivilObject
from backend.object_generation import ObjectMapper


class ReviewQueue:
    """Persist extracted SDTL object proposals so a human can review and
    approve them before any 3D geometry is generated.

    This is the explicit human-in-the-loop gate the SDTL data model already
    enforces (CivilObject.approve/activate) -- this class only adds
    load/save so that gate can span a CLI session instead of one process.
    """

    def __init__(self, mapper: ObjectMapper | None = None) -> None:
        self.mapper = mapper or ObjectMapper()

    def save(self, objects: list[CivilObject], path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = [obj.model_dump(mode="json") for obj in objects]
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def load(self, path: str | Path) -> list[CivilObject]:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"Review queue not found: {source}")
        payload = json.loads(source.read_text(encoding="utf-8"))
        return [
            self.mapper.entity_class(item["type"]).model_validate(item) for item in payload
        ]

    def approve(self, path: str | Path, object_id: str, reviewer: str) -> CivilObject:
        """Approve one object in a persisted queue and rewrite the file."""

        objects = self.load(path)
        target = next((obj for obj in objects if obj.id == object_id), None)
        if target is None:
            raise ValueError(f"No object with id {object_id!r} in review queue: {path}")

        target.approve(reviewer)
        self.save(objects, path)
        return target
