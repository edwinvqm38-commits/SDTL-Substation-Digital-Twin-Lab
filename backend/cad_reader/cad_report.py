from __future__ import annotations

import json
from pathlib import Path

from .cad_metadata import CADDocument


class CADReportBuilder:
    """Generate a compact ingestion report without duplicating every CAD entity."""

    VERSION = "0.1"

    def build(
        self,
        document: CADDocument,
        output_path: str | Path = "cad_report.json",
    ) -> Path:
        unsupported_types: dict[str, int] = {}
        supported_types: dict[str, int] = {}
        for entity in document.entities:
            if entity.mapping_status == "unsupported":
                unsupported_types[entity.entity_type] = (
                    unsupported_types.get(entity.entity_type, 0) + 1
                )
            else:
                supported_types[entity.entity_type] = (
                    supported_types.get(entity.entity_type, 0) + 1
                )

        report = {
            "report_version": self.VERSION,
            "document": document.document_id,
            "file": document.filename,
            "dxf_version": document.version,
            "units": document.units,
            "units_code": document.metadata.get("insertion_units_code"),
            "layers": [layer.name for layer in document.layers],
            "statistics": document.statistics.model_dump(),
            "supported_entities": document.statistics.supported_entities,
            "unsupported_entities": document.statistics.unsupported_entities,
            "supported_types": dict(sorted(supported_types.items())),
            "unsupported_types": dict(sorted(unsupported_types.items())),
        }
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return target
