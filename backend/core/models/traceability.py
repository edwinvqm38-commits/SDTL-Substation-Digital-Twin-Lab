from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ObjectTraceability(BaseModel):
    """Auditable link from an engineering document location to a digital-twin object."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    document_id: str
    object_id: str
    relation_type: str
    page_number: int | None = None
    region_reference: str | None = None
    extraction_method: str
