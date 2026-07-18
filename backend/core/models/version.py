from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ObjectVersion(BaseModel):
    """Auditable version record describing when, why, and by whom a digital-twin object changed."""

    model_config = ConfigDict(extra="forbid")

    version_id: str
    created_date: datetime
    author: str
    description: str
    change_type: str
