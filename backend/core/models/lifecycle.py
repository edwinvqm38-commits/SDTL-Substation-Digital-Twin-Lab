from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LifecycleState(BaseModel):
    """Operational state available to an asset throughout its engineering lifecycle."""

    model_config = ConfigDict(extra="forbid")

    state_id: str
    name: str
    description: str


class LifecycleEvent(BaseModel):
    """Timestamped transition between two asset lifecycle states, with responsibility and engineering context."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    timestamp: datetime
    state_from: str
    state_to: str
    description: str
    responsible: str
