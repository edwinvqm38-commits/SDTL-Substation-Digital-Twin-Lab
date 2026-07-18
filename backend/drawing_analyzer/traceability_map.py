from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class TraceabilityMap(BaseModel):
    """Traceable source reference from derived drawing data back to a PDF region."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(default_factory=lambda: f"TM-{uuid4().hex}")
    source_pdf: str
    page: int
    geometry_id: str | None = None
    dimension_ids: list[str] = Field(default_factory=list)
    coordinates: list[list[float]] = Field(default_factory=list)
    text_ids: list[str] = Field(default_factory=list)
    topology_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def references_dimension(self, dimension_id: str) -> bool:
        """Return whether this PDF source record contains the requested dimension."""

        return dimension_id in self.dimension_ids
