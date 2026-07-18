from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EngineeringCandidate(BaseModel):
    """Evidence-backed semantic candidate that is not yet an SDTL domain object."""

    model_config = ConfigDict(extra="forbid")

    id: str
    status: str = "candidate"
    possible_type: str
    confidence: float
    source_geometry: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    traceability: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
