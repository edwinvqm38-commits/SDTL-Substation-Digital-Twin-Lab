from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SpatialRelation(BaseModel):
    """Represents a spatial relation between located text and vector geometry."""

    model_config = ConfigDict(extra="forbid")

    relation_id: str
    text_id: str
    geometry_id: str
    relation_type: str
    distance: float | None = None
    overlap_ratio: float | None = None
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)
