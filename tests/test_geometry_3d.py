from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from backend.core.models import Dimensions, Geometry, Point3D, SDTLObject
from backend.geometry_3d import (
    CableTrenchGenerator,
    FoundationGenerator,
    GLTFExporter,
    Mesh,
    RoomGenerator,
    Transform,
)
from backend.geometry_3d.models import load_material
from backend.sdtl_core.entities import CableTrench, ElectricalRoom, Foundation


def make_room(
    dimensions: dict[str, float] | list[dict[str, object]] | None = None,
    *,
    approved: bool = True,
    properties: dict[str, object] | None = None,
) -> ElectricalRoom:
    room = ElectricalRoom(
        id="CIV-ROOM-001",
        source_geometry="GEO-ROOM-001",
        coordinates=[[10, 20], [22, 28]],
        dimensions=(
            {"length": 12, "width": 8, "height": 4}
            if dimensions is None
            else dimensions
        ),
        properties=properties or {},
        source_pdf="SE-PI-PL-OC-700.pdf",
        page=2,
    )
    if approved:
        room.approve("engineer@sdtl.local")
    return room


def make_foundation(
    dimensions: dict[str, float] | None = None,
) -> Foundation:
    foundation = Foundation(
        id="CIV-FOUND-001",
        source_geometry="GEO-FOUND-001",
        dimensions=dimensions or {"length": 8, "width": 5, "height": 1},
        source_pdf="SE-PI-PL-OC-701.pdf",
        page=3,
    )
    foundation.approve("engineer@sdtl.local")
    return foundation


def make_trench() -> CableTrench:
    trench = CableTrench(
        id="CIV-TRENCH-001",
        source_geometry="GEO-TRENCH-001",
        dimensions={"length": 20, "width": 1.2, "depth": 0.8},
        source_pdf="SE-PI-PL-OC-702.pdf",
        page=4,
    )
    trench.approve("engineer@sdtl.local")
    return trench


def test_electrical_room_generates_engineering_components() -> None:
    model = RoomGenerator().generate(make_room())

    assert model.component_names == [
        "Floor",
        "Wall_1",
        "Wall_2",
        "Wall_3",
        "Wall_4",
        "Roof",
    ]


def test_foundation_generates_closed_footing_mesh() -> None:
    model = FoundationGenerator().generate(make_foundation())
    mesh = model.components[0].mesh

    assert model.component_names == ["Footing"]
    assert len(mesh.vertices) == 8
    assert len(mesh.faces) == 12


def test_cable_trench_generates_open_channel_geometry() -> None:
    model = CableTrenchGenerator().generate(make_trench())

    assert model.component_names == [
        "Channel_Base",
        "Side_Wall_Left",
        "Side_Wall_Right",
    ]
    assert model.metadata["open_channel"] is True
    assert "Roof" not in model.component_names


def test_foundation_vertices_follow_dimensions() -> None:
    mesh = FoundationGenerator().generate(make_foundation()).components[0].mesh

    assert [8.0, 5.0, 1.0] in mesh.vertices
    assert [0.0, 0.0, 0.0] in mesh.vertices


def test_transform_defaults_are_identity() -> None:
    transform = Transform()

    assert transform.position == [0.0, 0.0, 0.0]
    assert transform.rotation == [0.0, 0.0, 0.0]
    assert transform.scale == [1.0, 1.0, 1.0]
    assert transform.apply([2, 3, 4]) == [2.0, 3.0, 4.0]


def test_generator_uses_source_transform() -> None:
    room = make_room(
        properties={
            "position": [10, 0, 20],
            "rotation": [0, 0, 90],
            "scale": [1, 2, 1],
        }
    )
    transform = RoomGenerator().generate(room).transform

    assert transform.position == [10.0, 0.0, 20.0]
    assert transform.rotation == [0.0, 0.0, 90.0]
    assert transform.scale == [1.0, 2.0, 1.0]


def test_concrete_material_is_assigned() -> None:
    model = FoundationGenerator().generate(make_foundation())
    material = model.components[0].material

    assert material.name == "Concrete"
    assert material.density == 2400
    assert material.visual.color == "#808080"


