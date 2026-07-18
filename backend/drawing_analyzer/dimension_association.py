from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DimensionAssociation(BaseModel):
    """Association between dimensional information and vector geometry."""

    model_config = ConfigDict(extra="forbid")

    association_id: str
    dimension_id: str
    dimension_line_id: str | None = None
    target_geometry_id: str | None = None
    relation_type: str
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)
