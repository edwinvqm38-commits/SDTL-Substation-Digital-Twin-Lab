from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .material import Material3D
from .mesh import Mesh
from .transform import Transform


class Object3DComponent(BaseModel):
    """Named engineering component with its own mesh, material, and transform."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    mesh: Mesh
    material: Material3D
    transform: Transform = Field(default_factory=Transform)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Object3D(BaseModel):
    """Complete parametric 3D representation derived from one approved SDTL object."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    components: list[Object3DComponent] = Field(default_factory=list)
    source_sdtl_object: str
    transform: Transform = Field(default_factory=Transform)
    traceability: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def source(self) -> str:
        """Short compatibility alias for source_sdtl_object."""

        return self.source_sdtl_object

    @property
    def component_names(self) -> list[str]:
        """Return component names without discarding their geometric models."""

        return [component.name for component in self.components]
