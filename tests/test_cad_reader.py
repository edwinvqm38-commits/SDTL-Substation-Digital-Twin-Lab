from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.cad_reader import CADDocument, CADReportBuilder, DXFReader


DXF_PATH = Path(
    "data/DXF_TEST/"
    "SE-PI-PL-OC-330_B Canaletas y Ductos Para Cables Eléctricos - Planta.Rev B.dxf"
)


@pytest.fixture(scope="module")
def cad_document() -> CADDocument:
    return DXFReader().read(DXF_PATH, document_id="OC-330")


def test_reads_oc330_dxf_with_original_metadata(cad_document: CADDocument) -> None:
    assert cad_document.document_id == "OC-330"
    assert cad_document.version == "AC1032"
    assert cad_document.units == "in"
    assert cad_document.metadata["insertion_units_code"] == 1
    assert cad_document.statistics.total_entities == 1034


def test_preserves_cable_trench_layer(cad_document: CADDocument) -> None:
    layer_names = {layer.name for layer in cad_document.layers}

    assert len(layer_names) == 39
    assert "OC_CANALETA" in layer_names


def test_extracts_line_with_exact_coordinates(cad_document: CADDocument) -> None:
    line = next(
        entity
        for entity in cad_document.entities
        if entity.entity_type == "LINE" and entity.layer == "OC_CANALETA"
    )

    assert line.mapping_status == "supported"
    assert line.entity_id == f"OC-330:{line.attributes['handle']}"
    assert line.coordinates["start"]["x"] == pytest.approx(98.23495943643684)
    assert line.coordinates["start"]["z"] == 0.0
    assert line.properties["planar_length"] > 0


def test_extracts_mtext_without_losing_raw_content(cad_document: CADDocument) -> None:
    mtext = next(
        entity for entity in cad_document.entities if entity.entity_type == "MTEXT"
    )

    assert mtext.mapping_status == "supported"
    assert mtext.attributes["text"]
    assert mtext.attributes["raw_text"]
    assert "insert" in mtext.coordinates


def test_extracts_insert_and_block_reference(cad_document: CADDocument) -> None:
    insert = next(
        entity for entity in cad_document.entities if entity.entity_type == "INSERT"
    )

    assert insert.mapping_status == "supported"
    assert insert.properties["block_name"]
    assert insert.coordinates["insert"]
    assert isinstance(insert.attributes["attached_attributes"], list)
    assert cad_document.statistics.entity_types["INSERT"] == 74


@pytest.mark.parametrize(
    "entity_type",
    ["LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "TEXT", "MTEXT", "INSERT"],
)
def test_maps_every_initially_supported_type(
    cad_document: CADDocument,
    entity_type: str,
) -> None:
    entity = next(
        item for item in cad_document.entities if item.entity_type == entity_type
    )

    assert entity.mapping_status == "supported"
    assert entity.coordinates
    assert entity.attributes["dxf_attributes"]["handle"]


def test_preserves_unsupported_entities(cad_document: CADDocument) -> None:
    unsupported = [
        entity
        for entity in cad_document.entities
        if entity.mapping_status == "unsupported"
    ]

    assert len(unsupported) == 175
    assert {entity.entity_type for entity in unsupported} == {
        "DIMENSION",
        "MULTILEADER",
        "HATCH",
        "LEADER",
    }
    assert all(entity.attributes["handle"] for entity in unsupported)
    assert all(entity.properties["dxf_attributes"] for entity in unsupported)


def test_all_entities_keep_unique_cad_traceability(cad_document: CADDocument) -> None:
    entity_ids = [entity.entity_id for entity in cad_document.entities]

    assert len(entity_ids) == len(set(entity_ids))
    assert all(entity.source_type == "DXF" for entity in cad_document.entities)
    assert all(entity.layer for entity in cad_document.entities)


def test_cad_document_is_json_serializable(cad_document: CADDocument) -> None:
    payload = json.loads(cad_document.model_dump_json())

    assert len(payload["entities"]) == 1034
    assert payload["entities"][0]["source_type"] == "DXF"


def test_cad_report_contains_supported_and_unsupported_counts(
    cad_document: CADDocument,
    tmp_path: Path,
) -> None:
    report_path = CADReportBuilder().build(cad_document, tmp_path / "cad_report.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["document"] == "OC-330"
    assert report["units"] == "in"
    assert "OC_CANALETA" in report["layers"]
    assert report["supported_entities"] == 859
    assert report["unsupported_entities"] == 175
    assert report["unsupported_types"]["MULTILEADER"] == 62
