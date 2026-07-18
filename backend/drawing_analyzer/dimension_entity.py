from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DimensionEntity(BaseModel):
    """Dimensional entity extracted from engineering documentation."""

    model_config = ConfigDict(extra="forbid")

    dimension_id: str
    document_id: str
    page_number: int
    dimension_type: str
    value: float | None = None
    unit: str | None = None
    text_source_id: str | None = None
    geometry_reference_id: str | None = None
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)
