from __future__ import annotations

from collections.abc import Sequence
import re
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .text_geometry import ExtractedText


class ScaleInformation(BaseModel):
    """Drawing scale extracted from located PDF text using an explicit ratio."""

    model_config = ConfigDict(extra="forbid")

    scale_id: str
    document_id: str
    page_number: int
    numerator: int
    denominator: int
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class DrawingScale(BaseModel):
    """Normalized drawing-scale ratio with optional units and PDF traceability."""

    model_config = ConfigDict(extra="forbid")

    scale_id: str = Field(default_factory=lambda: f"DS-{uuid4().hex}")
    document_id: str | None = None
    page_number: int | None = None
    scale_type: str = "ratio"
    paper_units: float
    real_units: float
    unit: str | None = None
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScaleDetector:
    """Detect labeled or standalone drawing-scale ratios using regular expressions."""

    _LABELED_SCALE = re.compile(
        r"\b(?P<label>ESCALA|E|S)\s*(?:[:=]\s*)?"
        r"(?P<numerator>\d+)\s*[:/]\s*(?P<denominator>\d+)\b",
        re.IGNORECASE,
    )
    _STANDALONE_SCALE = re.compile(
        r"^\s*(?P<numerator>\d+)\s*[:/]\s*(?P<denominator>\d+)\s*$"
    )

    def detect_scales(
        self,
        texts: Sequence[ExtractedText],
    ) -> list[ScaleInformation]:
        scales: list[ScaleInformation] = []

        for text in texts:
            matches = list(self._LABELED_SCALE.finditer(text.content))
            if matches:
                for match in matches:
                    scale = self._build_scale(text, match, confidence=0.98)
                    if scale is not None:
                        scales.append(scale)
                continue

            standalone_match = self._STANDALONE_SCALE.fullmatch(text.content)
            if standalone_match:
                scale = self._build_scale(
                    text,
                    standalone_match,
                    confidence=0.80,
                )
                if scale is not None:
                    scales.append(scale)

        return scales

    def detect_drawing_scales(
        self,
        texts: Sequence[ExtractedText],
        unit: str | None = None,
    ) -> list[DrawingScale]:
        """Return v1.6.5 drawing-scale models while preserving the v1.4 API."""

        return [
            DrawingScale(
                document_id=scale.document_id,
                page_number=scale.page_number,
                paper_units=float(scale.numerator),
                real_units=float(scale.denominator),
                unit=unit,
                confidence=scale.confidence,
                metadata=dict(scale.metadata),
            )
            for scale in self.detect_scales(texts)
        ]

    def _build_scale(
        self,
        text: ExtractedText,
        match: re.Match[str],
        confidence: float,
    ) -> ScaleInformation | None:
        numerator = int(match.group("numerator"))
        denominator = int(match.group("denominator"))
        if numerator <= 0 or denominator <= 0:
            return None

        label = match.groupdict().get("label")
        return ScaleInformation(
            scale_id=f"SCL-{uuid4().hex}",
            document_id=text.document_id,
            page_number=text.page_number,
            numerator=numerator,
            denominator=denominator,
            confidence=confidence,
            metadata={
                "text_source_id": text.text_id,
                "matched_text": match.group(0),
                "source_content": text.content,
                "label": label.upper() if label else None,
            },
        )
