from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from backend.geometry_3d import (
    CableTrenchGenerator,
    FoundationGenerator,
    GLTFExporter,
    RoomGenerator,
)
from backend.sdtl_core.entities import CivilObject

_GENERATORS = {
    "ElectricalRoom": RoomGenerator(),
    "Foundation": FoundationGenerator(),
    "CableTrench": CableTrenchGenerator(),
}


@dataclass
class GeneratedModel:
    object_id: str
    object_type: str
    gltf_path: Path


@dataclass
class ThreeDGenerationResult:
    generated: list[GeneratedModel] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)


class ThreeDGenerationStage:
    """Dispatch approved/active SDTL objects to their geometry_3d generator
    and export the result as glTF.

    Only ElectricalRoom, Foundation, and CableTrench have a generator today
    (see backend/geometry_3d/generators/); Fence and Road are reported as
    skipped rather than failing the whole batch, since their generators do
    not exist yet.
    """

    def __init__(self, exporter: GLTFExporter | None = None) -> None:
        self.exporter = exporter or GLTFExporter()

    def run(self, objects: list[CivilObject], output_dir: str | Path) -> ThreeDGenerationResult:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        result = ThreeDGenerationResult()

        for civil_object in objects:
            if civil_object.state not in {"approved", "active", "modified"}:
                result.skipped.append(
                    {
                        "object_id": civil_object.id,
                        "reason": f"object is not approved (state={civil_object.state})",
                    }
                )
                continue

            generator = _GENERATORS.get(civil_object.type)
            if generator is None:
                result.skipped.append(
                    {
                        "object_id": civil_object.id,
                        "reason": f"no 3D generator implemented for {civil_object.type}",
                    }
                )
                continue

            object_3d = generator.generate(civil_object)
            gltf_path = self.exporter.export_file(
                object_3d, output / f"{civil_object.id}.gltf"
            )
            result.generated.append(
                GeneratedModel(
                    object_id=civil_object.id,
                    object_type=civil_object.type,
                    gltf_path=gltf_path,
                )
            )

        return result
