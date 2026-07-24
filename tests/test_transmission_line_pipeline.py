from __future__ import annotations

from pathlib import Path

import pytest

from backend.transmission_line import TransmissionLinePipeline

TOWERS_CSV = """id,name,tower_type,latitude,longitude,elevation_m,height_m,base_width_m
TWR-001,Torre 1,suspension,-3.5000,-80.4000,20,35,2.5
TWR-002,Torre 2,tension,-3.5030,-80.4000,22,38,2.5
TWR-003,Torre 3,suspension,-3.5060,-80.4000,24,35,2.5
"""

SPANS_CSV = """id,from_tower_id,to_tower_id,conductor_type,conductors_per_phase,sag_m
SPAN-001,TWR-001,TWR-002,ACSR 400mm2,2,5.0
SPAN-002,TWR-002,TWR-003,ACSR 400mm2,2,5.0
"""


def write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_import_projects_every_tower_to_a_local_position(tmp_path: Path) -> None:
    towers_path = write(tmp_path, "towers.csv", TOWERS_CSV)
    spans_path = write(tmp_path, "spans.csv", SPANS_CSV)

    imported = TransmissionLinePipeline().import_line(towers_path, spans_path)

    assert imported.towers[0].properties["position"] == pytest.approx([0.0, 0.0, 0.0])
    for tower in imported.towers:
        assert "position" in tower.properties
    assert len(imported.spans) == 2


def test_unapproved_assets_are_skipped_not_failed(tmp_path: Path) -> None:
    towers_path = write(tmp_path, "towers.csv", TOWERS_CSV)
    spans_path = write(tmp_path, "spans.csv", SPANS_CSV)
    pipeline = TransmissionLinePipeline()
    imported = pipeline.import_line(towers_path, spans_path)

    result = pipeline.generate_3d(imported.towers, imported.spans, tmp_path / "out")

    assert result.generated == []
    assert len(result.skipped) == len(imported.towers) + len(imported.spans)


def test_approved_towers_and_spans_generate_gltf(tmp_path: Path) -> None:
    towers_path = write(tmp_path, "towers.csv", TOWERS_CSV)
    spans_path = write(tmp_path, "spans.csv", SPANS_CSV)
    pipeline = TransmissionLinePipeline()
    imported = pipeline.import_line(towers_path, spans_path)

    for tower in imported.towers:
        tower.approve("engineer@sdtl.local")
    for span in imported.spans:
        span.approve("engineer@sdtl.local")

    result = pipeline.generate_3d(imported.towers, imported.spans, tmp_path / "out")

    assert len(result.generated) == len(imported.towers) + len(imported.spans)
    assert result.skipped == []
    for generated in result.generated:
        assert generated.gltf_path.exists()
