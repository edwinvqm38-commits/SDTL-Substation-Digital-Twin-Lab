from __future__ import annotations

from typing import Any
from uuid import uuid4

from backend.core.models import DocumentAnalysis, ExtractionResult


class DrawingAnalysisBuilder:
    """Build validated SDTL Core analysis models from drawing-analyzer results."""

    def build_analysis(
        self,
        document_id: str,
        extraction_metadata: dict[str, Any] | None = None,
        status: str = "completed",
        text_blocks_detected: int | None = None,
        coordinates_available: bool | None = None,
        geometry_entities_detected: int | None = None,
        geometry_metadata: dict[str, Any] | None = None,
        spatial_relations_detected: int | None = None,
        association_metadata: dict[str, Any] | None = None,
        dimensions_found: int | None = None,
        scales_found: int | None = None,
        measurement_metadata: dict[str, Any] | None = None,
        dimension_associations_detected: int | None = None,
        dimension_association_metadata: dict[str, Any] | None = None,
        dimension_target_links_detected: int | None = None,
        dimension_target_metadata: dict[str, Any] | None = None,
        scale_detected: bool | None = None,
        units_normalized: bool | None = None,
        dimension_topology_validated: bool | None = None,
        semantic_candidates_created: bool | None = None,
        candidate_count: int | None = None,
    ) -> DocumentAnalysis:
        if (
            semantic_candidates_created is not None or candidate_count is not None
        ):
            analyzer_version = "1.7"
        elif (
            scale_detected is not None
            or units_normalized is not None
            or dimension_topology_validated is not None
        ):
            analyzer_version = "1.6.5"
        elif (
            dimension_target_links_detected is not None
            or dimension_target_metadata is not None
        ):
            analyzer_version = "1.6"
        elif (
            dimension_associations_detected is not None
            or dimension_association_metadata is not None
        ):
            analyzer_version = "1.5"
        elif (
            dimensions_found is not None
            or scales_found is not None
            or measurement_metadata is not None
        ):
            analyzer_version = "1.4"
        elif spatial_relations_detected is not None or association_metadata is not None:
            analyzer_version = "1.3"
        elif geometry_entities_detected is not None or geometry_metadata is not None:
            analyzer_version = "1.2"
        else:
            analyzer_version = "1.1"
        metadata: dict[str, Any] = {
            "analyzer": "SDTL Drawing Analyzer",
            "analyzer_version": analyzer_version,
            "advanced_detection": False,
        }
        if extraction_metadata:
            metadata.update(extraction_metadata)
        if text_blocks_detected is not None:
            metadata["text_blocks_detected"] = text_blocks_detected
        if coordinates_available is not None:
            metadata["coordinates_available"] = coordinates_available
        if geometry_entities_detected is not None:
            metadata["geometry_entities_detected"] = geometry_entities_detected
            metadata["vector_geometry_available"] = geometry_entities_detected > 0
        if geometry_metadata is not None:
            metadata["geometry_metadata"] = dict(geometry_metadata)
        if spatial_relations_detected is not None:
            metadata["spatial_relations_detected"] = spatial_relations_detected
        if association_metadata is not None:
            metadata["association_metadata"] = dict(association_metadata)
        if dimensions_found is not None:
            metadata["dimensions_found"] = dimensions_found
        if scales_found is not None:
            metadata["scales_found"] = scales_found
        if measurement_metadata is not None:
            metadata["measurement_metadata"] = dict(measurement_metadata)
        if dimension_associations_detected is not None:
            metadata[
                "dimension_associations_detected"
            ] = dimension_associations_detected
            metadata[
                "dimension_associations_created"
            ] = dimension_associations_detected
        if dimension_association_metadata is not None:
            metadata["dimension_association_metadata"] = dict(
                dimension_association_metadata
            )
        if dimension_target_links_detected is not None:
            metadata[
                "dimension_target_links_detected"
            ] = dimension_target_links_detected
            metadata["dimension_links_created"] = dimension_target_links_detected
        if dimension_target_metadata is not None:
            metadata["dimension_target_metadata"] = dict(dimension_target_metadata)
            if "resolved_targets" in dimension_target_metadata:
                metadata["resolved_targets"] = dimension_target_metadata[
                    "resolved_targets"
                ]
        if analyzer_version in {"1.6.5", "1.7"}:
            metadata["analysis_version"] = analyzer_version
        if scale_detected is not None:
            metadata["scale_detected"] = scale_detected
        if units_normalized is not None:
            metadata["units_normalized"] = units_normalized
        if dimension_topology_validated is not None:
            metadata["dimension_topology_validated"] = dimension_topology_validated
        if semantic_candidates_created is not None:
            metadata["semantic_candidates_created"] = semantic_candidates_created
        if candidate_count is not None:
            metadata["candidate_count"] = candidate_count

        return DocumentAnalysis(
            analysis_id=f"AN-{uuid4().hex}",
            document_id=document_id,
            status=status,
            elements_detected=0,
            dimensions_found=dimensions_found if dimensions_found is not None else 0,
            references_found=0,
            sections_found=0,
            extraction_metadata=metadata,
        )

    def build_extraction_result(
        self,
        document_id: str,
        element_type: str,
        confidence: float,
        raw_data: dict[str, Any] | None = None,
        geometry_reference: str | None = None,
    ) -> ExtractionResult:
        return ExtractionResult(
            extraction_id=f"EXT-{uuid4().hex}",
            document_id=document_id,
            element_type=element_type,
            confidence=confidence,
            geometry_reference=geometry_reference,
            raw_data=raw_data or {},
        )
