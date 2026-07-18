from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExtractionResult(BaseModel):
    """Structured element extracted from an engineering document for later validation and processing."""

    model_config = ConfigDict(extra="forbid")

    extraction_id: str
    document_id: str
    element_type: str
    confidence: float
    geometry_reference: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
