from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DocumentSet(BaseModel):
    """Discipline-based collection of engineering document identifiers within an SDTL project."""

    model_config = ConfigDict(extra="forbid")

    set_id: str
    name: str
    discipline: str
    description: str | None = None
    documents: list[str] = Field(default_factory=list)
