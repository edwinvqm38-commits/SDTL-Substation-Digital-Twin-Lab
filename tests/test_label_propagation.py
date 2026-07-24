from __future__ import annotations

from backend.drawing_analyzer import EngineeringCandidate, GeometryEntity
from backend.pipeline.label_propagation import ConnectedLabelPropagator

DOCUMENT_ID = "DOC-LABEL-001"


def make_line(geometry_id: str, start: tuple[float, float], end: tuple[float, float]) -> GeometryEntity:
    return GeometryEntity(
        geometry_id=geometry_id,
        document_id=DOCUMENT_ID,
        page_number=1,
        entity_type="line",
        coordinates={"start": {"x": start[0], "y": start[1]}, "end": {"x": end[0], "y": end[1]}},
        confidence=1.0,
    )


def make_candidate(
    candidate_id: str,
    geometry_id: str,
    *,
    text_score: float = 0.0,
    dimension_score: float = 0.0,
    topology_score: float = 0.0,
    possible_type: str = "fence",
) -> EngineeringCandidate:
    geometry_score = 0.35
    final = geometry_score + text_score + dimension_score + topology_score
    evidence = []
    if text_score > 0:
        evidence.append({"type": "text_match", "value": "CERCO DE", "relation_id": "TGR-1"})
    if dimension_score > 0:
        evidence.append({"type": "dimension_match", "value": "12.50 m", "association_id": "DGA-1"})
    return EngineeringCandidate(
        id=candidate_id,
        possible_type=possible_type,
        confidence=round(final, 4),
        source_geometry=[geometry_id],
        evidence=evidence,
        scores={
            "geometry_score": geometry_score,
            "text_score": text_score,
            "dimension_score": dimension_score,
            "topology_score": topology_score,
            "final": final,
        },
    )


