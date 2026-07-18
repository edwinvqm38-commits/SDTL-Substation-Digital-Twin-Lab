from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .classification import Classification
from .document import DocumentReference
from .event import SDTLEvent
from .geometry import Geometry
from .lifecycle import LifecycleEvent, LifecycleState
from .relationship import Relationship
from .spatial import SpatialPosition
from .traceability import ObjectTraceability
from .version import ObjectVersion


class SDTLObject(BaseModel):
    """Main domain entity for a substation digital twin object across civil, electrical, BIM, and logical models."""

    model_config = ConfigDict(extra="forbid")

    id: str
    object_type: str
    category: str
    name: str
    state: str = "undefined"
    properties: dict[str, Any] = Field(default_factory=dict)
    geometry: Geometry | None = None
    documents: list[DocumentReference] = Field(default_factory=list)
    events: list[SDTLEvent] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    classifications: list[Classification] = Field(default_factory=list)
    lifecycle_states: list[LifecycleState] = Field(default_factory=list)
    history: list[LifecycleEvent] = Field(default_factory=list)
    versions: list[ObjectVersion] = Field(default_factory=list)
    traceability: list[ObjectTraceability] = Field(default_factory=list)
    spatial_position: SpatialPosition | None = None
    # Kept for loading and serializing SDTL Core v0.1 objects.
    relations: list[str] = Field(default_factory=list)
