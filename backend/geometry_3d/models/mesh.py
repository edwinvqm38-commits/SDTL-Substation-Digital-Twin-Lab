from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Mesh(BaseModel):
    """Serializable geometric mesh containing topology but no engineering rules."""

    model_config = ConfigDict(extra="forbid")

    id: str
    vertices: list[list[float]] = Field(default_factory=list)
    faces: list[list[int]] = Field(default_factory=list)
    normals: list[list[float]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_topology(self) -> Mesh:
        if any(len(vertex) != 3 for vertex in self.vertices):
            raise ValueError("Every mesh vertex must contain x, y, and z")
        if any(len(face) < 3 for face in self.faces):
            raise ValueError("Every mesh face must contain at least three indices")
        vertex_count = len(self.vertices)
        if any(
            index < 0 or index >= vertex_count
            for face in self.faces
            for index in face
        ):
            raise ValueError("Mesh face references a vertex outside the mesh")
        if self.normals and len(self.normals) != vertex_count:
            raise ValueError("Mesh normals must be empty or match the vertex count")
        if any(len(normal) != 3 for normal in self.normals):
            raise ValueError("Every mesh normal must contain x, y, and z")
        return self
