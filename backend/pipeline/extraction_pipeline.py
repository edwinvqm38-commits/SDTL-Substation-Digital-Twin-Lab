from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.drawing_analyzer import (
    CandidateBuilder,
    DimensionDetector,
    DimensionGeometryAssociationEngine,
    DimensionTargetResolutionEngine,
    DimensionTopologyAnalyzer,
    EngineeringCandidate,
    GeometryEntity,
    GeometryFeatureExtractor,
    PDFTextExtractor,
    SpatialAssociationEngine,
    TextGeometryRelationEngine,
    TraceabilityMap,
    VectorGeometryExtractor,
)
from backend.drawing_analyzer.dimension_topology_analyzer import DimensionTopology
from backend.drawing_analyzer.semantic_engine import LLMFallbackClassifier
from backend.drawing_analyzer.semantic_engine.text_geometry_relation import (
    TextGeometryRelation,
)
from backend.object_generation import ObjectValidator, SDTLObjectFactory
from backend.sdtl_core.entities import CivilObject

from .dimension_resolver import DimensionResolver

# Mirrors backend/sdtl_catalog/civil_objects.json's candidate_type values.
# Used only to tell the (optional) LLM fallback which labels are valid
# answers -- it never invents a type outside this catalog.
_KNOWN_CANDIDATE_TYPES = ["electrical_room", "cable_trench", "foundation", "fence", "road"]


@dataclass
class SkippedCandidate:
    """A candidate that could not become a reviewable SDTL object, and why."""

    candidate_id: str
    possible_type: str
    confidence: float
    reason: str
    ai_suggested_type: str | None = None
    ai_model: str | None = None


@dataclass
class ExtractionResult:
    source_pdf: str
    objects: list[CivilObject] = field(default_factory=list)
    skipped: list[SkippedCandidate] = field(default_factory=list)
    statistics: dict[str, int] = field(default_factory=dict)


