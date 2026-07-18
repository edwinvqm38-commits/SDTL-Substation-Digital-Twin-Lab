from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DimensionGeometryLink(BaseModel):
    """Represents the complete relation between a graphical dimension and its measured target geometry."""

    model_config = ConfigDict(extra="forbid")

    link_id: str
    dimension_id: str
    dimension_line_id: str | None = None
    extension_geometry_ids: list[str] = Field(default_factory=list)
    target_geometry_id: str | None = None
    relation_type: str
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)
