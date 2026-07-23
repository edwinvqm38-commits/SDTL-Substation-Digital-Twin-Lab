from __future__ import annotations

from backend.drawing_analyzer import DimensionAssociation, ExtractedText, GeometryEntity
from backend.pipeline.extraction_pipeline import DrawingToObjectsPipeline

DOCUMENT_ID = "DOC-PERF-001"


def make_line(geometry_id: str, length: float) -> GeometryEntity:
    return GeometryEntity(
        geometry_id=geometry_id,
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="line",
        coordinates={"start": {"x": 0.0, "y": 0.0}, "end": {"x": length, "y": 0.0}},
        confidence=1.0,
    )


def make_text(text_id: str, width: float, content: str = "SALA") -> ExtractedText:
    return ExtractedText(
        text_id=text_id,
        document_id=DOCUMENT_ID,
        page_number=1,
        content=content,
        x=0.0,
        y=0.0,
        width=width,
        height=5.0,
        confidence=1.0,
    )


def make_association(association_id: str, confidence: float) -> DimensionAssociation:
    return DimensionAssociation(
        association_id=association_id,
        dimension_id=f"DIM-{association_id}",
        dimension_line_id=f"GEO-{association_id}",
        relation_type="defines_length",
        confidence=confidence,
    )


class TestFilterNegligibleGeometries:
    def test_drops_geometries_smaller_than_threshold(self) -> None:
        pipeline = DrawingToObjectsPipeline(minimum_geometry_size=3.0)
        tiny = make_line("GEO-TINY", length=1.0)
        real = make_line("GEO-REAL", length=200.0)

        kept = pipeline._filter_negligible_geometries([tiny, real])

        assert kept == [real]

    def test_keeps_geometry_exactly_at_threshold(self) -> None:
        pipeline = DrawingToObjectsPipeline(minimum_geometry_size=3.0)
        exact = make_line("GEO-EXACT", length=3.0)

        assert pipeline._filter_negligible_geometries([exact]) == [exact]

    def test_zero_threshold_disables_filtering(self) -> None:
        pipeline = DrawingToObjectsPipeline(minimum_geometry_size=0)
        tiny = make_line("GEO-TINY", length=0.1)

        assert pipeline._filter_negligible_geometries([tiny]) == [tiny]

    def test_geometry_without_determinable_bounds_is_kept(self) -> None:
        pipeline = DrawingToObjectsPipeline(minimum_geometry_size=3.0)
        undetermined = GeometryEntity(
            geometry_id="GEO-UNKNOWN",
            document_id=DOCUMENT_ID,
            page_number=1,
            entity_type="unknown",
            coordinates={"operation": "unhandled"},
            confidence=1.0,
        )

        assert pipeline._filter_negligible_geometries([undetermined]) == [undetermined]


class TestCapAssociations:
    def test_returns_all_when_under_the_cap(self) -> None:
        pipeline = DrawingToObjectsPipeline(max_dimension_associations=5)
        associations = [make_association(f"A{i}", confidence=0.5) for i in range(3)]

        assert pipeline._cap_associations(associations) == associations

    def test_keeps_highest_confidence_when_over_the_cap(self) -> None:
        pipeline = DrawingToObjectsPipeline(max_dimension_associations=2)
        low = make_association("LOW", confidence=0.5)
        mid = make_association("MID", confidence=0.7)
        high = make_association("HIGH", confidence=0.95)

        capped = pipeline._cap_associations([low, high, mid])

        assert capped == [high, mid]

    def test_exactly_at_cap_returns_all_unsorted(self) -> None:
        pipeline = DrawingToObjectsPipeline(max_dimension_associations=2)
        associations = [make_association("A", 0.5), make_association("B", 0.9)]

        assert pipeline._cap_associations(associations) == associations


class TestFilterLongNotes:
    def test_drops_text_wider_than_the_limit(self) -> None:
        pipeline = DrawingToObjectsPipeline(maximum_label_width=80.0)
        note = make_text("TXT-NOTE", width=228.5, content="El acceso vehicular sera...")
        label = make_text("TXT-LABEL", width=40.0, content="SALA ELECTRICA")

        kept = pipeline._filter_long_notes([note, label])

        assert kept == [label]

    def test_keeps_text_exactly_at_the_limit(self) -> None:
        pipeline = DrawingToObjectsPipeline(maximum_label_width=80.0)
        exact = make_text("TXT-EXACT", width=80.0)

        assert pipeline._filter_long_notes([exact]) == [exact]

    def test_zero_width_disables_filtering(self) -> None:
        pipeline = DrawingToObjectsPipeline(maximum_label_width=0)
        note = make_text("TXT-NOTE", width=500.0)

        assert pipeline._filter_long_notes([note]) == [note]
