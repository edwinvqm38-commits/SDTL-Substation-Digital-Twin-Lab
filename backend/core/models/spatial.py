from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CoordinateReference(BaseModel):
    """Coordinate reference system used to locate SDTL assets in local, GIS, BIM, or CAD contexts."""

    model_config = ConfigDict(extra="forbid")

    reference_id: str
    system: str
    description: str | None = None


class SpatialPosition(BaseModel):
    """Three-dimensional asset position associated with an optional coordinate reference system."""

    model_config = ConfigDict(extra="forbid")

    x: float
    y: float
    z: float
    coordinate_system: CoordinateReference | None = None
