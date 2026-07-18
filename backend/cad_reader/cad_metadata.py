from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CADLayer(BaseModel):
    """Definition and display state of a native CAD layer."""

    model_config = ConfigDict(extra="forbid")

    name: str
    color: int | None = None
    linetype: str | None = None
    lineweight: int | None = None
    is_off: bool = False
    is_frozen: bool = False
    is_locked: bool = False


class CADStatistics(BaseModel):
    """Mapping statistics for all entities found in DXF modelspace."""

    model_config = ConfigDict(extra="forbid")

    total_entities: int = 0
    supported_entities: int = 0
    unsupported_entities: int = 0
    entity_types: dict[str, int] = Field(default_factory=dict)


class CADEntity(BaseModel):
    """Traceable SDTL representation of one native DXF entity."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str
    entity_type: str
    layer: str
    coordinates: dict[str, Any] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)
    source_type: Literal["DXF"] = "DXF"
    mapping_status: Literal["supported", "unsupported"] = "supported"


class CADDocument(BaseModel):
    """Native CAD document with metadata, layers, statistics, and mapped entities."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    filename: str
    version: str
    units: str | None = None
    layers: list[CADLayer] = Field(default_factory=list)
    statistics: CADStatistics = Field(default_factory=CADStatistics)
    metadata: dict[str, Any] = Field(default_factory=dict)
    entities: list[CADEntity] = Field(default_factory=list)