class TestConnectivity:
    def test_propagates_text_match_to_connected_unlabelled_segment(self) -> None:
        # Two segments sharing endpoint (100, 0): one labelled, one not.
        labelled_geometry = make_line("GEO-1", (0, 0), (100, 0))
        unlabelled_geometry = make_line("GEO-2", (100, 0), (200, 0))
        labelled = make_candidate("CAND-1", "GEO-1", text_score=0.285)
        unlabelled = make_candidate("CAND-2", "GEO-2", text_score=0.0)

        geometries_by_id = {"GEO-1": labelled_geometry, "GEO-2": unlabelled_geometry}
        ConnectedLabelPropagator().propagate([labelled, unlabelled], geometries_by_id)

        assert unlabelled.confidence == labelled.confidence
        assert any(
            item["type"] == "text_match"
            and item.get("propagated") is True
            and item["propagated_from"] == "CAND-1"
            for item in unlabelled.evidence
        )
        # The labelled candidate itself is untouched.
        assert labelled.confidence == 0.35 + 0.285

    def test_does_not_propagate_across_disconnected_segments(self) -> None:
        labelled_geometry = make_line("GEO-1", (0, 0), (100, 0))
        far_geometry = make_line("GEO-2", (500, 500), (600, 500))
        labelled = make_candidate("CAND-1", "GEO-1", text_score=0.285)
        far = make_candidate("CAND-2", "GEO-2", text_score=0.0)

        ConnectedLabelPropagator().propagate(
            [labelled, far], {"GEO-1": labelled_geometry, "GEO-2": far_geometry}
        )

        assert far.confidence == 0.35
        assert far.evidence == []

    def test_propagates_across_a_chain_of_three_segments(self) -> None:
        geometries = {
            "GEO-1": make_line("GEO-1", (0, 0), (100, 0)),
            "GEO-2": make_line("GEO-2", (100, 0), (200, 0)),
            "GEO-3": make_line("GEO-3", (200, 0), (300, 0)),
        }
        labelled = make_candidate("CAND-1", "GEO-1", text_score=0.285)
        middle = make_candidate("CAND-2", "GEO-2")
        far_end = make_candidate("CAND-3", "GEO-3")

        ConnectedLabelPropagator().propagate([labelled, middle, far_end], geometries)

        assert middle.confidence == labelled.confidence
        assert far_end.confidence == labelled.confidence

    def test_does_not_propagate_between_different_possible_types(self) -> None:
        geometries = {
            "GEO-1": make_line("GEO-1", (0, 0), (100, 0)),
            "GEO-2": make_line("GEO-2", (100, 0), (200, 0)),
        }
        fence_candidate = make_candidate("CAND-1", "GEO-1", text_score=0.285, possible_type="fence")
        road_candidate = make_candidate("CAND-2", "GEO-2", possible_type="road")

        ConnectedLabelPropagator().propagate([fence_candidate, road_candidate], geometries)

        assert road_candidate.confidence == 0.35
        assert road_candidate.evidence == []

    def test_does_not_downgrade_a_candidate_with_its_own_stronger_text_match(self) -> None:
        geometries = {
            "GEO-1": make_line("GEO-1", (0, 0), (100, 0)),
            "GEO-2": make_line("GEO-2", (100, 0), (200, 0)),
        }
        weak = make_candidate("CAND-1", "GEO-1", text_score=0.15)
        strong = make_candidate("CAND-2", "GEO-2", text_score=0.285)

        ConnectedLabelPropagator().propagate([weak, strong], geometries)

        assert strong.confidence == 0.35 + 0.285
        assert strong.evidence == [
            {"type": "text_match", "value": "CERCO DE", "relation_id": "TGR-1"}
        ]

    def test_preserves_each_candidates_own_dimension_and_topology_scores(self) -> None:
        geometries = {
            "GEO-1": make_line("GEO-1", (0, 0), (100, 0)),
            "GEO-2": make_line("GEO-2", (100, 0), (200, 0)),
        }
        labelled = make_candidate("CAND-1", "GEO-1", text_score=0.285)
        with_dimension = make_candidate("CAND-2", "GEO-2", dimension_score=0.20, topology_score=0.10)

        ConnectedLabelPropagator().propagate([labelled, with_dimension], geometries)

        assert with_dimension.confidence == round(0.35 + 0.285 + 0.20 + 0.10, 4)

    def test_no_op_when_no_candidate_in_component_has_a_text_match(self) -> None:
        geometries = {
            "GEO-1": make_line("GEO-1", (0, 0), (100, 0)),
            "GEO-2": make_line("GEO-2", (100, 0), (200, 0)),
        }
        first = make_candidate("CAND-1", "GEO-1")
        second = make_candidate("CAND-2", "GEO-2")

        ConnectedLabelPropagator().propagate([first, second], geometries)

        assert first.confidence == 0.35
        assert second.confidence == 0.35

    def test_endpoint_tolerance_is_configurable(self) -> None:
        geometries = {
            "GEO-1": make_line("GEO-1", (0, 0), (100, 0)),
            "GEO-2": make_line("GEO-2", (100.05, 0), (200, 0)),
        }
        labelled = make_candidate("CAND-1", "GEO-1", text_score=0.285)
        near_miss = make_candidate("CAND-2", "GEO-2")

        ConnectedLabelPropagator(endpoint_tolerance=0.01).propagate(
            [labelled, near_miss], geometries
        )
        assert near_miss.confidence == 0.35

        labelled2 = make_candidate("CAND-1", "GEO-1", text_score=0.285)
        near_miss2 = make_candidate("CAND-2", "GEO-2")
        ConnectedLabelPropagator(endpoint_tolerance=1.0).propagate(
            [labelled2, near_miss2], geometries
        )
        assert near_miss2.confidence == labelled2.confidence

    def test_rejects_non_positive_tolerance(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="endpoint_tolerance"):
            ConnectedLabelPropagator(endpoint_tolerance=0)


