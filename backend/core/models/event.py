from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SDTLEvent(BaseModel):
    """Captures lifecycle events for construction, maintenance, operation, and failures."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    name: str
    description: str
    timestamp: datetime
    responsible: str
