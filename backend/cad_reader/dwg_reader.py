from __future__ import annotations

from pathlib import Path
import tempfile

from .cad_metadata import CADDocument
from .dwg_converter import DWGConverter
from .dxf_reader import DXFReader


class DWGReader:
    """Read a DWG file's modelspace via ODA File Converter + DXFReader.

    Exposes the same .read()/.read_document() interface as DXFReader so a
    caller can accept either format transparently; the DWG is converted to a
    temporary DXF and then handed to the existing, already-tested DXFReader
    -- this class adds no DWG-specific parsing of its own.
    """

    def __init__(
        self,
        converter: DWGConverter | None = None,
        dxf_reader: DXFReader | None = None,
    ) -> None:
        self.converter = converter or DWGConverter()
        self.dxf_reader = dxf_reader or DXFReader()

    @property
    def is_available(self) -> bool:
        return self.converter.is_available

    def read(
        self,
        path: str | Path,
        document_id: str | None = None,
    ) -> CADDocument:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"DWG document not found: {source}")

        with tempfile.TemporaryDirectory() as output_dir:
            dxf_path = self.converter.convert(source, output_dir)
            document = self.dxf_reader.read(dxf_path, document_id=document_id or source.stem)

        document.filename = source.name
        document.metadata["source_path"] = str(source)
        document.metadata["converted_from_dwg"] = True
        return document

    def read_document(
        self,
        path: str | Path,
        document_id: str | None = None,
    ) -> CADDocument:
        """Compatibility alias matching DXFReader.read_document()."""

        return self.read(path, document_id=document_id)
