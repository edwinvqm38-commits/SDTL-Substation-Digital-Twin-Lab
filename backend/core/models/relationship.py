from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Relationship(BaseModel):
    """Engineering link between two digital-twin objects, such as electrical connectivity, physical support, or containment."""

    model_config = ConfigDict(extra="forbid")

    relationship_id: str
    source_id: str
    target_id: str
    relationship_type: str
    properties: dict[str, Any] = Field(default_factory=dict)
