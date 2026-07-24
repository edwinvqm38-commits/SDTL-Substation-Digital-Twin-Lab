from __future__ import annotations

from pathlib import Path

import pytest

from backend.transmission_line import TransmissionLineImportError, TransmissionLineImporter

TOWERS_CSV = """id,name,tower_type,latitude,longitude,elevation_m,height_m,base_width_m
TWR-001,Torre 1,suspension,-3.500,-80.400,20,35,2.5
TWR-002,Torre 2,tension,-3.505,-80.400,22,38,2.5
"""

SPANS_CSV = """id,from_tower_id,to_tower_id,conductor_type,conductors_per_phase,sag_m
SPAN-001,TWR-001,TWR-002,ACSR 400mm2,2,4.5
"""


def write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_imports_towers_from_csv(tmp_path: Path) -> None:
    towers_path = write(tmp_path, "towers.csv", TOWERS_CSV)

    towers = TransmissionLineImporter().import_towers(towers_path)

    assert [tower.id for tower in towers] == ["TWR-001", "TWR-002"]
    assert towers[0].location.latitude == pytest.approx(-3.5)
    assert towers[0].source_dataset == "towers.csv:row=2"
    assert towers[0].state == "proposal"


def test_imports_spans_referencing_known_towers(tmp_path: Path) -> None:
    towers_path = write(tmp_path, "towers.csv", TOWERS_CSV)
    spans_path = write(tmp_path, "spans.csv", SPANS_CSV)
    importer = TransmissionLineImporter()
    towers = importer.import_towers(towers_path)

    spans = importer.import_spans(spans_path, towers)

    assert spans[0].from_tower_id == "TWR-001"
    assert spans[0].sag_m == pytest.approx(4.5)
    assert spans[0].conductors_per_phase == 2


def test_span_referencing_unknown_tower_is_rejected(tmp_path: Path) -> None:
    towers_path = write(tmp_path, "towers.csv", TOWERS_CSV)
    bad_spans = write(
        tmp_path,
        "spans.csv",
        "id,from_tower_id,to_tower_id,conductor_type\nSPAN-001,TWR-001,TWR-999,ACSR 400mm2\n",
    )
    importer = TransmissionLineImporter()
    towers = importer.import_towers(towers_path)

    with pytest.raises(TransmissionLineImportError, match="unknown tower id"):
        importer.import_spans(bad_spans, towers)


def test_missing_required_column_is_rejected(tmp_path: Path) -> None:
    bad_towers = write(
        tmp_path,
        "towers.csv",
        "id,name,tower_type,latitude,height_m\nTWR-001,Torre 1,suspension,-3.5,35\n",
    )

    with pytest.raises(TransmissionLineImportError):
        TransmissionLineImporter().import_towers(bad_towers)


def test_invalid_tower_type_is_rejected(tmp_path: Path) -> None:
    bad_towers = write(
        tmp_path,
        "towers.csv",
        "id,name,tower_type,latitude,longitude,height_m\n"
        "TWR-001,Torre 1,not_a_real_type,-3.5,-80.4,35\n",
    )

    with pytest.raises(TransmissionLineImportError):
        TransmissionLineImporter().import_towers(bad_towers)


def test_empty_towers_file_is_rejected(tmp_path: Path) -> None:
    empty = write(
        tmp_path, "towers.csv", "id,name,tower_type,latitude,longitude,height_m\n"
    )

    with pytest.raises(TransmissionLineImportError, match="no tower rows"):
        TransmissionLineImporter().import_towers(empty)
