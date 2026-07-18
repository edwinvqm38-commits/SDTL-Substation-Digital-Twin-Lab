from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.core.loader import load_json, load_object, load_project
from backend.core.models import Project, SDTLObject
from backend.core.serializer import save_json, serialize_model


DEMO_PATH = Path(__file__).parents[1] / "data" / "models" / "SE001_demo.json"


def test_load_demo_json() -> None:
    payload = load_json(DEMO_PATH)

    assert payload["project"]["project_id"] == "SE001"
    assert payload["document_sets"][0]["name"] == "Civil"
    assert payload["engineering_documents"][0]["document_id"] == "OC-320_demo"


def test_reconstruct_project_from_demo() -> None:
    project = load_project(DEMO_PATH)

    assert isinstance(project, Project)
    assert project.project_id == "SE001"
    assert project.name == "Subestacion Demo 220kV"
    assert project.voltage_levels[0].value == 220_000


def test_serialize_project_to_valid_json() -> None:
    project = load_project(DEMO_PATH)
    serialized = serialize_model(project)
    payload = json.loads(serialized)

    assert payload["project_id"] == "SE001"
    assert payload["objects"] == ["FOUND-TR01"]


def test_serialized_project_matches_demo_content() -> None:
    demo_payload = load_json(DEMO_PATH)
    project = load_project(DEMO_PATH)

    assert json.loads(serialize_model(project)) == demo_payload["project"]


def test_save_and_reload_project(tmp_path: Path) -> None:
    project = load_project(DEMO_PATH)
    saved_path = tmp_path / "SE001_project.json"

    save_json(project, saved_path)
    reloaded = load_project(saved_path)

    assert reloaded == project


def test_load_sdtl_object_from_demo() -> None:
    obj = load_object(DEMO_PATH)

    assert isinstance(obj, SDTLObject)
    assert obj.id == "FOUND-TR01"
    assert obj.properties["material"] == "concrete"
    assert obj.properties["dimensions"] == {
        "length": 8,
        "width": 5,
        "height": 1,
    }
    assert obj.relationships[0].source_id == "OC-320_demo"
    assert obj.lifecycle_states[0].state_id == "constructed"
    assert obj.spatial_position is not None
    assert obj.spatial_position.coordinate_system is not None
    assert obj.spatial_position.coordinate_system.system == "LOCAL"


def test_load_project_reports_validation_errors(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid_project.json"
    invalid_path.write_text('{"project": {"project_id": "SE-BAD"}}', encoding="utf-8")

    with pytest.raises(ValidationError):
        load_project(invalid_path)
