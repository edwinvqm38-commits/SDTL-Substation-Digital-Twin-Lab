from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field

from .cad_metadata import CADDocument, CADEntity
from .dxf_reader import DXFReader


class CADLayerAnalysis(BaseModel):
    """Aggregated, traceable use of one native CAD layer across documents."""

    model_config = ConfigDict(extra="forbid")

    layer_name: str
    total_entities: int = Field(default=0, ge=0)
    entity_types: dict[str, int] = Field(default_factory=dict)
    source_documents: list[str] = Field(default_factory=list)
    geometry_types: dict[str, int] = Field(default_factory=dict)
    handles_sample: list[str] = Field(default_factory=list)


class CADProjectLayerReport(BaseModel):
    """Project-wide inventory of native CAD layers and their entity usage."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    total_documents: int = Field(ge=0)
    total_layers: int = Field(ge=0)
    layers: dict[str, CADLayerAnalysis] = Field(default_factory=dict)
    global_statistics: dict[str, Any] = Field(default_factory=dict)


class CADLayerAnalyzer:
    """Aggregate exact DXF layer information without changing source CAD data."""

    _GEOMETRY_TYPES = {
        "LINE": "line",
        "LWPOLYLINE": "polyline",
        "POLYLINE": "polyline",
        "ARC": "curve",
        "CIRCLE": "curve",
        "TEXT": "text",
        "MTEXT": "text",
        "INSERT": "block_reference",
        "DIMENSION": "annotation",
        "MULTILEADER": "annotation",
        "LEADER": "annotation",
        "HATCH": "fill",
    }

    def __init__(
        self,
        reader: DXFReader | None = None,
        handles_sample_size: int = 20,
    ) -> None:
        if handles_sample_size < 0:
            raise ValueError("handles_sample_size must be zero or greater")
        self.reader = reader or DXFReader()
        self.handles_sample_size = handles_sample_size

    def analyze_directory(
        self,
        directory: str | Path,
        pattern: str = "*.dxf",
    ) -> CADProjectLayerReport:
        """Read and aggregate every matching DXF in a directory."""

        source_directory = Path(directory)
        if not source_directory.is_dir():
            raise NotADirectoryError(f"DXF directory not found: {source_directory}")

        paths = sorted(
            source_directory.glob(pattern),
            key=lambda path: path.name.casefold(),
        )
        if not paths:
            raise ValueError(
                f"No DXF documents matching {pattern!r} found in: {source_directory}"
            )
        return self.analyze_files(paths)

    def analyze_files(
        self,
        paths: Iterable[str | Path],
    ) -> CADProjectLayerReport:
        """Read selected DXF paths sequentially and aggregate their layers."""

        return self.analyze_documents(self.reader.read(path) for path in paths)

    def analyze_documents(
        self,
        documents: Iterable[CADDocument],
    ) -> CADProjectLayerReport:
        """Aggregate existing CAD documents while preserving their native values."""

        layer_state: dict[str, dict[str, Any]] = {}
        global_entity_types: Counter[str] = Counter()
        global_geometry_types: Counter[str] = Counter()
        units: Counter[str] = Counter()
        versions: Counter[str] = Counter()
        document_statistics: list[dict[str, Any]] = []
        total_documents = 0
        total_entities = 0
        supported_entities = 0
        unsupported_entities = 0

        for document in documents:
            total_documents += 1
            total_entities += document.statistics.total_entities
            supported_entities += document.statistics.supported_entities
            unsupported_entities += document.statistics.unsupported_entities
            units[document.units or "unspecified"] += 1
            versions[document.version] += 1

            declared_layers = {layer.name for layer in document.layers}
            for layer_name in declared_layers:
                state = self._layer_state(layer_state, layer_name)
                state["source_documents"].add(document.filename)

            for entity in document.entities:
                state = self._layer_state(layer_state, entity.layer)
                state["source_documents"].add(document.filename)
                state["total_entities"] += 1
                state["entity_types"][entity.entity_type] += 1

                geometry_type = self._geometry_type(entity)
                state["geometry_types"][geometry_type] += 1
                global_entity_types[entity.entity_type] += 1
                global_geometry_types[geometry_type] += 1

                if len(state["handles_sample"]) < self.handles_sample_size:
                    state["handles_sample"].append(entity.entity_id)

            document_statistics.append(
                {
                    "document_id": document.document_id,
                    "filename": document.filename,
                    "version": document.version,
                    "units": document.units,
                    "declared_layers": len(declared_layers),
                    "total_entities": document.statistics.total_entities,
                    "supported_entities": document.statistics.supported_entities,
                    "unsupported_entities": document.statistics.unsupported_entities,
                }
            )

        layers = {
            layer_name: CADLayerAnalysis(
                layer_name=layer_name,
                total_entities=state["total_entities"],
                entity_types=dict(sorted(state["entity_types"].items())),
                source_documents=sorted(
                    state["source_documents"], key=str.casefold
                ),
                geometry_types=dict(sorted(state["geometry_types"].items())),
                handles_sample=state["handles_sample"],
            )
            for layer_name, state in sorted(
                layer_state.items(), key=lambda item: item[0].casefold()
            )
        }

        return CADProjectLayerReport(
            generated_at=datetime.now(timezone.utc),
            total_documents=total_documents,
            total_layers=len(layers),
            layers=layers,
            global_statistics={
                "total_entities": total_entities,
                "supported_entities": supported_entities,
                "unsupported_entities": unsupported_entities,
                "entity_types": dict(sorted(global_entity_types.items())),
                "geometry_types": dict(sorted(global_geometry_types.items())),
                "units": dict(sorted(units.items())),
                "versions": dict(sorted(versions.items())),
                "handles_sample_size": self.handles_sample_size,
                "documents": document_statistics,
            },
        )

    def save_report(
        self,
        report: CADProjectLayerReport,
        path: str | Path = "layer_analysis.json",
    ) -> Path:
        """Serialize a layer report as UTF-8 JSON."""

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return destination

    def analyze_and_save(
        self,
        directory: str | Path,
        output_path: str | Path = "layer_analysis.json",
        pattern: str = "*.dxf",
    ) -> CADProjectLayerReport:
        """Analyze a DXF directory and persist the resulting project report."""

        report = self.analyze_directory(directory, pattern=pattern)
        self.save_report(report, output_path)
        return report

    @staticmethod
    def _layer_state(
        layer_state: dict[str, dict[str, Any]],
        layer_name: str,
    ) -> dict[str, Any]:
        return layer_state.setdefault(
            layer_name,
            {
                "total_entities": 0,
                "entity_types": Counter(),
                "source_documents": set(),
                "geometry_types": Counter(),
                "handles_sample": [],
            },
        )

    @classmethod
    def _geometry_type(cls, entity: CADEntity) -> str:
        return cls._GEOMETRY_TYPES.get(entity.entity_type, "other")
