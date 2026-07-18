from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentReference(BaseModel):
    """Links SDTL objects to engineering documents such as PDF, CAD, manuals, and datasheets."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    name: str
    document_type: str
    revision: str
    source: str
    date_created: datetime
