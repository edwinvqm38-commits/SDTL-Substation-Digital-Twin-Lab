from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .arrow_detector import ArrowDetector
from .dimension_entity import DimensionEntity
from .dimension_geometry_link import DimensionGeometryLink
from .extension_line_detector import ExtensionLineDetector
from .geometry_entity import GeometryEntity


class DimensionTopology(BaseModel):
    """Validated geometric structure of a dimension and its target relation."""

    model_config = ConfigDict(extra="forbid")

    id: str
    dimension_id: str
    dimension_line: str | None = None
    extension_lines: list[str] = Field(default_factory=list)
    arrow_heads: list[str] = Field(default_factory=list)
    orientation: str | None = None
    target_geometry_id: str | None = None
    valid: bool
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class DimensionTopologyAnalyzer:
    """Validate dimension-line, extension-line, arrow, and target topology."""

    def __init__(
        self,
        extension_line_detector: ExtensionLineDetector | None = None,
        arrow_detector: ArrowDetector | None = None,
    ) -> None:
        self.extension_line_detector = extension_line_detector or ExtensionLineDetector()
        self.arrow_detector = arrow_detector or ArrowDetector()

    def analyze(
        self,
        dimension: DimensionEntity,
        link: DimensionGeometryLink,
        geometries: Sequence[GeometryEntity],
    ) -> DimensionTopology:
        geometries_by_id = {geometry.geometry_id: geometry for geometry in geometries}
        dimension_line = geometries_by_id.get(link.dimension_line_id)
        target_exists = link.target_geometry_id in geometries_by_id

        if dimension_line is None:
            return DimensionTopology(
                id=f"DT-{uuid4().hex}",
                dimension_id=dimension.dimension_id,
                dimension_line=link.dimension_line_id,
                target_geometry_id=link.target_geometry_id,
                valid=False,
                confidence=0.0,
                metadata={"reason": "dimension_line_not_found"},
            )

        extension_lines = self.extension_line_detector.detect_extension_lines(
            dimension_line,
            geometries,
        )
        arrow_detections = self.arrow_detector.detect_arrows(
            dimension_line,
            geometries,
        )
        orientation = self._orientation(dimension_line)

        has_line = orientation is not None
        has_extensions = len(extension_lines) >= 2
        has_target = target_exists and link.target_geometry_id is not None
        valid = has_line and has_extensions and has_target

        confidence = 0.0
        confidence += 0.20 if has_line else 0.0
        confidence += 0.15 if orientation is not None else 0.0
        confidence += 0.25 if has_extensions else 0.0
        confidence += 0.20 if has_target else 0.0
        confidence += 0.16 if len(arrow_detections) >= 2 else 0.08 * len(
            arrow_detections
        )

        return DimensionTopology(
            id=f"DT-{uuid4().hex}",
            dimension_id=dimension.dimension_id,
            dimension_line=dimension_line.geometry_id,
            extension_lines=extension_lines,
            arrow_heads=[arrow.geometry_id for arrow in arrow_detections],
            orientation=orientation,
            target_geometry_id=link.target_geometry_id,
            valid=valid,
            confidence=round(min(confidence, 1.0), 4),
            metadata={
                "document_id": dimension.document_id,
                "page_number": dimension.page_number,
                "checks": {
                    "dimension_line_valid": has_line,
                    "two_extension_lines": has_extensions,
                    "target_geometry_exists": has_target,
                    "arrow_heads_detected": len(arrow_detections),
                },
                "extension_detection": dict(self.extension_line_detector.metadata),
                "arrow_detections": [
                    arrow.model_dump(mode="json") for arrow in arrow_detections
                ],
                "source_link_id": link.link_id,
            },
        )

    def _orientation(self, geometry: GeometryEntity) -> str | None:
        start = geometry.coordinates.get("start")
        end = geometry.coordinates.get("end")
        if not isinstance(start, Mapping) or not isinstance(end, Mapping):
            return None
        try:
            delta_x = abs(float(end["x"]) - float(start["x"]))
            delta_y = abs(float(end["y"]) - float(start["y"]))
        except (KeyError, TypeError, ValueError):
            return None
        if delta_x == 0 and delta_y == 0:
            return None
        return "horizontal" if delta_x >= delta_y else "vertical"
