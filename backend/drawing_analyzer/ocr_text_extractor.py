from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import fitz
from PIL import Image
import pytesseract

from .text_geometry import ExtractedText


class OCRTextExtractor:
    """Recover text from PDF pages whose text was flattened to vector
    outlines by the CAD plot driver instead of kept as real PDF text (no
    embedded fonts at all -- confirmed to be the case for every real
    AutoCAD-plotted drawing tested so far in this project, where
    PDFTextExtractor returns zero characters despite tens of thousands of
    vector paths).

    Renders each page to a raster image and runs Tesseract, grouping
    recognized words back into per-line entries (matching PyMuPDF's own
    per-span granularity) so a multi-token callout like "8 m" or
    "ESCALA 1:50" stays in one ExtractedText.content string -- exactly what
    DimensionDetector/ScaleDetector already expect from PDFTextExtractor.
    """

    def __init__(
        self,
        dpi: int = 300,
        lang: str = "spa+eng",
        min_confidence: int = 40,
    ) -> None:
        if dpi <= 0:
            raise ValueError("dpi must be greater than zero")
        self.dpi = dpi
        self.lang = lang
        self.min_confidence = min_confidence

    def extract_text(
        self,
        path: str | Path,
        document_id: str | None = None,
    ) -> list[ExtractedText]:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"PDF document not found: {source}")

        resolved_document_id = document_id if document_id is not None else source.stem
        zoom = self.dpi / 72

        with fitz.open(source) as document:
            extracted: list[ExtractedText] = []
            for page_number, page in enumerate(document, start=1):
                pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                extracted.extend(
                    self._extract_page(image, zoom, resolved_document_id, page_number)
                )
            return extracted

    def _extract_page(
        self,
        image: Image.Image,
        zoom: float,
        document_id: str,
        page_number: int,
    ) -> list[ExtractedText]:
        data = pytesseract.image_to_data(
            image, lang=self.lang, output_type=pytesseract.Output.DICT
        )
        lines: dict[tuple[int, int, int], dict] = {}

        for index in range(len(data["text"])):
            word = data["text"][index].strip()
            try:
                confidence = int(data["conf"][index])
            except (TypeError, ValueError):
                confidence = -1
            if not word or confidence < self.min_confidence:
                continue

            key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
            x, y, w, h = (
                data["left"][index],
                data["top"][index],
                data["width"][index],
                data["height"][index],
            )
            line = lines.setdefault(
                key,
                {"words": [], "confidences": [], "x0": x, "y0": y, "x1": x + w, "y1": y + h},
            )
            line["words"].append((data["word_num"][index], word))
            line["confidences"].append(confidence)
            line["x0"] = min(line["x0"], x)
            line["y0"] = min(line["y0"], y)
            line["x1"] = max(line["x1"], x + w)
            line["y1"] = max(line["y1"], y + h)

        extracted: list[ExtractedText] = []
        for line in lines.values():
            content = " ".join(word for _, word in sorted(line["words"]))
            average_confidence = sum(line["confidences"]) / len(line["confidences"])
            extracted.append(
                ExtractedText(
                    text_id=f"TXT-{uuid4().hex}",
                    document_id=document_id,
                    page_number=page_number,
                    content=content,
                    x=line["x0"] / zoom,
                    y=line["y0"] / zoom,
                    width=(line["x1"] - line["x0"]) / zoom,
                    height=(line["y1"] - line["y0"]) / zoom,
                    confidence=round(min(average_confidence / 100, 1.0), 3),
                )
            )
        return extracted