class TestDimensionPropagation:
    def test_propagates_dimension_match_to_connected_undimensioned_segment(self) -> None:
        dimensioned_geometry = make_line("GEO-1", (0, 0), (100, 0))
        undimensioned_geometry = make_line("GEO-2", (100, 0), (200, 0))
        dimensioned = make_candidate("CAND-1", "GEO-1", dimension_score=0.20)
        undimensioned = make_candidate("CAND-2", "GEO-2", dimension_score=0.0)

        geometries_by_id = {"GEO-1": dimensioned_geometry, "GEO-2": undimensioned_geometry}
        ConnectedLabelPropagator().propagate([dimensioned, undimensioned], geometries_by_id)

        assert undimensioned.confidence == dimensioned.confidence
        assert any(
            item["type"] == "dimension_match"
            and item.get("propagated") is True
            and item["propagated_from"] == "CAND-1"
            for item in undimensioned.evidence
        )
        assert dimensioned.confidence == 0.35 + 0.20

    def test_combines_text_from_one_sibling_and_dimension_from_another(self) -> None:
        # The real-world case this propagator exists for: a fence drawn as
        # three segments, one carrying the name label, another carrying the
        # only written dimension, and a third carrying neither -- all three
        # must end up with both, since they are the same physical feature.
        geometries = {
            "GEO-1": make_line("GEO-1", (0, 0), (100, 0)),
            "GEO-2": make_line("GEO-2", (100, 0), (200, 0)),
            "GEO-3": make_line("GEO-3", (200, 0), (300, 0)),
        }
        text_only = make_candidate("CAND-1", "GEO-1", text_score=0.30)
        dimension_only = make_candidate("CAND-2", "GEO-2", dimension_score=0.20)
        neither = make_candidate("CAND-3", "GEO-3")

        ConnectedLabelPropagator().propagate(
            [text_only, dimension_only, neither], geometries
        )

        expected = round(0.35 + 0.30 + 0.20, 4)
        assert neither.confidence == expected
        assert any(
            item["type"] == "text_match" and item["propagated_from"] == "CAND-1"
            for item in neither.evidence
        )
        assert any(
            item["type"] == "dimension_match" and item["propagated_from"] == "CAND-2"
            for item in neither.evidence
        )
        # The threshold ObjectValidator enforces -- confirms this scenario is
        # actually enough to make the object validate, not just score higher.
        assert neither.confidence >= 0.85

    def test_dimension_only_candidate_also_gains_text_from_sibling(self) -> None:
        geometries = {
            "GEO-1": make_line("GEO-1", (0, 0), (100, 0)),
            "GEO-2": make_line("GEO-2", (100, 0), (200, 0)),
        }
        text_only = make_candidate("CAND-1", "GEO-1", text_score=0.285)
        dimension_only = make_candidate("CAND-2", "GEO-2", dimension_score=0.20)

        ConnectedLabelPropagator().propagate([text_only, dimension_only], geometries)

        assert dimension_only.confidence == round(0.35 + 0.285 + 0.20, 4)
        assert any(item["type"] == "text_match" for item in dimension_only.evidence)
        assert any(
            item["type"] == "dimension_match" and "propagated" not in item
            for item in dimension_only.evidence
        )

    def test_does_not_downgrade_a_candidate_with_its_own_stronger_dimension_match(self) -> None:
        geometries = {
            "GEO-1": make_line("GEO-1", (0, 0), (100, 0)),
            "GEO-2": make_line("GEO-2", (100, 0), (200, 0)),
        }
        weak = make_candidate("CAND-1", "GEO-1", dimension_score=0.05)
        strong = make_candidate("CAND-2", "GEO-2", dimension_score=0.20)

        ConnectedLabelPropagator().propagate([weak, strong], geometries)

        assert strong.confidence == 0.35 + 0.20
        assert strong.evidence == [
            {"type": "dimension_match", "value": "12.50 m", "association_id": "DGA-1"}
        ]
