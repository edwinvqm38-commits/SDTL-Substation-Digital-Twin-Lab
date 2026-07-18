from __future__ import annotations

from collections.abc import Sequence
import re
from uuid import uuid4

from .dimension_entity import DimensionEntity
from .text_geometry import ExtractedText


class DimensionDetector:
    """Detect dimensional values in located PDF text using explicit regular-expression rules."""

    _DIAMETER = re.compile(
        r"[Øø⌀]\s*(?P<value>\d+(?:[.,]\d+)?)"
        r"(?:\s*(?P<unit>mm|cm|m))?\b",
        re.IGNORECASE,
    )
    _NPT_LEVEL = re.compile(
        r"\bNPT\s*(?P<value>[+-]\s*\d+(?:[.,]\d+)?)\b",
        re.IGNORECASE,
    )
    _SIGNED_LEVEL = re.compile(
        r"(?<![A-Za-z0-9])(?P<value>[+-]\s*\d+(?:[.,]\d+)?)\b"
    )
    _ANGLE = re.compile(r"(?P<value>\d+(?:[.,]\d+)?)\s*°")
    _LINEAR = re.compile(
        r"(?<![A-Za-z0-9_.])(?P<value>\d+(?:[.,]\d+)?)\s*"
        r"(?P<unit>mm|cm|km|m)\b",
        re.IGNORECASE,
    )
    _NUMERIC = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")

    def detect_dimensions(
        self,
        texts: Sequence[ExtractedText],
    ) -> list[DimensionEntity]:
        dimensions: list[DimensionEntity] = []

        for text in texts:
            detected_ranges: list[tuple[int, int]] = []
            rules = (
                (self._DIAMETER, "diameter", 0.90, "diameter_symbol"),
                (self._NPT_LEVEL, "level", 0.95, "npt_level"),
                (self._SIGNED_LEVEL, "level", 0.85, "signed_level"),
                (self._ANGLE, "angle", 0.90, "degree_symbol"),
                (self._LINEAR, "linear", 0.95, "explicit_unit"),
            )

            for pattern, dimension_type, confidence, rule_name in rules:
                for match in pattern.finditer(text.content):
                    if self._overlaps(match.span(), detected_ranges):
                        continue

                    unit = match.groupdict().get("unit")
                    if dimension_type == "angle":
                        unit = "deg"

                    dimensions.append(
                        self._build_dimension(
                            text=text,
                            dimension_type=dimension_type,
                            value=self._parse_value(match.group("value")),
                            unit=unit.lower() if unit else None,
                            confidence=confidence,
                            matched_text=match.group(0),
                            rule_name=rule_name,
                        )
                    )
                    detected_ranges.append(match.span())

            stripped_content = text.content.strip()
            if not detected_ranges and self._NUMERIC.fullmatch(stripped_content):
                dimensions.append(
                    self._build_dimension(
                        text=text,
                        dimension_type="unknown",
                        value=self._parse_value(stripped_content),
                        unit=None,
                        confidence=0.60,
                        matched_text=stripped_content,
                        rule_name="standalone_numeric",
                    )
                )

        return dimensions

    def _build_dimension(
        self,
        text: ExtractedText,
        dimension_type: str,
        value: float,
        unit: str | None,
        confidence: float,
        matched_text: str,
        rule_name: str,
    ) -> DimensionEntity:
        return DimensionEntity(
            dimension_id=f"DIM-{uuid4().hex}",
            document_id=text.document_id,
            page_number=text.page_number,
            dimension_type=dimension_type,
            value=value,
            unit=unit,
            text_source_id=text.text_id,
            geometry_reference_id=None,
            confidence=confidence,
            metadata={
                "rule": rule_name,
                "matched_text": matched_text,
                "source_content": text.content,
                "text_bbox": {
                    "x": text.x,
                    "y": text.y,
                    "width": text.width,
                    "height": text.height,
                },
            },
        )

    def _parse_value(self, value: str) -> float:
        return float(value.replace(" ", "").replace(",", "."))

    def _overlaps(
        self,
        candidate: tuple[int, int],
        detected: list[tuple[int, int]],
    ) -> bool:
        return any(
            candidate[0] < existing[1] and candidate[1] > existing[0]
            for existing in detected
        )
