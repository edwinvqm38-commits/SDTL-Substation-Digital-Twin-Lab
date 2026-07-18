from __future__ import annotations

from pathlib import Path

import fitz

from .coordinate_extractor import CoordinateTextExtractor
from .text_geometry import ExtractedText


class PDFTextExtractor:
    """Extract PDF text page by page while preserving one-based page references."""

    def extract_text(self, path: str | Path) -> list[dict[str, int | str]]:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"PDF document not found: {source}")

        try:
            document = fitz.open(source)
        except (fitz.FileDataError, RuntimeError) as exc:
            raise ValueError(f"Unable to open PDF document: {source}") from exc

        with document:
            if not document.is_pdf:
                raise ValueError(f"Document is not a PDF file: {source}")
            if document.needs_pass:
                raise ValueError(f"PDF document requires a password: {source}")

            return [
                {"page": page_number, "text": page.get_text("text")}
                for page_number, page in enumerate(document, start=1)
            ]

    def extract_text_with_coordinates(
        self,
        path: str | Path,
        document_id: str | None = None,
    ) -> list[ExtractedText]:
        """Extract native PDF text spans with page coordinates and typography."""

        return CoordinateTextExtractor().extract_text(path, document_id=document_id)
