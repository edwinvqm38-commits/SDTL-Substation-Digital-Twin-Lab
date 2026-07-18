from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.cad_reader import CADLayerAnalysis, CADProjectLayerReport
from backend.semantic import (
    SemanticMapper,
    SemanticMappingReport,
    SemanticRuleSet,
)


def _layer_report() -> CADProjectLayerReport:
    return CADProjectLayerReport(
        generated_at=datetime.now(timezone.utc),
        total_documents=2,
        total_layers=3,
        layers={
            "OC_CANALETA": CADLayerAnalysis(
                layer_name="OC_CANALETA",
                total_entities=3,
                entity_types={"LINE": 2, "LWPOLYLINE": 1},
                source_documents=["civil_a.dxf", "civil_b.dxf"],
                geometry_types={"line": 2, "polyline": 1},
                handles_sample=["civil_a:A1"],
            ),
            "OC_CERCO": CADLayerAnalysis(
                layer_name="OC_CERCO",
                total_entities=1,
                entity_types={"LINE": 1},
                source_documents=["civil_a.dxf"],
                geometry_types={"line": 1},
                handles_sample=["civil_a:B1"],
            ),
            "CUSTOM_UNKNOWN": CADLayerAnalysis(
                layer_name="CUSTOM_UNKNOWN",
                total_entities=1,
                entity_types={"LINE": 1},
                source_documents=["civil_b.dxf"],
                geometry_types={"line": 1},
                handles_sample=["civil_b:C1"],
            ),
        },
        global_statistics={"total_entities": 5},
    )


def test_loads_external_json_rules() -> None:
    mapper = SemanticMapper()

    assert isinstance(mapper.rule_set, SemanticRuleSet)
    assert mapper.rule_set.version == "0.1"
    assert any(rule.cad_layer == "OC_CANALETA" for rule in mapper.rule_set.rules)


def test_maps_known_layers_to_engineering_concepts() -> None:
    report = SemanticMapper().map_report(_layer_report())

    cable_trench = report.mapped_layers["OC_CANALETA"]
    assert cable_trench.concept == "CableTrench"
    assert cable_trench.confidence == 0.95
    assert cable_trench.matched_geometry == ["LINE", "LWPOLYLINE"]
    assert cable_trench.source_documents == ["civil_a.dxf", "civil_b.dxf"]
    assert report.mapped_layers["OC_CERCO"].concept == "PerimeterFence"


def test_keeps_unknown_layers_unclassified() -> None:
    report = SemanticMapper().map_report(_layer_report())

    assert report.unclassified_layers == ["CUSTOM_UNKNOWN"]
    assert "CUSTOM_UNKNOWN" not in report.mapped_layers


def test_geometry_mismatch_requires_review() -> None:
    layer_report = _layer_report()
    layer_report.layers["OC_CANALETA"].entity_types = {"HATCH": 3}

    report = SemanticMapper().map_report(layer_report)

    assert "OC_CANALETA" not in report.mapped_layers
    review = report.review_required_layers["OC_CANALETA"]
    assert review.validation_status == "review_required"
    assert review.warnings


def test_semantic_report_is_pydantic_json_serializable() -> None:
    report = SemanticMapper().map_report(_layer_report())
    payload = json.loads(report.model_dump_json())
    reconstructed = SemanticMappingReport.model_validate(payload)

    assert reconstructed.layers_analyzed == 3
    assert "CableTrench" in reconstructed.concepts_found


def test_generates_semantic_mapping_json(tmp_path: Path) -> None:
    source = tmp_path / "layer_analysis.json"
    source.write_text(_layer_report().model_dump_json(indent=2), encoding="utf-8")
    output = tmp_path / "semantic_mapping.json"

    report = SemanticMapper().map_file(source, output)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert report.version == "0.1"
    assert payload["mapped_layers"]["OC_CANALETA"]["concept"] == "CableTrench"
    assert payload["unclassified_layers"] == ["CUSTOM_UNKNOWN"]
    assert payload["metadata"]["source_layer_report"] == str(source)


def test_rejects_rule_that_contradicts_concept_source_layers() -> None:
    payload = {
        "version": "test",
        "minimum_confidence": 0.8,
        "concepts": [
            {
                "concept_id": "CIV-TEST-001",
                "name": "TestConcept",
                "discipline": "Civil",
                "category": "Test",
                "source_layers": ["OC_EXPECTED"],
                "expected_geometry": ["LINE"],
                "description": "Test concept.",
                "metadata": {},
            }
        ],
        "rules": [
            {
                "cad_layer": "OC_WRONG",
                "concept_id": "CIV-TEST-001",
                "confidence": 0.9,
                "notes": None,
            }
        ],
    }

    with pytest.raises(ValidationError, match="must be declared"):
        SemanticRuleSet.model_validate(payload)
