from __future__ import annotations

from backend.drawing_analyzer import (
    CandidateConfidenceCalculator,
    EngineeringCandidate,
    GeometryEntity,
)

Point = tuple[float, float]


class ConnectedLabelPropagator:
    """Share a confident text match and/or dimension callout across line
    segments that are physically the same feature, drawn as many separate
    geometries.

    A real fence/perimeter is drawn as dozens or hundreds of short straight
    line segments meeting end to end, but its name label ("CERCO DE LADRILLO
    PROYECTADO") and its one written spacing dimension are each only present
    next to ONE of those segments -- on a real drawing tested against this
    pipeline, that alone meant only 1 of 2,798 fence-shaped line candidates
    ever had a text match. The other segments are the same physical fence,
    just unlabelled at that exact point.

    Text and dimension evidence are each propagated independently (a
    candidate keeps its own score in either category if it is already the
    strongest in its component): ObjectValidator's geometry_valid check
    requires dimension_match evidence on every object regardless of type,
    and the 0.35/0.30/0.20/0.10 confidence weights mean geometry+text alone
    tops out at 0.65 -- structurally short of the 0.85 threshold without a
    dimension_match contribution, so text alone is not enough to fix this.

    This propagates within each connected group of same-type candidates
    (segments sharing an endpoint, found via a cheap coordinate bucketing --
    no full geometric fusion, so it works without touching
    GeometryFeatureExtractor's closed/open polygon model). Confidence is
    recomputed with the same CandidateConfidenceCalculator the rest of the
    pipeline already uses, never invented. Propagated evidence keeps its
    real "text_match"/"dimension_match" type (ObjectValidator and
    SDTLObjectFactory both look evidence up by that exact string) but is
    marked with "propagated": True and "propagated_from": <candidate id>,
    so a reviewer can always tell a direct match from an inherited one.
    """

    def __init__(
        self,
        confidence_calculator: CandidateConfidenceCalculator | None = None,
        endpoint_tolerance: float = 2.0,
    ) -> None:
        if endpoint_tolerance <= 0:
            raise ValueError("endpoint_tolerance must be greater than zero")
        self.confidence_calculator = confidence_calculator or CandidateConfidenceCalculator()
        self.endpoint_tolerance = endpoint_tolerance

    def propagate(
        self,
        candidates: list[EngineeringCandidate],
        geometries_by_id: dict[str, GeometryEntity],
    ) -> None:
        """Mutate candidates in place, boosting confidence where a connected
        sibling of the same type already carries a real text match."""

        by_type: dict[str, list[EngineeringCandidate]] = {}
        for candidate in candidates:
            if candidate.source_geometry:
                by_type.setdefault(candidate.possible_type, []).append(candidate)

        for group in by_type.values():
            for component in self._connected_components(group, geometries_by_id):
                self._propagate_within_component(component)

    def _propagate_within_component(self, component: list[EngineeringCandidate]) -> None:
        if len(component) < 2:
            return

        best_text = max(component, key=lambda candidate: candidate.scores.get("text_score", 0.0))
        best_text_score = best_text.scores.get("text_score", 0.0)
        best_dimension = max(
            component, key=lambda candidate: candidate.scores.get("dimension_score", 0.0)
        )
        best_dimension_score = best_dimension.scores.get("dimension_score", 0.0)
        if best_text_score <= 0 and best_dimension_score <= 0:
            return

        # Evidence keeps its real "text_match"/"dimension_match" type (rather
        # than a distinct "..._propagated" type) because ObjectValidator and
        # SDTLObjectFactory both look evidence up by that exact type string
        # -- those are tested, core modules this pipeline does not modify.
        # The "propagated"/"propagated_from" keys are the transparency: any
        # reviewer or downstream code can still tell a direct match from an
        # inherited one by checking for them.
        text_evidence = [
            {**item, "propagated": True, "propagated_from": best_text.id}
            for item in best_text.evidence
            if item.get("type") == "text_match"
        ]
        dimension_evidence = [
            {**item, "propagated": True, "propagated_from": best_dimension.id}
            for item in best_dimension.evidence
            if item.get("type") == "dimension_match"
        ]

        for candidate in component:
            own_text_score = candidate.scores.get("text_score", 0.0)
            own_dimension_score = candidate.scores.get("dimension_score", 0.0)
            adopt_text = best_text_score > own_text_score
            adopt_dimension = best_dimension_score > own_dimension_score
            if not adopt_text and not adopt_dimension:
                continue

            text_match = (best_text_score if adopt_text else own_text_score) / 0.30
            dimension_match = (
                best_dimension_score if adopt_dimension else own_dimension_score
            ) / 0.20
            topology_match = candidate.scores.get("topology_score", 0.0) / 0.10
            updated = self.confidence_calculator.calculate(
                geometry_match=1.0,
                text_match=text_match,
                dimension_match=dimension_match,
                topology_match=topology_match,
            )
            candidate.confidence = updated.final
            candidate.scores = updated.model_dump()
            candidate.evidence = [
                *candidate.evidence,
                *(text_evidence if adopt_text else []),
                *(dimension_evidence if adopt_dimension else []),
            ]

    def _connected_components(
        self,
        group: list[EngineeringCandidate],
        geometries_by_id: dict[str, GeometryEntity],
    ) -> list[list[EngineeringCandidate]]:
        parent: dict[str, str] = {candidate.id: candidate.id for candidate in group}

        def find(candidate_id: str) -> str:
            while parent[candidate_id] != candidate_id:
                parent[candidate_id] = parent[parent[candidate_id]]
                candidate_id = parent[candidate_id]
            return candidate_id

        def union(first: str, second: str) -> None:
            root_first, root_second = find(first), find(second)
            if root_first != root_second:
                parent[root_first] = root_second

        buckets: dict[tuple[int, int], list[str]] = {}
        for candidate in group:
            geometry = geometries_by_id.get(candidate.source_geometry[0])
            if geometry is None:
                continue
            for point in self._endpoints(geometry):
                key = (
                    round(point[0] / self.endpoint_tolerance),
                    round(point[1] / self.endpoint_tolerance),
                )
                buckets.setdefault(key, []).append(candidate.id)

        for candidate_ids in buckets.values():
            for other_id in candidate_ids[1:]:
                union(candidate_ids[0], other_id)

        components: dict[str, list[EngineeringCandidate]] = {}
        for candidate in group:
            components.setdefault(find(candidate.id), []).append(candidate)
        return list(components.values())

    @staticmethod
    def _endpoints(geometry: GeometryEntity) -> list[Point]:
        start = geometry.coordinates.get("start")
        end = geometry.coordinates.get("end")
        if isinstance(start, dict) and isinstance(end, dict):
            try:
                return [
                    (float(start["x"]), float(start["y"])),
                    (float(end["x"]), float(end["y"])),
                ]
            except (KeyError, TypeError, ValueError):
                return []
        return []
