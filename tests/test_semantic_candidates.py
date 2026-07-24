from __future__ import annotations

from backend.drawing_analyzer import (
    CandidateBuilder,
    CandidateConfidenceCalculator,
    DimensionEntity,
    DrawingAnalysisBuilder,
    EngineeringCandidate,
    ExtractedText,
    GeometryEntity,
    GeometryFeatureExtractor,
    TextGeometryRelationEngine,
    TraceabilityMap,
)


DOCUMENT_ID = "DOC-SEMANTIC-001"


def make_rectangle(
    geometry_id: str,
    width: float,
    height: float,
) -> GeometryEntity:
    return GeometryEntity(
        geometry_id=geometry_id,
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="rectangle",
        coordinates={"x": 0, "y": 0, "width": width, "height": height},
        properties={"unit": "m"},
        confidence=1.0,
    )


def make_text(text_id: str, content: str, x: float = 2, y: float = 2) -> ExtractedText:
    return ExtractedText(
        text_id=text_id,
        document_id=DOCUMENT_ID,
        page_number=1,
        content=content,
        x=x,
        y=y,
        width=2,
        height=1,
        confidence=1.0,
    )


def candidates_for(
    geometry: GeometryEntity,
    texts: list[ExtractedText] | None = None,
    dimensions: list[DimensionEntity] | None = None,
    traceability: list[TraceabilityMap] | None = None,
) -> list[EngineeringCandidate]:
    text_values = texts or []
    feature = GeometryFeatureExtractor().extract_feature(
        geometry,
        texts=text_values,
        dimensions=dimensions or [],
    )
    relations = TextGeometryRelationEngine().relate(text_values, [geometry])
    return CandidateBuilder().build_candidates(
        [feature],
        text_relations=relations,
        dimensions=dimensions or [],
        traceability=traceability or [],
    )


def test_text_is_associated_with_containing_geometry() -> None:
    geometry = make_rectangle("GEO-ROOM-001", 8, 6)
    text = make_text("TXT-ROOM-001", "SALA ELECTRICA", x=3, y=2)

    relation = TextGeometryRelationEngine().relate([text], [geometry])[0]

    assert relation.geometry_id == "GEO-ROOM-001"
    assert relation.text == "SALA ELECTRICA"
    assert relation.contained is True
    assert relation.confidence == 0.95


def test_electrical_room_candidate() -> None:
    candidates = candidates_for(
        make_rectangle("GEO-ROOM-001", 8, 6),
        [make_text("TXT-ROOM-001", "SALA ELECTRICA")],
    )
    candidate = next(
        item for item in candidates if item.possible_type == "electrical_room"
    )

    assert candidate.status == "candidate"
    assert candidate.confidence > 0.60
    assert any(evidence["type"] == "text_match" for evidence in candidate.evidence)


def test_cable_trench_candidate() -> None:
    candidates = candidates_for(
        make_rectangle("GEO-TRENCH-001", 10, 1),
        [make_text("TXT-TRENCH-001", "CANAL DE CABLES")],
    )
    candidate = next(
        item for item in candidates if item.possible_type == "cable_trench"
    )

    assert candidate.source_geometry == ["GEO-TRENCH-001"]
    assert candidate.metadata["catalog_code"] == "CABLE_TRENCH"


def test_foundation_candidate_requires_dimension() -> None:
    geometry = make_rectangle("GEO-BASE-001", 8, 5)
    dimension = DimensionEntity(
        dimension_id="DIM-BASE-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        dimension_type="linear",
        value=8,
        unit="m",
        geometry_reference_id="GEO-BASE-001",
        confidence=0.95,
    )
    candidates = candidates_for(
        geometry,
        [make_text("TXT-BASE-001", "BASE DE EQUIPO")],
        [dimension],
    )
    candidate = next(item for item in candidates if item.possible_type == "foundation")

    assert candidate.confidence > 0.80
    assert any(
        evidence["type"] == "dimension_match" for evidence in candidate.evidence
    )


def test_candidate_confidence_is_deterministic() -> None:
    confidence = CandidateConfidenceCalculator().calculate(1, 1, 1, 1)

    assert confidence.geometry_score == 0.35
    assert confidence.text_score == 0.30
    assert confidence.dimension_score == 0.20
    assert confidence.topology_score == 0.10
    assert confidence.final == 0.95


def test_geometry_without_text_creates_low_confidence_candidate() -> None:
    candidates = candidates_for(make_rectangle("GEO-NO-TEXT-001", 8, 6))
    candidate = next(
        item for item in candidates if item.possible_type == "electrical_room"
    )

    assert candidate.confidence == 0.35
    assert not any(
        evidence["type"] == "text_match" for evidence in candidate.evidence
    )


