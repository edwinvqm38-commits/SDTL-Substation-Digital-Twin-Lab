from __future__ import annotations

import base64
import json

from backend.geometry_3d import GLTFExporter, RoomGenerator
from backend.sdtl_core.entities import ElectricalRoom


def make_model():
    room = ElectricalRoom(
        id="CIV-ROOM-001",
        source_geometry="GEO-ROOM-001",
        dimensions={"length": 12, "width": 8, "height": 4},
        properties={"semantic_scores": {"final": 0.93}},
        source_pdf="SE-PI-PL-OC-700.pdf",
        page=2,
    )
    room.approve("engineer@sdtl.local")
    return RoomGenerator().generate(room)


def test_sdtl_metadata_is_exported() -> None:
    metadata = GLTFExporter().prepare(make_model())["extras"]["metadata"]

    assert metadata["state"] == "approved"
    assert metadata["confidence"] == 0.93
    assert metadata["dimensions"] == {"length": 12.0, "width": 8.0, "height": 4.0}


def test_sdtl_id_is_preserved() -> None:
    manifest = GLTFExporter().prepare(make_model())

    assert manifest["extras"]["metadata"]["sdtl_id"] == "CIV-ROOM-001"


def test_source_pdf_and_page_are_preserved() -> None:
    metadata = GLTFExporter().prepare(make_model())["extras"]["metadata"]

    assert metadata["source_pdf"] == "SE-PI-PL-OC-700.pdf"
    assert metadata["page"] == 2


def test_object_type_is_preserved() -> None:
    manifest = GLTFExporter().prepare(make_model())

    assert manifest["extras"]["metadata"]["object_type"] == "ElectricalRoom"


def test_gltf_manifest_contains_standard_geometry_sections() -> None:
    manifest = GLTFExporter().prepare(make_model())

    assert manifest["asset"] == {"version": "2.0", "generator": "SDTL v1.9.5"}
    assert manifest["scenes"][manifest["scene"]]["nodes"] == [0]
    assert manifest["buffers"][0]["byteLength"] > 0
    assert manifest["bufferViews"]
    assert manifest["accessors"]


def test_object3d_maintains_source_relationship() -> None:
    model = make_model()

    assert model.source_sdtl_object == "CIV-ROOM-001"
    assert model.traceability["source_geometry"] == "GEO-ROOM-001"


def test_every_gltf_mesh_references_the_sdtl_object() -> None:
    manifest = GLTFExporter().prepare(make_model())

    assert all(
        mesh["extras"]["metadata"]["sdtl_id"] == "CIV-ROOM-001"
        for mesh in manifest["meshes"]
    )
    assert manifest["meshes"][0]["extras"]["metadata"]["component_name"] == "Floor"


def test_gltf_json_is_serializable() -> None:
    payload = json.loads(GLTFExporter().export_json(make_model()))

    assert payload["extras"]["metadata"]["object_type"] == "ElectricalRoom"


def test_embedded_buffer_matches_declared_length() -> None:
    manifest = GLTFExporter().prepare(make_model())
    uri = manifest["buffers"][0]["uri"]
    binary = base64.b64decode(uri.split(",", maxsplit=1)[1])

    assert uri.startswith("data:application/octet-stream;base64,")
    assert len(binary) == manifest["buffers"][0]["byteLength"]


def test_mesh_primitive_uses_position_normal_and_indices_accessors() -> None:
    manifest = GLTFExporter().prepare(make_model())
    primitive = manifest["meshes"][0]["primitives"][0]

    assert set(primitive["attributes"]) == {"POSITION", "NORMAL"}
    assert isinstance(primitive["indices"], int)
    assert primitive["mode"] == 4


def test_export_file_creates_loadable_gltf_document(tmp_path) -> None:
    path = GLTFExporter().export_file(make_model(), tmp_path / "room.gltf")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.suffix == ".gltf"
    assert payload["asset"]["version"] == "2.0"
