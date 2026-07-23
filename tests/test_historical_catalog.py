from __future__ import annotations

from pathlib import Path

from backend.pipeline.dimension_resolver import DimensionResolver
from backend.pipeline.historical_catalog import HistoricalCatalog
from backend.sdtl_core.entities import ElectricalRoom, Foundation


def make_room(object_id: str, height: float) -> ElectricalRoom:
    room = ElectricalRoom(
        id=object_id,
        source_geometry="GEO-ROOM",
        dimensions=[
            {"name": "length", "value": 10.0, "unit": "m"},
            {"name": "width", "value": 8.0, "unit": "m"},
            {"name": "height", "value": height, "unit": "m"},
        ],
        source_pdf="SE-PI-PL-OC-800.pdf",
        page=1,
    )
    room.approve("engineer@sdtl.local")
    return room


class TestHistoricalCatalog:
    def test_record_ignores_unapproved_proposals(self, tmp_path: Path) -> None:
        catalog = HistoricalCatalog(tmp_path / "history.sqlite3")
        pending = ElectricalRoom(
            id="OBJ-PENDING",
            source_geometry="GEO-1",
            dimensions=[{"name": "height", "value": 3.0, "unit": "m"}],
            source_pdf="SE-PI-PL-OC-800.pdf",
            page=1,
        )

        recorded = catalog.record(pending)

        assert recorded == 0
        assert catalog.suggest("ElectricalRoom", "height") is None

    def test_suggest_requires_minimum_samples(self, tmp_path: Path) -> None:
        catalog = HistoricalCatalog(tmp_path / "history.sqlite3")
        catalog.record(make_room("OBJ-1", 3.0))
        catalog.record(make_room("OBJ-2", 3.2))

        assert catalog.suggest("ElectricalRoom", "height") is None

        catalog.record(make_room("OBJ-3", 2.8))
        suggestion = catalog.suggest("ElectricalRoom", "height")

        assert suggestion is not None
        assert suggestion.sample_size == 3
        assert suggestion.value == 3.0
        assert suggestion.minimum == 2.8
        assert suggestion.maximum == 3.2

    def test_suggest_is_scoped_to_object_type_and_dimension(self, tmp_path: Path) -> None:
        catalog = HistoricalCatalog(tmp_path / "history.sqlite3")
        for index in range(3):
            catalog.record(make_room(f"OBJ-ROOM-{index}", 3.0))

        assert catalog.suggest("Foundation", "height") is None
        assert catalog.suggest("ElectricalRoom", "depth") is None


class TestDimensionResolverWithHistory:
    def test_uses_historical_median_before_static_default(self, tmp_path: Path) -> None:
        catalog = HistoricalCatalog(tmp_path / "history.sqlite3")
        for height in (2.6, 3.0, 3.4):
            catalog.record(make_room(f"OBJ-HIST-{height}", height))

        resolver = DimensionResolver(historical_catalog=catalog)
        new_room = ElectricalRoom(
            id="OBJ-NEW",
            source_geometry="GEO-NEW",
            dimensions=[
                {"reference": "DIM-LENGTH", "unit": "m"},
            ],
            source_pdf="SE-PI-PL-OC-999.pdf",
            page=1,
        )
        resolver.resolve(new_room, dimensions_by_id={}, topologies=[])

        dimensions = {item["name"]: item for item in new_room.dimensions}
        assert dimensions["height"]["source"] == "historical_estimate"
        assert dimensions["height"]["value"] == 3.0
        assert dimensions["height"]["sample_size"] == 3
        assert new_room.properties["dimension_defaults_applied"] == ["height"]

    def test_falls_back_to_static_default_without_enough_history(
        self, tmp_path: Path
    ) -> None:
        resolver = DimensionResolver(
            historical_catalog=HistoricalCatalog(tmp_path / "empty_history.sqlite3")
        )
        new_foundation = Foundation(
            id="OBJ-NEW-FOUND",
            source_geometry="GEO-NEW-FOUND",
            dimensions=[],
            source_pdf="SE-PI-PL-OC-998.pdf",
            page=1,
        )
        resolver.resolve(new_foundation, dimensions_by_id={}, topologies=[])

        dimensions = {item["name"]: item for item in new_foundation.dimensions}
        assert dimensions["height"]["source"] == "default"
        assert dimensions["height"]["value"] == 1.0
