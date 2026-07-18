from __future__ import annotations

import json

from backend.core.models import Dimensions, Geometry, Point3D, SDTLObject


def test_sdtl_object_creation_and_properties() -> None:
    geometry = Geometry(
        position=Point3D(x=10.0, y=20.0, z=0.5),
        dimensions=Dimensions(length=4.0, width=2.0, height=3.0),
        geometry_type="box",
    )

    obj = SDTLObject(
        id="SWT-001",
        object_type="equipment",
        category="electrical",
        name="Disconnect Switch",
        state="installed",
        geometry=geometry,
        properties={
            "voltage_kv": 220,
            "manufacturer": "SDTL Lab",
            "tags": ["civil", "electrical"],
        },
        relations=["BAY-001"],
    )

    assert obj.id == "SWT-001"
    assert obj.geometry is not None
    assert obj.geometry.position.x == 10.0
    assert obj.properties["voltage_kv"] == 220
    assert obj.properties["tags"] == ["civil", "electrical"]


def test_sdtl_object_json_serialization() -> None:
    obj = SDTLObject(
        id="FOUND-001",
        object_type="foundation",
        category="civil",
        name="Transformer Foundation",
        properties={"concrete_grade": "C30", "volume_m3": 12.5},
    )

    serialized = obj.model_dump_json()
    payload = json.loads(serialized)

    assert payload["id"] == "FOUND-001"
    assert payload["properties"]["concrete_grade"] == "C30"
    assert payload["documents"] == []
    assert payload["events"] == []
    assert payload["relations"] == []
