from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz


class PDFDocumentReader:
    """Read structural and availability information from engineering PDF files."""

    def read_document(self, path: str | Path) -> dict[str, Any]:
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

            page_sizes: list[dict[str, int | float]] = []
            text_available = False
            image_count = 0

            for page_number, page in enumerate(document, start=1):
                page_sizes.append(
                    {
                        "page": page_number,
                        "width": float(page.rect.width),
                        "height": float(page.rect.height),
                    }
                )
                text_available = text_available or bool(page.get_text("text").strip())
                image_count += len(page.get_images(full=True))

            metadata = {
                key: value
                for key, value in (document.metadata or {}).items()
                if value not in (None, "")
            }

            return {
                "path": str(source),
                "page_count": document.page_count,
                "page_sizes": page_sizes,
                "text_available": text_available,
                "images_available": image_count > 0,
                "image_count": image_count,
                "metadata": metadata,
            }
