from __future__ import annotations

from backend.drawing_analyzer import DimensionEntity, ExtractedText, GeometryEntity
from backend.drawing_analyzer.dimension_topology_analyzer import DimensionTopology
from backend.pipeline.scale_analysis import ScaleAnalyzer

DOCUMENT_ID = "DOC-SCALE-001"


def make_line(geometry_id: str, length: float) -> GeometryEntity:
    return GeometryEntity(
        geometry_id=geometry_id,
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="line",
        coordinates={"start": {"x": 0.0, "y": 0.0}, "end": {"x": length, "y": 0.0}},
        confidence=1.0,
    )


def make_dimension(dimension_id: str, value: float, unit: str = "m") -> DimensionEntity:
    return DimensionEntity(
        dimension_id=dimension_id,
        document_id=DOCUMENT_ID,
        page_number=1,
        dimension_type="linear",
        value=value,
        unit=unit,
        confidence=0.95,
    )


def make_topology(
    dimension_id: str, dimension_line: str, *, valid: bool = True
) -> DimensionTopology:
    return DimensionTopology(
        id=f"DT-{dimension_id}",
        dimension_id=dimension_id,
        dimension_line=dimension_line,
        valid=valid,
        confidence=0.8,
    )


def make_scale_text(content: str) -> ExtractedText:
    return ExtractedText(
        text_id="TXT-SCALE",
        document_id=DOCUMENT_ID,
        page_number=1,
        content=content,
        x=0,
        y=0,
        width=40,
        height=10,
        confidence=1.0,
    )


class TestEmpiricalRatio:
    def test_derives_ratio_from_a_single_valid_callout(self) -> None:
        dimension = make_dimension("DIM-1", value=20.0)
        line = make_line("GEO-LINE-1", length=200.0)
        topology = make_topology("DIM-1", "GEO-LINE-1")

        analysis = ScaleAnalyzer().analyze(
            texts=[],
            dimensions_by_id={"DIM-1": dimension},
            topologies=[topology],
            geometries_by_id={"GEO-LINE-1": line},
        )

        assert analysis.meters_per_pdf_unit == 0.1
        assert analysis.sample_size == 1

    def test_uses_median_across_multiple_callouts(self) -> None:
        dimensions_by_id = {
            "DIM-1": make_dimension("DIM-1", value=20.0),
            "DIM-2": make_dimension("DIM-2", value=12.0),
        }
        geometries_by_id = {
            "GEO-1": make_line("GEO-1", length=200.0),
            "GEO-2": make_line("GEO-2", length=120.0),
        }
        topologies = [
            make_topology("DIM-1", "GEO-1"),
            make_topology("DIM-2", "GEO-2"),
        ]

        analysis = ScaleAnalyzer().analyze([], dimensions_by_id, topologies, geometries_by_id)

        assert analysis.meters_per_pdf_unit == 0.1
        assert analysis.sample_size == 2

    def test_ignores_invalid_topologies(self) -> None:
        dimension = make_dimension("DIM-1", value=20.0)
        line = make_line("GEO-LINE-1", length=200.0)
        topology = make_topology("DIM-1", "GEO-LINE-1", valid=False)

        analysis = ScaleAnalyzer().analyze(
            [], {"DIM-1": dimension}, [topology], {"GEO-LINE-1": line}
        )

        assert analysis.meters_per_pdf_unit is None
        assert analysis.sample_size == 0

    def test_converts_units_before_deriving_ratio(self) -> None:
        dimension = make_dimension("DIM-1", value=8000.0, unit="mm")
        line = make_line("GEO-LINE-1", length=80.0)
        topology = make_topology("DIM-1", "GEO-LINE-1")

        analysis = ScaleAnalyzer().analyze(
            [], {"DIM-1": dimension}, [topology], {"GEO-LINE-1": line}
        )

        assert analysis.meters_per_pdf_unit == 0.1

    def test_no_dimension_data_returns_none_without_guessing(self) -> None:
        analysis = ScaleAnalyzer().analyze([], {}, [], {})

        assert analysis.meters_per_pdf_unit is None
        assert analysis.sample_size == 0


class TestDeclaredScaleDetection:
    def test_detects_labeled_scale_annotation(self) -> None:
        analysis = ScaleAnalyzer().analyze(
            [make_scale_text("ESCALA 1:50")], {}, [], {}
        )

        assert analysis.declared_scale == "1:50"
        assert analysis.declared_scale_confidence == 0.98

    def test_no_annotation_present_leaves_declared_scale_none(self) -> None:
        analysis = ScaleAnalyzer().analyze(
            [make_scale_text("SALA ELECTRICA")], {}, [], {}
        )

        assert analysis.declared_scale is None

    def test_declared_scale_is_independent_of_empirical_ratio(self) -> None:
        dimension = make_dimension("DIM-1", value=20.0)
        line = make_line("GEO-LINE-1", length=200.0)
        topology = make_topology("DIM-1", "GEO-LINE-1")

        analysis = ScaleAnalyzer().analyze(
            texts=[make_scale_text("ESCALA 1:75")],
            dimensions_by_id={"DIM-1": dimension},
            topologies=[topology],
            geometries_by_id={"GEO-LINE-1": line},
        )

        assert analysis.declared_scale == "1:75"
        assert analysis.meters_per_pdf_unit == 0.1
