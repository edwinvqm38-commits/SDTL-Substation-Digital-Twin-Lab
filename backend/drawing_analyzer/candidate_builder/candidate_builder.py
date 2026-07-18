from __future__ import annotations

from collections.abc import Sequence
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..dimension_entity import DimensionEntity
from ..dimension_topology_analyzer import DimensionTopology
from ..geometry_features import GeometryFeature
from ..semantic_engine import SemanticResolutionEngine, TextGeometryRelation
from ..traceability_map import TraceabilityMap
from .engineering_candidate import EngineeringCandidate


class CandidateBuilder:
    """Build evidence-backed semantic candidates from features and catalog rules."""

    def __init__(
        self,
        semantic_engine: SemanticResolutionEngine | None = None,
        catalog_paths: Sequence[str | Path] | None = None,
    ) -> None:
        self.semantic_engine = semantic_engine or SemanticResolutionEngine()
        catalog_directory = Path(__file__).parents[1] / "engineering_catalog"
        self.catalog_paths = list(catalog_paths) if catalog_paths is not None else [
            catalog_directory / "civil_elements.json",
            catalog_directory / "electrical_elements.json",
            catalog_directory / "structural_elements.json",
        ]

    def build_candidates(
        self,
        features: Sequence[GeometryFeature],
        text_relations: Sequence[TextGeometryRelation] = (),
        dimensions: Sequence[DimensionEntity] = (),
        topologies: Sequence[DimensionTopology] = (),
        traceability: Sequence[TraceabilityMap] = (),
    ) -> list[EngineeringCandidate]:
        catalog_elements = self._load_catalog_elements()
        candidates: list[EngineeringCandidate] = []

        for feature in features:
            for element in catalog_elements:
                confidence = self.semantic_engine.evaluate(
                    feature=feature,
                    catalog_element=element,
                    text_relations=text_relations,
                    dimensions=dimensions,
                    topologies=topologies,
                )
                if confidence is None:
                    continue

                matching_text = self.semantic_engine.matching_text_relations(
                    feature,
                    element,
                    text_relations,
                )
                related_topologies = [
                    topology
                    for topology in topologies
                    if topology.target_geometry_id == feature.source_geometry
                ]
                related_dimension_ids = {
                    topology.dimension_id for topology in related_topologies
                }
                related_dimensions = [
                    dimension
                    for dimension in dimensions
                    if dimension.geometry_reference_id == feature.source_geometry
                    or dimension.dimension_id in related_dimension_ids
                ]
                evidence: list[dict[str, Any]] = [
                    {
                        "type": "geometry_match",
                        "value": feature.type,
                        "feature_id": feature.id,
                    }
                ]
                evidence.extend(
                    {
                        "type": "text_match",
                        "value": relation.text,
                        "relation_id": relation.id,
                    }
                    for relation in matching_text
                )
                evidence.extend(
                    {
                        "type": "dimension_match",
                        "value": dimension.dimension_id,
                        "unit": dimension.unit,
                    }
                    for dimension in related_dimensions
                )
                evidence.extend(
                    {
                        "type": "topology_match",
                        "value": topology.id,
                        "valid": topology.valid,
                    }
                    for topology in related_topologies
                )

                source_traceability = next(
                    (
                        record
                        for record in traceability
                        if record.geometry_id == feature.source_geometry
                    ),
                    None,
                )
                candidates.append(
                    EngineeringCandidate(
                        id=f"CAND-{uuid4().hex}",
                        possible_type=str(element["type"]),
                        confidence=confidence.final,
                        source_geometry=[feature.source_geometry],
                        evidence=evidence,
                        scores=confidence.model_dump(),
                        traceability=(
                            source_traceability.model_dump(mode="json")
                            if source_traceability is not None
                            else {
                                "document_id": feature.metadata.get("document_id"),
                                "page": feature.metadata.get("page_number"),
                            }
                        ),
                        metadata={
                            "catalog_code": element.get("code"),
                            "catalog_version": element.get("catalog_version"),
                            "feature_id": feature.id,
                        },
                    )
                )
        return candidates

    def _load_catalog_elements(self) -> list[dict[str, Any]]:
        elements: list[dict[str, Any]] = []
        for path_value in self.catalog_paths:
            path = Path(path_value)
            with path.open(encoding="utf-8") as catalog_file:
                payload = json.load(catalog_file)
            for element in payload.get("elements", []):
                item = dict(element)
                item["catalog_version"] = payload.get("version")
                elements.append(item)
        return elements
