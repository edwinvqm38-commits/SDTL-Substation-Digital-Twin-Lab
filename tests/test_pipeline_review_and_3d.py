from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.pipeline.generate_3d import ThreeDGenerationStage
from backend.pipeline.quantity_takeoff import QuantityTakeoffBuilder
from backend.pipeline.review_queue import ReviewQueue
from backend.sdtl_core.entities import CableTrench, ElectricalRoom, Fence, Foundation


def make_room(object_id: str = "OBJ-ROOM-001") -> ElectricalRoom:
    return ElectricalRoom(
        id=object_id,
        source_geometry="GEO-ROOM-001",
        coordinates=[[0, 0], [20, 12]],
        dimensions=[
            {"name": "length", "value": 20.0, "unit": "m", "source": "drawing"},
            {"name": "width", "value": 12.0, "unit": "m", "source": "drawing"},
            {"name": "height", "value": 3.0, "unit": "m", "source": "default"},
        ],
        source_pdf="SE-PI-PL-OC-900.pdf",
        page=1,
    )


def make_foundation(object_id: str = "OBJ-FOUND-001") -> Foundation:
    return Foundation(
        id=object_id,
        source_geometry="GEO-FOUND-001",
        dimensions=[
            {"name": "length", "value": 8.0, "unit": "m", "source": "drawing"},
            {"name": "width", "value": 5.0, "unit": "m", "source": "drawing"},
            {"name": "height", "value": 1.0, "unit": "m", "source": "default"},
        ],
        source_pdf="SE-PI-PL-OC-901.pdf",
        page=1,
    )


def make_fence(object_id: str = "OBJ-FENCE-001") -> Fence:
    return Fence(
        id=object_id,
        source_geometry="GEO-FENCE-001",
        dimensions=[{"name": "length", "value": 50.0, "unit": "m", "source": "drawing"}],
        source_pdf="SE-PI-PL-OC-902.pdf",
        page=1,
    )


class TestReviewQueue:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        queue = ReviewQueue()
        path = queue.save([make_room(), make_foundation()], tmp_path / "queue.json")

        loaded = queue.load(path)

        assert {obj.id for obj in loaded} == {"OBJ-ROOM-001", "OBJ-FOUND-001"}
        assert isinstance(next(o for o in loaded if o.type == "ElectricalRoom"), ElectricalRoom)
        assert all(obj.state == "proposal" for obj in loaded)

    def test_approve_persists_reviewer_and_state(self, tmp_path: Path) -> None:
        queue = ReviewQueue()
        path = queue.save([make_room()], tmp_path / "queue.json")

        approved = queue.approve(path, "OBJ-ROOM-001", "engineer@sdtl.local")

        assert approved.state == "approved"
        reloaded = queue.load(path)
        room = next(obj for obj in reloaded if obj.id == "OBJ-ROOM-001")
        assert room.state == "approved"
        assert room.review.approved is True
        assert room.review.reviewer == "engineer@sdtl.local"

    def test_approve_unknown_object_raises(self, tmp_path: Path) -> None:
        queue = ReviewQueue()
        path = queue.save([make_room()], tmp_path / "queue.json")

        with pytest.raises(ValueError, match="No object"):
            queue.approve(path, "OBJ-MISSING", "engineer@sdtl.local")


class TestThreeDGenerationStage:
    def test_generates_gltf_for_approved_objects(self, tmp_path: Path) -> None:
        room = make_room()
        room.approve("engineer@sdtl.local")
        foundation = make_foundation()
        foundation.approve("engineer@sdtl.local")

        result = ThreeDGenerationStage().run([room, foundation], tmp_path / "models")

        assert {item.object_id for item in result.generated} == {room.id, foundation.id}
        for item in result.generated:
            assert item.gltf_path.is_file()
            manifest = json.loads(item.gltf_path.read_text(encoding="utf-8"))
            assert manifest["asset"]["version"] == "2.0"
        assert result.skipped == []

    def test_skips_unapproved_object_without_failing_batch(self, tmp_path: Path) -> None:
        approved_room = make_room("OBJ-ROOM-002")
        approved_room.approve("engineer@sdtl.local")
        pending_room = make_room("OBJ-ROOM-003")

        result = ThreeDGenerationStage().run(
            [approved_room, pending_room], tmp_path / "models"
        )

        assert [item.object_id for item in result.generated] == ["OBJ-ROOM-002"]
        assert result.skipped == [
            {"object_id": "OBJ-ROOM-003", "reason": "object is not approved (state=proposal)"}
        ]

    def test_skips_object_type_without_generator(self, tmp_path: Path) -> None:
        fence = make_fence()
        fence.approve("engineer@sdtl.local")

        result = ThreeDGenerationStage().run([fence], tmp_path / "models")

        assert result.generated == []
        assert result.skipped == [
            {
                "object_id": "OBJ-FENCE-001",
                "reason": "no 3D generator implemented for Fence",
            }
        ]


class TestQuantityTakeoffBuilder:
    def test_aggregates_count_area_and_volume_per_type(self) -> None:
        room = make_room()
        room.approve("engineer@sdtl.local")
        room.activate()
        foundation = make_foundation()
        foundation.approve("engineer@sdtl.local")

        report = QuantityTakeoffBuilder().build([room, foundation])

        rooms = report["quantity_takeoff"]["ElectricalRoom"]
        assert rooms["count"] == 1
        assert rooms["total_length_m"] == 20.0
        assert rooms["total_area_m2"] == pytest.approx(240.0)
        assert rooms["total_volume_m3"] == pytest.approx(720.0)

        foundations = report["quantity_takeoff"]["Foundation"]
        assert foundations["count"] == 1
        assert foundations["total_volume_m3"] == pytest.approx(40.0)

    def test_pending_proposals_are_excluded(self) -> None:
        pending_room = make_room()

        report = QuantityTakeoffBuilder().build([pending_room])

        assert report["quantity_takeoff"] == {}

    def test_object_missing_dimensions_is_reported_not_silently_dropped(self) -> None:
        trench = CableTrench(
            id="OBJ-TRENCH-001",
            source_geometry="GEO-TRENCH-001",
            dimensions=[],
            source_pdf="SE-PI-PL-OC-903.pdf",
            page=1,
        )
        trench.approve("engineer@sdtl.local")

        report = QuantityTakeoffBuilder().build([trench])

        trenches = report["quantity_takeoff"]["CableTrench"]
        assert trenches["count"] == 1
        assert trenches["objects_missing_dimensions"] == ["OBJ-TRENCH-001"]
