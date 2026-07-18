from __future__ import annotations

from collections import Counter
from pathlib import Path

import ezdxf
from ezdxf import recover, units
from ezdxf.lldxf.const import DXFStructureError

from .cad_entity_mapper import CADEntityMapper
from .cad_metadata import CADDocument, CADLayer, CADStatistics


class DXFReader:
    """Read DXF modelspace and preserve native CAD metadata and entities."""

    def __init__(self, mapper: CADEntityMapper | None = None) -> None:
        self.mapper = mapper or CADEntityMapper()

    def read(
        self,
        path: str | Path,
        document_id: str | None = None,
    ) -> CADDocument:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"DXF document not found: {source}")

        recovered = False
        audit_errors = 0
        audit_fixes = 0
        try:
            document = ezdxf.readfile(source)
        except (DXFStructureError, UnicodeDecodeError) as error:
            try:
                document, auditor = recover.readfile(source)
            except Exception as recovery_error:
                raise ValueError(f"Unable to read DXF document: {source}") from recovery_error
            recovered = True
            audit_errors = len(auditor.errors)
            audit_fixes = len(auditor.fixes)
        except (OSError, IOError) as error:
            raise ValueError(f"Unable to read DXF document: {source}") from error

        resolved_id = document_id or source.stem
        modelspace = document.modelspace()
        entities = [
            self.mapper.map_entity(entity, resolved_id, index)
            for index, entity in enumerate(modelspace)
        ]
        type_counts = Counter(entity.entity_type for entity in entities)
        supported_count = sum(
            entity.mapping_status == "supported" for entity in entities
        )
        insertion_units_code = int(document.header.get("$INSUNITS", 0))

        return CADDocument(
            document_id=resolved_id,
            filename=source.name,
            version=document.dxfversion,
            units=units.decode(insertion_units_code),
            layers=[self._map_layer(layer) for layer in document.layers],
            statistics=CADStatistics(
                total_entities=len(entities),
                supported_entities=supported_count,
                unsupported_entities=len(entities) - supported_count,
                entity_types=dict(sorted(type_counts.items())),
            ),
            metadata={
                "source_path": str(source),
                "acad_release": document.acad_release,
                "encoding": document.encoding,
                "insertion_units_code": insertion_units_code,
                "measurement_system": document.header.get("$MEASUREMENT"),
                "linear_units_format": document.header.get("$LUNITS"),
                "linear_units_precision": document.header.get("$LUPREC"),
                "angular_units_format": document.header.get("$AUNITS"),
                "dwg_codepage": document.header.get("$DWGCODEPAGE"),
                "layouts": [layout.name for layout in document.layouts],
                "paperspace_entity_count": sum(
                    len(layout) for layout in document.layouts if layout.name != "Model"
                ),
                "block_definitions": [block.name for block in document.blocks],
                "recovered": recovered,
                "audit_errors": audit_errors,
                "audit_fixes": audit_fixes,
            },
            entities=entities,
        )

    def read_document(
        self,
        path: str | Path,
        document_id: str | None = None,
    ) -> CADDocument:
        """Compatibility alias with other SDTL document readers."""

        return self.read(path, document_id=document_id)

    @staticmethod
    def _map_layer(layer: object) -> CADLayer:
        return CADLayer(
            name=layer.dxf.name,
            color=layer.dxf.get("color"),
            linetype=layer.dxf.get("linetype"),
            lineweight=layer.dxf.get("lineweight"),
            is_off=layer.is_off(),
            is_frozen=layer.is_frozen(),
            is_locked=layer.is_locked(),
        )