def test_model_preserves_sdtl_traceability() -> None:
    model = RoomGenerator().generate(make_room())

    assert model.source_sdtl_object == "CIV-ROOM-001"
    assert model.traceability == {
        "source_geometry": "GEO-ROOM-001",
        "source_pdf": "SE-PI-PL-OC-700.pdf",
        "page": 2,
    }


def test_object_3d_is_json_serializable() -> None:
    model = RoomGenerator().generate(make_room())
    payload = json.loads(model.model_dump_json())

    assert payload["type"] == "ElectricalRoom"
    assert len(payload["components"]) == 6
    assert payload["components"][0]["mesh"]["vertices"]


def test_object_without_dimensions_is_rejected() -> None:
    room = make_room(dimensions=[])

    with pytest.raises(ValueError, match="missing dimensions"):
        RoomGenerator().generate(room)


def test_negative_dimensions_are_rejected() -> None:
    foundation = make_foundation({"length": -8, "width": 5, "height": 1})

    with pytest.raises(ValueError, match="must be positive"):
        FoundationGenerator().generate(foundation)


def test_transform_applies_scale_rotation_and_position() -> None:
    transform = Transform(
        position=[10, 0, 0],
        rotation=[0, 0, 90],
        scale=[2, 1, 1],
    )

    assert transform.apply([1, 0, 0]) == pytest.approx([10, 2, 0])


def test_room_contains_multiple_independent_meshes() -> None:
    model = RoomGenerator().generate(make_room())

    assert len(model.components) == 6
    assert len({component.mesh.id for component in model.components}) == 6


def test_engineering_material_is_separate_from_mesh_topology() -> None:
    component = RoomGenerator().generate(make_room()).components[0]

    assert "material" not in Mesh.model_fields
    assert component.material.name == "Concrete"
    assert set(Mesh.model_fields) == {"id", "vertices", "faces", "normals", "metadata"}


def test_gltf_exporter_prepares_initial_manifest() -> None:
    manifest = GLTFExporter().prepare(RoomGenerator().generate(make_room()))

    assert manifest["asset"]["version"] == "2.0"
    assert manifest["scene"] == 0
    assert len(manifest["meshes"]) == 6
    assert len(manifest["nodes"]) == 7


def test_gltf_manifest_keeps_future_babylon_compatibility_metadata() -> None:
    exporter = GLTFExporter()
    manifest = json.loads(exporter.export_json(RoomGenerator().generate(make_room())))

    assert manifest["extras"]["future_target"] == "Babylon.js"
    assert manifest["extras"]["source_sdtl_object"] == "CIV-ROOM-001"
    assert manifest["nodes"][0]["rotation"] == [0.0, 0.0, 0.0, 1.0]


def test_unapproved_object_is_rejected() -> None:
    with pytest.raises(ValueError, match="approved"):
        RoomGenerator().generate(make_room(approved=False))


def test_mesh_rejects_face_with_unknown_vertex() -> None:
    with pytest.raises(ValidationError, match="outside the mesh"):
        Mesh(
            id="MESH-BAD",
            vertices=[[0, 0, 0], [1, 0, 0], [0, 1, 0]],
            faces=[[0, 1, 3]],
        )


def test_v18_named_dimension_list_remains_supported() -> None:
    room = make_room(
        dimensions=[
            {"name": "length", "value": 12, "unit": "m"},
            {"name": "width", "value": 8, "unit": "m"},
            {"name": "height", "value": 4, "unit": "m"},
        ]
    )

    assert RoomGenerator().generate(room).metadata["dimensions"] == {
        "length": 12.0,
        "width": 8.0,
        "height": 4.0,
    }


def test_legacy_core_sdtl_object_can_generate_geometry() -> None:
    source = SDTLObject(
        id="CORE-FOUND-001",
        object_type="Foundation",
        category="civil",
        name="Transformer foundation",
        state="approved",
        geometry=Geometry(
            position=Point3D(x=5, y=6, z=0),
            dimensions=Dimensions(length=8, width=5, height=1),
            geometry_type="foundation",
        ),
    )

    model = FoundationGenerator().generate(source)

    assert model.source_sdtl_object == "CORE-FOUND-001"
    assert model.transform.position == [5.0, 6.0, 0.0]


@pytest.mark.parametrize("material_name", ["concrete", "steel", "soil"])
def test_material_catalogs_are_valid(material_name: str) -> None:
    material = load_material(material_name)

    assert material.name
    assert material.visual.color.startswith("#")