class DrawingToObjectsPipeline:
    """Chain the existing extraction, semantic, and object-generation stages
    into one traceable PDF -> reviewable SDTL object flow.

    This stage never activates an object: every CivilObject it returns is in
    "proposal" state and still requires a human `.approve(reviewer)` (see
    ReviewQueue) before ThreeDGenerationStage will accept it.
    """

    def __init__(
        self,
        dimension_resolver: DimensionResolver | None = None,
        llm_classifier: LLMFallbackClassifier | None = None,
    ) -> None:
        self.dimension_resolver = dimension_resolver or DimensionResolver()
        self.factory = SDTLObjectFactory()
        self.validator = ObjectValidator()
        self.llm_classifier = llm_classifier or LLMFallbackClassifier()

    def run(self, pdf_path: str | Path) -> ExtractionResult:
        pdf = Path(pdf_path)
        if not pdf.exists():
            raise FileNotFoundError(pdf)

        geometries = self._deduplicate_lines(
            VectorGeometryExtractor().extract_geometry(str(pdf))
        )
        texts = PDFTextExtractor().extract_text_with_coordinates(str(pdf))
        dimensions = DimensionDetector().detect_dimensions(texts)
        dimensions_by_id = {dimension.dimension_id: dimension for dimension in dimensions}

        spatial_relations = SpatialAssociationEngine().associate(texts, geometries)
        dimension_associations = DimensionGeometryAssociationEngine().associate(
            dimensions, geometries, spatial_relations
        )
        dimension_links = DimensionTargetResolutionEngine().resolve(
            dimensions, dimension_associations, geometries, spatial_relations
        )

        topology_analyzer = DimensionTopologyAnalyzer()
        topologies: list[DimensionTopology] = [
            topology_analyzer.analyze(dimensions_by_id[link.dimension_id], link, geometries)
            for link in dimension_links
            if link.dimension_id in dimensions_by_id
        ]

        features = GeometryFeatureExtractor().extract_features(
            geometries, texts=texts, dimensions=dimensions
        )
        text_relations = TextGeometryRelationEngine().relate(texts, geometries)
        traceability = [
            TraceabilityMap(
                source_pdf=pdf.name,
                page=geometry.page_number,
                geometry_id=geometry.geometry_id,
                coordinates=self._bounds_as_coordinates(geometry),
            )
            for geometry in geometries
        ]

        candidates = CandidateBuilder().build_candidates(
            features,
            text_relations=text_relations,
            dimensions=dimensions,
            topologies=topologies,
            traceability=traceability,
        )

        result = ExtractionResult(source_pdf=pdf.name)
        for candidate in candidates:
            validation = self.validator.validate(candidate)
            if not validation["valid"]:
                checks = validation["checks"]
                failed = [name for name, ok in checks.items() if not ok]
                skipped = SkippedCandidate(
                    candidate_id=candidate.id,
                    possible_type=candidate.possible_type,
                    confidence=candidate.confidence,
                    reason=f"failed checks: {', '.join(failed)}",
                )
                # Only ask the (optional) LLM when geometry/traceability are
                # sound and the sole problem is that no catalog text pattern
                # matched -- that is the one failure mode a short label
                # classification can plausibly help with.
                if failed == ["semantic"]:
                    self._attach_llm_suggestion(skipped, candidate, text_relations)
                result.skipped.append(skipped)
                continue

            proposal = self.factory.create_proposal(candidate)
            civil_object = self.factory.create_object(proposal)
            # Carry the drawing's own text labels (e.g. "SALA ELECTRICA",
            # "BASE E-01") onto the object so ProjectCrossReferenceEngine can
            # later match the same real-world element across other plans of
            # the same project (electrical/civil/architectural) without
            # needing a shared coordinate system between sheets.
            civil_object.properties = {
                **civil_object.properties,
                "matched_labels": [
                    item["value"]
                    for item in candidate.evidence
                    if item.get("type") == "text_match"
                ],
            }
            related_topologies = [
                topology
                for topology in topologies
                if topology.target_geometry_id == civil_object.source_geometry
            ]
            self.dimension_resolver.resolve(
                civil_object,
                dimensions_by_id=dimensions_by_id,
                topologies=related_topologies,
            )
            result.objects.append(civil_object)

        result.statistics = {
            "geometries": len(geometries),
            "texts": len(texts),
            "dimensions": len(dimensions),
            "dimension_links_resolved": sum(
                1 for link in dimension_links if link.target_geometry_id
            ),
            "candidates": len(candidates),
            "objects_created": len(result.objects),
            "objects_skipped": len(result.skipped),
        }
        return result

    def _attach_llm_suggestion(
        self,
        skipped: SkippedCandidate,
        candidate: EngineeringCandidate,
        text_relations: list[TextGeometryRelation],
    ) -> None:
        """Ask the (optional) LLM fallback to classify the text nearest this
        candidate's geometry, and record its answer for a human to confirm.
        A no-op whenever no provider is configured (the default)."""

        if not self.llm_classifier.is_configured or not candidate.source_geometry:
            return

        nearby = [
            relation
            for relation in text_relations
            if relation.geometry_id == candidate.source_geometry[0]
        ]
        if not nearby:
            return

        best_text = max(nearby, key=lambda relation: relation.confidence).text
        suggestion = self.llm_classifier.classify_label(best_text, _KNOWN_CANDIDATE_TYPES)
        if suggestion is None:
            return

        skipped.ai_suggested_type = suggestion.object_type
        skipped.ai_model = f"{suggestion.provider}:{suggestion.model}"

    @staticmethod
    def _deduplicate_lines(geometries: list[GeometryEntity]) -> list[GeometryEntity]:
        """Collapse duplicate line paths that PDF renderers commonly emit for a
        single stroked segment (forward and backward), which would otherwise
        make coincident lines outscore the real target geometry during
        dimension-target resolution.
        """

        seen: set[tuple[str, int, tuple[float, float], tuple[float, float]]] = set()
        deduplicated: list[GeometryEntity] = []
        for geometry in geometries:
            if geometry.entity_type != "line":
                deduplicated.append(geometry)
                continue

            start, end = geometry.coordinates.get("start"), geometry.coordinates.get("end")
            if not isinstance(start, dict) or not isinstance(end, dict):
                deduplicated.append(geometry)
                continue

            point_a = (round(start["x"], 3), round(start["y"], 3))
            point_b = (round(end["x"], 3), round(end["y"], 3))
            key = (
                geometry.document_id,
                geometry.page_number,
                *sorted([point_a, point_b]),
            )
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(geometry)
        return deduplicated

    @staticmethod
    def _bounds_as_coordinates(geometry: GeometryEntity) -> list[list[float]]:
        coordinates = geometry.coordinates
        bbox = coordinates.get("bounding_box", coordinates)
        try:
            return [
                [float(bbox["x"]), float(bbox["y"])],
                [float(bbox["x1"]), float(bbox["y1"])],
            ]
        except (KeyError, TypeError, ValueError):
            pass

        start, end = coordinates.get("start"), coordinates.get("end")
        if isinstance(start, dict) and isinstance(end, dict):
            try:
                return [
                    [float(start["x"]), float(start["y"])],
                    [float(end["x"]), float(end["y"])],
                ]
            except (KeyError, TypeError, ValueError):
                pass
        return []
