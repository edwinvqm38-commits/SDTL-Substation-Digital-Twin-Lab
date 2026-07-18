from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentAnalysis(BaseModel):
    """Structured summary of document extraction results, ready for future OCR and engineering analysis pipelines."""

    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    document_id: str
    status: str
    elements_detected: int
    dimensions_found: int
    references_found: int
    sections_found: int
    extraction_metadata: dict[str, Any] = Field(default_factory=dict)