def test_incorrect_geometry_is_rejected() -> None:
    geometry = GeometryEntity(
        geometry_id="GEO-CURVE-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="curve",
        coordinates={
            "bounding_box": {"x": 0, "y": 0, "width": 8, "height": 6}
        },
        confidence=1.0,
    )

    assert candidates_for(geometry) == []


def test_candidate_preserves_pdf_traceability() -> None:
    geometry = make_rectangle("GEO-TRACE-001", 8, 6)
    traceability = TraceabilityMap(
        source_pdf="SE-PI-PL-OC-500.pdf",
        page=2,
        geometry_id="GEO-TRACE-001",
        coordinates=[[10, 20], [18, 26]],
    )
    candidates = candidates_for(
        geometry,
        [make_text("TXT-TRACE-001", "SALA CONTROL")],
        traceability=[traceability],
    )
    candidate = next(
        item for item in candidates if item.possible_type == "electrical_room"
    )

    assert candidate.traceability["source_pdf"] == "SE-PI-PL-OC-500.pdf"
    assert candidate.traceability["page"] == 2
    assert candidate.traceability["geometry_id"] == "GEO-TRACE-001"


def test_analysis_builder_stores_semantic_metadata() -> None:
    analysis = DrawingAnalysisBuilder().build_analysis(
        document_id=DOCUMENT_ID,
        semantic_candidates_created=True,
        candidate_count=25,
    )

    assert analysis.extraction_metadata["analysis_version"] == "1.7"
    assert analysis.extraction_metadata["analyzer_version"] == "1.7"
    assert analysis.extraction_metadata["semantic_candidates_created"] is True
    assert analysis.extraction_metadata["candidate_count"] == 25


def test_transformer_candidate_requires_dimension() -> None:
    geometry = make_rectangle("GEO-TRAFO-001", 6, 4)
    dimension = DimensionEntity(
        dimension_id="DIM-TRAFO-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        dimension_type="linear",
        value=6,
        unit="m",
        geometry_reference_id="GEO-TRAFO-001",
        confidence=0.95,
    )
    candidates = candidates_for(
        geometry,
        [make_text("TXT-TRAFO-001", "TRANSFORMADOR DE POTENCIA")],
        [dimension],
    )
    candidate = next(item for item in candidates if item.possible_type == "transformer")

    assert candidate.confidence > 0.80
    assert candidate.metadata["catalog_code"] == "TRANSFORMER"


def test_circuit_breaker_candidate() -> None:
    geometry = make_rectangle("GEO-BRK-001", 3, 2)
    dimension = DimensionEntity(
        dimension_id="DIM-BRK-001",
        document_id=DOCUMENT_ID,
        page_number=1,
        dimension_type="linear",
        value=3,
        unit="m",
        geometry_reference_id="GEO-BRK-001",
        confidence=0.95,
    )
    candidates = candidates_for(
        geometry,
        [make_text("TXT-BRK-001", "INTERRUPTOR DE POTENCIA")],
        [dimension],
    )
    candidate = next(item for item in candidates if item.possible_type == "circuit_breaker")

    assert candidate.confidence > 0.80


def test_disconnector_candidate() -> None:
    candidates = candidates_for(
        make_rectangle("GEO-SEC-001", 2, 1.5),
        [make_text("TXT-SEC-001", "SECCIONADOR")],
    )
    candidate = next(item for item in candidates if item.possible_type == "disconnector")

    assert any(evidence["type"] == "text_match" for evidence in candidate.evidence)


def test_busbar_candidate() -> None:
    candidates = candidates_for(
        make_rectangle("GEO-BUS-001", 15, 0.3),
        [make_text("TXT-BUS-001", "BARRA PRINCIPAL")],
    )
    candidate = next(item for item in candidates if item.possible_type == "busbar")

    assert candidate.metadata["catalog_code"] == "BUSBAR"


def test_insulator_string_candidate() -> None:
    candidates = candidates_for(
        make_rectangle("GEO-AIS-001", 1, 0.3),
        [make_text("TXT-AIS-001", "CADENA DE AISLADORES")],
    )
    candidate = next(item for item in candidates if item.possible_type == "insulator_string")

    assert any(evidence["type"] == "text_match" for evidence in candidate.evidence)


def test_lightning_arrester_candidate() -> None:
    candidates = candidates_for(
        make_rectangle("GEO-PARARRAYOS-001", 1, 0.5),
        [make_text("TXT-PARARRAYOS-001", "PARARRAYOS")],
    )
    candidate = next(item for item in candidates if item.possible_type == "lightning_arrester")

    assert any(evidence["type"] == "text_match" for evidence in candidate.evidence)
