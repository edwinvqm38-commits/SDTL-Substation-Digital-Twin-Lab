from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GeometryEntity(BaseModel):
    """Represents vector geometry originating from an engineering drawing."""

    model_config = ConfigDict(extra="forbid")

    geometry_id: str
    document_id: str
    page_number: int
    entity_type: str
    coordinates: dict[str, Any] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float
