from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Classification(BaseModel):
    """Classification assigned to a digital-twin object in BIM, IEC 61850, GIS, SCADA, or asset-management systems."""

    model_config = ConfigDict(extra="forbid")

    classification_id: str
    system: str
    code: str
    description: str
