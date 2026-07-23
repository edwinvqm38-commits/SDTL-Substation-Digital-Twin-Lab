from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.drawing_analyzer import (
    CandidateBuilder,
    DimensionAssociation,
    DimensionDetector,
    DimensionGeometryAssociationEngine,
    DimensionTargetResolutionEngine,
    DimensionTopologyAnalyzer,
    EngineeringCandidate,
    ExtractedText,
    GeometryEntity,
    GeometryFeatureExtractor,
    OCRTextExtractor,
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
from .scale_analysis import ScaleAnalysis, ScaleAnalyzer

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
    scale: ScaleAnalysis | None = None


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
        scale_analyzer: ScaleAnalyzer | None = None,
        ocr_extractor: OCRTextExtractor | None = None,
        minimum_geometry_size: float = 3.0,
        max_dimension_associations: int = 40,
        text_geometry_distance_threshold: float = 20.0,
        maximum_label_width: float = 80.0,
    ) -> None:
        self.dimension_resolver = dimension_resolver or DimensionResolver()
        self.factory = SDTLObjectFactory()
        self.validator = ObjectValidator()
        self.llm_classifier = llm_classifier or LLMFallbackClassifier()
        self.scale_analyzer = scale_analyzer or ScaleAnalyzer()
        self.ocr_extractor = ocr_extractor or OCRTextExtractor()
        self.minimum_geometry_size = minimum_geometry_size
        self.max_dimension_associations = max_dimension_associations
        self.text_geometry_distance_threshold = text_geometry_distance_threshold
        self.maximum_label_width = maximum_label_width

    def run(self, pdf_path: str | Path) -> ExtractionResult:
        pdf = Path(pdf_path)
        if not pdf.exists():
            raise FileNotFoundError(pdf)

        geometries = self._filter_negligible_geometries(
            self._deduplicate_lines(VectorGeometryExtractor().extract_geometry(str(pdf)))
        )
        texts = PDFTextExtractor().extract_text_with_coordinates(str(pdf))
        used_ocr = False
        if not texts:
            # No embedded fonts / native text at all -- common for CAD plot
            # drivers that flatten text to vector outlines. Fall back to OCR
            # on a raster render so labels and dimension callouts are still
            # recoverable, instead of silently producing zero objects.
            texts = self.ocr_extractor.extract_text(str(pdf), document_id=pdf.stem)
            used_ocr = True
        texts = self._filter_long_notes(texts)
        dimensions = DimensionDetector().detect_dimensions(texts)
        dimensions_by_id = {dimension.dimension_id: dimension for dimension in dimensions}

        # The only consumer of these spatial_relations below is
        # DimensionGeometryAssociationEngine, which only ever looks up a
        # relation by (dimension.text_source_id, geometry_id) -- so only the
        # handful of texts that actually produced a dimension are relevant
        # here. That matters a lot on a real sheet: a long note/title line's
        # bounding box (hundreds of points wide) "intersects" huge numbers of
        # geometries regardless of any distance_threshold (that only gates
        # the weaker "near" fallback, not direct bbox overlap), and one such
        # line alone produced over 150,000 spurious matches on a real
        # drawing, which then made every later per-association scan
        # (extension lines, target resolution, topology) run for minutes.
        # Dimension callouts are always short strings with small boxes, so
        # restricting to them avoids that blowup at the source.
        dimension_text_ids = {
            dimension.text_source_id
            for dimension in dimensions
            if dimension.text_source_id is not None
        }
        dimension_texts = [text for text in texts if text.text_id in dimension_text_ids]

        spatial_relations = SpatialAssociationEngine(
            distance_threshold=self.text_geometry_distance_threshold
        ).associate(dimension_texts, geometries)
        dimension_associations = self._cap_associations(
            DimensionGeometryAssociationEngine(
                distance_threshold=self.text_geometry_distance_threshold
            ).associate(dimensions, geometries, spatial_relations)
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

        geometries_by_id = {geometry.geometry_id: geometry for geometry in geometries}
        scale = self.scale_analyzer.analyze(
            texts, dimensions_by_id, topologies, geometries_by_id
        )

        features = GeometryFeatureExtractor().extract_features(
            geometries, texts=texts, dimensions=dimensions
        )
        text_relations = TextGeometryRelationEngine(
            distance_threshold=self.text_geometry_distance_threshold
        ).relate(texts, geometries)
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
            self._assign_position(civil_object, geometries_by_id, scale)
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
            "used_ocr": used_ocr,
            "dimensions": len(dimensions),
            "dimension_links_resolved": sum(
                1 for link in dimension_links if link.target_geometry_id
            ),
            "candidates": len(candidates),
            "objects_created": len(result.objects),
            "objects_skipped": len(result.skipped),
        }
        result.scale = scale
        return result

    def _assign_position(
        self,
        civil_object: CivilObject,
        geometries_by_id: dict[str, GeometryEntity],
        scale: ScaleAnalysis,
    ) -> None:
        """Place the object at its true relative position on this sheet using
        the empirical meters-per-PDF-unit ratio (see scale_analysis.py). Left
        at the geometry_3d default ([0, 0, 0]) when no ratio could be derived
        (no valid dimension callouts anywhere on the sheet), rather than
        guessing -- generate_3d.py already requires human approval before
        using any of this, so an un-positioned object is still safe, just
        stacked at the origin until a scale can be established.

        Positions are only self-consistent within this one source PDF: each
        sheet has its own arbitrary drawing origin, so objects extracted
        from different plans of the same project are not placed in a shared
        world frame by this step (see cross_reference.py for matching them
        by label instead).
        """

        if scale.meters_per_pdf_unit is None:
            return

        geometry = geometries_by_id.get(civil_object.source_geometry)
        if geometry is None:
            return

        center = self._paper_center(geometry)
        if center is None:
            return

        x, y = center
        civil_object.properties = {
            **civil_object.properties,
            "position": [x * scale.meters_per_pdf_unit, y * scale.meters_per_pdf_unit, 0.0],
        }

    def _paper_center(self, geometry: GeometryEntity) -> tuple[float, float] | None:
        corners = self._bounds_as_coordinates(geometry)
        if not corners:
            return None
        return (
            sum(corner[0] for corner in corners) / len(corners),
            sum(corner[1] for corner in corners) / len(corners),
        )

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

    def _filter_long_notes(self, texts: list[ExtractedText]) -> list[ExtractedText]:
        """Drop text lines wider than maximum_label_width (default 80pt).

        A real object label ("SALA DE CONTROL"), equipment tag ("BASE E-01"),
        or dimension callout ("20 m") is always a short string. A drawing's
        general notes/legend, by contrast, are full sentences that OCR (or
        even native PDF text extraction) returns as much wider bounding
        boxes -- on a real drawing tested against this pipeline, a handful
        of ~200pt-wide note lines alone produced over 150,000 spurious
        "intersects" matches each in SpatialAssociationEngine and
        TextGeometryRelationEngine (bbox overlap there does not depend on
        any distance_threshold, so tuning that parameter alone cannot fix
        it), which then made every downstream stage that iterates those
        matches run for minutes. Filtering the source line out is cheaper
        and more correct than bounding the resulting relations after the
        fact, since notes were never going to become a room/dimension label
        anyway.
        """

        if self.maximum_label_width <= 0:
            return texts
        return [text for text in texts if text.width <= self.maximum_label_width]

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

    def _cap_associations(
        self, associations: list[DimensionAssociation]
    ) -> list[DimensionAssociation]:
        """Bound DimensionTargetResolutionEngine's worst case.

        That stage (and the topology analysis after it) does O(geometries)
        work per association -- necessary for its own correctness, but with
        thousands of geometries even a few hundred associations is a lot of
        Python-level work, and the number of "unknown"/proximity-only
        associations a real drawing produces isn't something this pipeline
        controls (it also isn't fully deterministic run to run, since OCR's
        recognized text positions vary slightly). Keeping only the
        highest-confidence associations, up to max_dimension_associations,
        makes runtime predictable regardless of how noisy a given sheet is,
        at the cost of only chasing the associations most likely to be real.
        """

        if len(associations) <= self.max_dimension_associations:
            return associations
        return sorted(associations, key=lambda item: item.confidence, reverse=True)[
            : self.max_dimension_associations
        ]

    def _filter_negligible_geometries(
        self, geometries: list[GeometryEntity]
    ) -> list[GeometryEntity]:
        """Drop geometries whose bounding-box diagonal is below
        minimum_geometry_size (default 3 PDF points).

        Real AutoCAD "plot to PDF" output commonly flattens every letterform
        into its own tiny vector outline (see ocr_text_extractor.py) instead
        of keeping real PDF text. On a real drawing tested against this
        pipeline, that alone produced 62,634 geometries, over 90% of them
        under 5pt across -- almost entirely former letter strokes and hatch
        ticks, not engineering content (a wall, dimension line, or fence
        segment on a properly scaled sheet is always far larger). Left
        unfiltered, every later stage that compares each dimension/text
        against every geometry (SpatialAssociationEngine,
        DimensionGeometryAssociationEngine, and especially
        DimensionTargetResolutionEngine's per-association extension-line and
        target scan) becomes O(n) or worse in that noise and can run for
        many minutes on a single sheet. This filter runs once, right after
        extraction, so every later stage only ever sees plausible
        engineering geometry.
        """

        if self.minimum_geometry_size <= 0:
            return geometries

        kept: list[GeometryEntity] = []
        for geometry in geometries:
            corners = self._bounds_as_coordinates(geometry)
            if not corners:
                kept.append(geometry)
                continue
            (x0, y0), (x1, y1) = corners[0], corners[-1]
            diagonal = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            if diagonal >= self.minimum_geometry_size:
                kept.append(geometry)
        return kept

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
