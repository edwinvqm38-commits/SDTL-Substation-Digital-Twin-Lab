from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.core.models import Project, SDTLObject


def load_json(path: str | Path) -> Any:
    """Read and decode a UTF-8 JSON file."""

    source = Path(path)
    with source.open(encoding="utf-8") as json_file:
        return json.load(json_file)


def load_project(path: str | Path) -> Project:
    """Load and validate a standalone Project or a Project from an SDTL data bundle."""

    payload = _require_json_object(load_json(path), path)
    project_data = payload.get("project", payload)
    return Project.model_validate(project_data)


def load_object(path: str | Path) -> SDTLObject:
    """Load and validate a standalone SDTLObject or the single object in an SDTL data bundle."""

    payload = _require_json_object(load_json(path), path)

    if "object" in payload:
        object_data = payload["object"]
    elif "objects" in payload:
        objects = payload["objects"]
        if not isinstance(objects, list) or len(objects) != 1:
            raise ValueError(
                f"Expected exactly one object in SDTL bundle: {Path(path)}"
            )
        object_data = objects[0]
    else:
        object_data = payload

    return SDTLObject.model_validate(object_data)


def _require_json_object(payload: Any, path: str | Path) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in SDTL file: {Path(path)}")
    return payload
