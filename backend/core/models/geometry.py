from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Point3D(BaseModel):
    """Represents a spatial point in the SDTL digital twin coordinate system."""

    model_config = ConfigDict(extra="forbid")

    x: float
    y: float
    z: float


class Dimensions(BaseModel):
    """Defines the physical envelope of a civil, electrical, or BIM object."""

    model_config = ConfigDict(extra="forbid")

    length: float
    width: float
    height: float


class Geometry(BaseModel):
    """Groups position, dimensions, and geometry classification for an SDTL asset."""

    model_config = ConfigDict(extra="forbid")

    position: Point3D
    dimensions: Dimensions
    geometry_type: str
