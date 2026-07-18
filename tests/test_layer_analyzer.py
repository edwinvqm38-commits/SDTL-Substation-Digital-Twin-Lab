from __future__ import annotations

import json
from pathlib import Path

import ezdxf
import pytest

from backend.cad_reader import (
    CADLayerAnalyzer,
    CADProjectLayerReport,
)


@pytest.fixture()
def dxf_project(tmp_path: Path) -> Path:
    first = ezdxf.new("R2018", setup=True)
    first.layers.add("OC_CANALETA")
    first.layers.add("OC_MURO")
    first.modelspace().add_line(
        (0, 0, 0),
        (10, 0, 0),
        dxfattribs={"layer": "OC_CANALETA"},
    )
    first.modelspace().add_lwpolyline(
        [(0, 0), (10, 0), (10, 5)],
        dxfattribs={"layer": "OC_CANALETA"},
    )
    first.modelspace().add_mtext(
        "Canaleta principal",
        dxfattribs={"layer": "OC_MURO"},
    )
    first.saveas(tmp_path / "civil_a.dxf")

    second = ezdxf.new("R2018", setup=True)
    second.layers.add("OC_CANALETA")
    second.layers.add("OC_DUCTOS")
    second.modelspace().add_line(
        (0, 0, 0),
        (0, 8, 0),
        dxfattribs={"layer": "OC_CANALETA"},
    )
    second.modelspace().add_circle(
        (5, 5, 0),
        radius=2,
        dxfattribs={"layer": "OC_DUCTOS"},
    )
    second.saveas(tmp_path / "civil_b.dxf")
    return tmp_path


@pytest.fixture()
def layer_report(dxf_project: Path) -> CADProjectLayerReport:
    return CADLayerAnalyzer(handles_sample_size=2).analyze_directory(dxf_project)


def test_reads_multiple_dxf_documents(layer_report: CADProjectLayerReport) -> None:
    assert layer_report.total_documents == 2
    assert len(layer_report.global_statistics["documents"]) == 2


def test_detects_oc_layers_and_counts_entities(
    layer_report: CADProjectLayerReport,
) -> None:
    assert {name for name in layer_report.layers if name.startswith("OC_")} == {
        "OC_CANALETA",
        "OC_DUCTOS",
        "OC_MURO",
    }
    canaleta = layer_report.layers["OC_CANALETA"]
    assert canaleta.total_entities == 3
    assert canaleta.entity_types == {"LINE": 2, "LWPOLYLINE": 1}
    assert canaleta.geometry_types == {"line": 2, "polyline": 1}


def test_preserves_layer_document_and_handle_traceability(
    layer_report: CADProjectLayerReport,
) -> None:
    canaleta = layer_report.layers["OC_CANALETA"]

    assert canaleta.source_documents == ["civil_a.dxf", "civil_b.dxf"]
    assert len(canaleta.handles_sample) == 2
    assert all(":" in entity_id for entity_id in canaleta.handles_sample)


def test_includes_declared_layers_without_entities(
    layer_report: CADProjectLayerReport,
) -> None:
    assert "Defpoints" in layer_report.layers
    assert layer_report.layers["Defpoints"].total_entities == 0


def test_serializes_and_saves_pydantic_report(
    layer_report: CADProjectLayerReport,
    tmp_path: Path,
) -> None:
    analyzer = CADLayerAnalyzer()
    output = analyzer.save_report(layer_report, tmp_path / "layer_analysis.json")
    payload = json.loads(output.read_text(encoding="utf-8"))
    reconstructed = CADProjectLayerReport.model_validate(payload)

    assert payload["total_documents"] == 2
    assert payload["layers"]["OC_CANALETA"]["total_entities"] == 3
    assert reconstructed.layers["OC_DUCTOS"].entity_types == {"CIRCLE": 1}


def test_empty_directory_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No DXF documents"):
        CADLayerAnalyzer().analyze_directory(tmp_path)


def test_negative_handle_sample_size_is_rejected() -> None:
    with pytest.raises(ValueError, match="zero or greater"):
        CADLayerAnalyzer(handles_sample_size=-1)
