from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EngineeringValue(BaseModel):
    """Physical engineering value paired with its unit and an optional domain description."""

    model_config = ConfigDict(extra="forbid")

    value: float
    unit: str
    description: str | None = None
