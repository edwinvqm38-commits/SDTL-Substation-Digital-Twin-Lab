from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VisualProperties(BaseModel):
    """Renderer-neutral visual properties for a 3D material."""

    model_config = ConfigDict(extra="allow")

    color: str
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)


class Material3D(BaseModel):
    """Material descriptor kept separate from mesh topology and engineering data."""

    model_config = ConfigDict(extra="forbid")

    name: str
    density: float | None = Field(default=None, gt=0)
    visual: VisualProperties
    metadata: dict[str, Any] = Field(default_factory=dict)


Material = Material3D


def load_material(name: str) -> Material3D:
    """Load a validated renderer-neutral material from the local catalog."""

    if not name.replace("_", "").isalnum():
        raise ValueError(f"Invalid material catalog name: {name}")
    path = Path(__file__).parents[1] / "materials" / f"{name.lower()}.json"
    try:
        with path.open(encoding="utf-8") as material_file:
            payload = json.load(material_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Unable to load 3D material: {name}") from error
    return Material3D.model_validate(payload)
