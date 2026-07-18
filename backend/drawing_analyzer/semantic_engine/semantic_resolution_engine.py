from __future__ import annotations

from collections.abc import Mapping, Sequence
import unicodedata
from typing import Any

from ..dimension_entity import DimensionEntity
from ..dimension_topology_analyzer import DimensionTopology
from ..geometry_features import GeometryFeature
from .candidate_confidence import CandidateConfidence, CandidateConfidenceCalculator
from .text_geometry_relation import TextGeometryRelation


class SemanticResolutionEngine:
    """Evaluate catalog rules against geometric, textual, dimensional, and topology evidence."""

    def __init__(
        self,
        confidence_calculator: CandidateConfidenceCalculator | None = None,
    ) -> None:
        self.confidence_calculator = (
            confidence_calculator or CandidateConfidenceCalculator()
        )

    def evaluate(
        self,
        feature: GeometryFeature,
        catalog_element: Mapping[str, Any],
        text_relations: Sequence[TextGeometryRelation] = (),
        dimensions: Sequence[DimensionEntity] = (),
        topologies: Sequence[DimensionTopology] = (),
    ) -> CandidateConfidence | None:
        rules = catalog_element.get("rules", {})
        if not isinstance(rules, Mapping) or not self._geometry_matches(feature, rules):
            return None

        related_text = [
            relation
            for relation in text_relations
            if relation.geometry_id == feature.source_geometry
        ]
        text_patterns = rules.get("text_patterns", [])
        text_match = self._text_match(related_text, text_patterns)

        related_topologies = [
            topology
            for topology in topologies
            if topology.target_geometry_id == feature.source_geometry
        ]
        topology_dimension_ids = {
            topology.dimension_id for topology in related_topologies
        }
        related_dimensions = [
            dimension
            for dimension in dimensions
            if dimension.geometry_reference_id == feature.source_geometry
            or dimension.dimension_id in topology_dimension_ids
        ]

        if rules.get("dimension_required") and not related_dimensions:
            return None

        dimension_match = 1.0 if related_dimensions else 0.0
        topology_match = (
            max(topology.confidence for topology in related_topologies)
            if related_topologies
            else 0.0
        )
        return self.confidence_calculator.calculate(
            geometry_match=1.0,
            text_match=text_match,
            dimension_match=dimension_match,
            topology_match=topology_match,
        )

    def matching_text_relations(
        self,
        feature: GeometryFeature,
        catalog_element: Mapping[str, Any],
        relations: Sequence[TextGeometryRelation],
    ) -> list[TextGeometryRelation]:
        rules = catalog_element.get("rules", {})
        patterns = rules.get("text_patterns", []) if isinstance(rules, Mapping) else []
        normalized_patterns = [self._normalize(str(pattern)) for pattern in patterns]
        return [
            relation
            for relation in relations
            if relation.geometry_id == feature.source_geometry
            and any(
                pattern in self._normalize(relation.text)
                for pattern in normalized_patterns
            )
        ]

    def _geometry_matches(
        self,
        feature: GeometryFeature,
        rules: Mapping[str, Any],
    ) -> bool:
        geometry_rule = str(rules.get("geometry", ""))
        properties = feature.properties
        closed = bool(properties.get("closed"))
        aspect_ratio = properties.get("aspect_ratio")
        area = float(properties.get("area") or 0.0)

        if geometry_rule == "closed_rectangle":
            matched = feature.type == "rectangle" and closed
        elif geometry_rule == "long_rectangle":
            matched = feature.type == "rectangle" and closed
        elif geometry_rule == "rectangle":
            matched = feature.type == "rectangle"
        elif geometry_rule == "long_open_polyline":
            matched = feature.type in {"line", "polygon"} and not closed
        elif geometry_rule == "large_polygon":
            matched = feature.type in {"polygon", "rectangle"} and closed
        else:
            return False

        if not matched:
            return False

        minimum_aspect = rules.get("aspect_ratio_min")
        if minimum_aspect is not None:
            if geometry_rule == "long_open_polyline" and feature.type == "line":
                if float(properties.get("length") or 0.0) < float(minimum_aspect):
                    return False
            elif aspect_ratio is None or float(aspect_ratio) < float(minimum_aspect):
                return False

        width_range = rules.get("width_range")
        if isinstance(width_range, list) and len(width_range) == 2:
            width = float(properties.get("width") or 0.0)
            if not float(width_range[0]) <= width <= float(width_range[1]):
                return False

        area_min = rules.get("area_min")
        if area_min is not None and area < float(area_min):
            return False
        return True

    def _text_match(
        self,
        relations: Sequence[TextGeometryRelation],
        patterns: Any,
    ) -> float:
        if not isinstance(patterns, list) or not patterns:
            return 0.0
        normalized_patterns = [self._normalize(str(pattern)) for pattern in patterns]
        matching_confidences = [
            relation.confidence
            for relation in relations
            if any(
                pattern in self._normalize(relation.text)
                for pattern in normalized_patterns
            )
        ]
        return max(matching_confidences, default=0.0)

    def _normalize(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value.upper())
        return "".join(character for character in normalized if not unicodedata.combining(character))
