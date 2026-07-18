from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .unit import EngineeringValue


class Project(BaseModel):
    """Engineering project that groups substation assets, voltage levels, and document sets."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    name: str
    project_type: str
    description: str | None = None
    voltage_levels: list[EngineeringValue] = Field(default_factory=list)
    document_sets: list[str] = Field(default_factory=list)
    objects: list[str] = Field(default_factory=list)
    status: str
