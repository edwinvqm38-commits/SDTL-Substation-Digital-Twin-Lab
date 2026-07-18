from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .extraction import ExtractionResult


class EngineeringDocument(BaseModel):
    """Controlled engineering document such as a drawing, CAD file, report, or technical specification."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    name: str
    document_type: str
    discipline: str
    revision: str
    status: str
    source_file: str | None = None
    pages: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    extractions: list[ExtractionResult] = Field(default_factory=list)
