from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Material(BaseModel):
    """Describes civil and electrical materials used by SDTL assets."""

    model_config = ConfigDict(extra="forbid")

    material_id: str
    name: str
    category: str
    properties: dict[str, Any] = Field(default_factory=dict)
