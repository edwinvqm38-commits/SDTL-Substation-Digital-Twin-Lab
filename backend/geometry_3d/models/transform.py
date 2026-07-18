from __future__ import annotations

from math import cos, radians, sin

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Transform(BaseModel):
    """Position, Euler rotation in degrees, and scale for a parametric 3D object."""

    model_config = ConfigDict(extra="forbid")

    position: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: list[float] = Field(default_factory=lambda: [1.0, 1.0, 1.0])

    @field_validator("position", "rotation", "scale")
    @classmethod
    def validate_vector(cls, value: list[float]) -> list[float]:
        if len(value) != 3:
            raise ValueError("A 3D transform vector must contain three values")
        return value

    @field_validator("scale")
    @classmethod
    def validate_scale(cls, value: list[float]) -> list[float]:
        if any(component <= 0 for component in value):
            raise ValueError("Transform scale components must be positive")
        return value

    def apply(self, point: list[float]) -> list[float]:
        """Apply scale, XYZ Euler rotation, and translation to a 3D point."""

        if len(point) != 3:
            raise ValueError("A 3D point must contain three values")
        x, y, z = (point[index] * self.scale[index] for index in range(3))
        rx, ry, rz = (radians(value) for value in self.rotation)

        y, z = y * cos(rx) - z * sin(rx), y * sin(rx) + z * cos(rx)
        x, z = x * cos(ry) + z * sin(ry), -x * sin(ry) + z * cos(ry)
        x, y = x * cos(rz) - y * sin(rz), x * sin(rz) + y * cos(rz)

        return [
            x + self.position[0],
            y + self.position[1],
            z + self.position[2],
        ]
