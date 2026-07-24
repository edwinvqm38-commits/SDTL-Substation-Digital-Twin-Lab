from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.geometry_3d import ConductorSpanGenerator, GLTFExporter, TowerGenerator

from .geo_projection import LocalEnuProjection
from .line_importer import TransmissionLineImporter
from .models import ConductorSpan, Tower


@dataclass
class ImportedLine:
    towers: list[Tower]
    spans: list[ConductorSpan]
    projection: LocalEnuProjection


@dataclass
class GeneratedAsset:
    asset_id: str
    asset_type: str
    gltf_path: Path


@dataclass
class TransmissionLineResult:
    generated: list[GeneratedAsset] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)


class TransmissionLinePipeline:
    """Import a transmission line from structured CSV and, once each tower and
    span is human-approved, generate 3D geometry for it as glTF.

    Geographic projection happens at import time (every tower needs a local
    position before any span's sag geometry can be built), but nothing is
    3D-generated until a reviewer calls .approve() on the specific tower or
    span -- import alone never creates active digital-twin geometry.
    """

    def __init__(
        self,
        importer: TransmissionLineImporter | None = None,
        tower_generator: TowerGenerator | None = None,
        span_generator: ConductorSpanGenerator | None = None,
        exporter: GLTFExporter | None = None,
    ) -> None:
        self.importer = importer or TransmissionLineImporter()
        self.tower_generator = tower_generator or TowerGenerator()
        self.span_generator = span_generator or ConductorSpanGenerator()
        self.exporter = exporter or GLTFExporter()

    def import_line(self, towers_csv: str | Path, spans_csv: str | Path) -> ImportedLine:
        towers = self.importer.import_towers(towers_csv)
        spans = self.importer.import_spans(spans_csv, towers)

        projection = LocalEnuProjection(towers[0].location)
        for tower in towers:
            east, north, up = projection.to_local(tower.location)
            tower.properties = {**tower.properties, "position": [east, north, up]}

        return ImportedLine(towers=towers, spans=spans, projection=projection)

    def generate_3d(
        self,
        towers: list[Tower],
        spans: list[ConductorSpan],
        output_dir: str | Path,
    ) -> TransmissionLineResult:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        result = TransmissionLineResult()
        towers_by_id: dict[str, Any] = {tower.id: tower for tower in towers}

        for tower in towers:
            if tower.state not in {"approved", "active", "modified"}:
                result.skipped.append(
                    {"asset_id": tower.id, "reason": f"tower is not approved (state={tower.state})"}
                )
                continue
            model = self.tower_generator.generate(tower)
            gltf_path = self.exporter.export_file(model, output / f"{tower.id}.gltf")
            result.generated.append(GeneratedAsset(tower.id, "Tower", gltf_path))

        for span in spans:
            if span.state not in {"approved", "active", "modified"}:
                result.skipped.append(
                    {"asset_id": span.id, "reason": f"span is not approved (state={span.state})"}
                )
                continue
            model = self.span_generator.generate(span, towers_by_id)
            gltf_path = self.exporter.export_file(model, output / f"{span.id}.gltf")
            result.generated.append(GeneratedAsset(span.id, "ConductorSpan", gltf_path))

        return result
