from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import fitz

from .text_geometry import ExtractedText


class CoordinateTextExtractor:
    """Extract native PDF text spans with coordinates and typography using PyMuPDF."""

    def extract_text(
        self,
        path: str | Path,
        document_id: str | None = None,
    ) -> list[ExtractedText]:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"PDF document not found: {source}")

        try:
            document = fitz.open(source)
        except (fitz.FileDataError, RuntimeError) as exc:
            raise ValueError(f"Unable to open PDF document: {source}") from exc

        resolved_document_id = document_id if document_id is not None else source.stem

        with document:
            if not document.is_pdf:
                raise ValueError(f"Document is not a PDF file: {source}")
            if document.needs_pass:
                raise ValueError(f"PDF document requires a password: {source}")

            extracted: list[ExtractedText] = []
            for page_number, page in enumerate(document, start=1):
                page_data = page.get_text("dict")
                extracted.extend(
                    self._extract_page_spans(
                        page_data=page_data,
                        page_number=page_number,
                        document_id=resolved_document_id,
                    )
                )
            return extracted

    def _extract_page_spans(
        self,
        page_data: dict[str, Any],
        page_number: int,
        document_id: str,
    ) -> list[ExtractedText]:
        extracted: list[ExtractedText] = []

        for block in page_data.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    content = str(span.get("text", "")).strip()
                    bbox = span.get("bbox")
                    if not content or not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                        continue

                    x0, y0, x1, y1 = (float(value) for value in bbox)
                    font_size = span.get("size")
                    font_name = span.get("font")

                    extracted.append(
                        ExtractedText(
                            text_id=f"TXT-{uuid4().hex}",
                            document_id=document_id,
                            page_number=page_number,
                            content=content,
                            x=x0,
                            y=y0,
                            width=max(0.0, x1 - x0),
                            height=max(0.0, y1 - y0),
                            font_size=(
                                float(font_size)
                                if isinstance(font_size, (int, float))
                                else None
                            ),
                            font_name=str(font_name) if font_name else None,
                            confidence=1.0,
                        )
                    )

        return extracted
