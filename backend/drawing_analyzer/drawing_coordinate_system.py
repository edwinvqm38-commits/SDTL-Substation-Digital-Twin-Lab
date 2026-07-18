from __future__ import annotations

from math import cos, radians, sin
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .scale_detector import DrawingScale


class DrawingCoordinateSystem(BaseModel):
    """Internal drawing coordinate system and traceable PDF-to-world transform."""

    model_config = ConfigDict(extra="forbid")

    coordinate_system_id: str
    document_id: str
    page_number: int
    origin: tuple[float, float]
    rotation: float
    unit: str
    bounds: dict[str, Any] = Field(default_factory=dict)
    transform: list[list[float]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DrawingCoordinateSystemBuilder:
    """Build and apply an affine transform from PDF coordinates to drawing coordinates."""

    def build(
        self,
        document_id: str,
        page_number: int,
        page_width: float,
        page_height: float,
        scale: DrawingScale | None = None,
        origin: tuple[float, float] = (0.0, 0.0),
        rotation: float = 0.0,
        unit: str = "m",
    ) -> DrawingCoordinateSystem:
        if page_width < 0 or page_height < 0:
            raise ValueError("Page dimensions must be greater than or equal to zero")

        scale_factor = (
            scale.real_units / scale.paper_units
            if scale is not None and scale.paper_units != 0
            else 1.0
        )
        resolved_unit = scale.unit if scale is not None and scale.unit else unit
        angle = radians(rotation)
        cosine = cos(angle)
        sine = sin(angle)
        transform = [
            [scale_factor * cosine, scale_factor * sine, float(origin[0])],
            [scale_factor * sine, -scale_factor * cosine, float(origin[1])],
            [0.0, 0.0, 1.0],
        ]

        system = DrawingCoordinateSystem(
            coordinate_system_id=f"DCS-{uuid4().hex}",
            document_id=document_id,
            page_number=page_number,
            origin=(float(origin[0]), float(origin[1])),
            rotation=float(rotation),
            unit=resolved_unit,
            bounds={
                "pdf": {
                    "x": 0.0,
                    "y": 0.0,
                    "width": float(page_width),
                    "height": float(page_height),
                }
            },
            transform=transform,
            metadata={
                "transform_type": "pdf_to_world_matrix",
                "scale_id": scale.scale_id if scale is not None else None,
                "scale_factor": scale_factor,
                "pdf_y_axis": "down",
                "world_y_axis": "up",
            },
        )
        world_corners = [
            self.transform_point(system, 0.0, 0.0),
            self.transform_point(system, page_width, 0.0),
            self.transform_point(system, 0.0, page_height),
            self.transform_point(system, page_width, page_height),
        ]
        system.bounds["world"] = {
            "x_min": min(point[0] for point in world_corners),
            "y_min": min(point[1] for point in world_corners),
            "x_max": max(point[0] for point in world_corners),
            "y_max": max(point[1] for point in world_corners),
        }
        return system

    def transform_point(
        self,
        coordinate_system: DrawingCoordinateSystem,
        x: float,
        y: float,
    ) -> tuple[float, float]:
        matrix = coordinate_system.transform
        if len(matrix) != 3 or any(len(row) != 3 for row in matrix):
            raise ValueError("Coordinate transform must be a 3x3 matrix")
        world_x = matrix[0][0] * x + matrix[0][1] * y + matrix[0][2]
        world_y = matrix[1][0] * x + matrix[1][1] * y + matrix[1][2]
        return world_x, world_y
