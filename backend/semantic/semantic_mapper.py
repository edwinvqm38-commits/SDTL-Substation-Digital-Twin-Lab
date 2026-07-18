from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.cad_reader import CADLayerAnalysis, CADProjectLayerReport

from .semantic_models import (
    SDTLElementConcept,
    SemanticLayerMapping,
    SemanticMappingReport,
    SemanticRule,
    SemanticRuleSet,
)


class SemanticMapper:
    """Map exact CAD layer names through an external, versioned rule catalog."""

    DEFAULT_RULES_PATH = Path(__file__).with_name("layer_rules.json")

    def __init__(self, rules_path: str | Path | None = None) -> None:
        self.rules_path = Path(rules_path or self.DEFAULT_RULES_PATH)
        self.rule_set = self.load_rules(self.rules_path)
        self._concepts = {
            concept.concept_id: concept for concept in self.rule_set.concepts
        }
        self._rules = {rule.cad_layer: rule for rule in self.rule_set.rules}

    @staticmethod
    def load_rules(path: str | Path) -> SemanticRuleSet:
        """Read and validate a semantic rule catalog from JSON."""

        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"Semantic rules file not found: {source}")
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid semantic rules JSON: {source}") from error
        return SemanticRuleSet.model_validate(payload)

    def map_report(
        self,
        layer_report: CADProjectLayerReport,
    ) -> SemanticMappingReport:
        """Map a layer analysis while separating accepted and reviewable results."""

        mapped: dict[str, SemanticLayerMapping] = {}
        review_required: dict[str, SemanticLayerMapping] = {}
        unclassified: list[str] = []

        for layer_name, layer in layer_report.layers.items():
            rule = self._rules.get(layer_name)
            if rule is None:
                unclassified.append(layer_name)
                continue

            concept = self._concepts[rule.concept_id]
            result = self._evaluate_rule(layer, rule, concept)
            if result.validation_status == "mapped":
                mapped[layer_name] = result
            else:
                review_required[layer_name] = result

        concepts_found = sorted(
            {result.concept for result in mapped.values()}, key=str.casefold
        )
        return SemanticMappingReport(
            generated_at=datetime.now(timezone.utc),
            version=self.rule_set.version,
            layers_analyzed=layer_report.total_layers,
            concepts_found=concepts_found,
            mapped_layers=dict(sorted(mapped.items(), key=self._sort_layer)),
            review_required_layers=dict(
                sorted(review_required.items(), key=self._sort_layer)
            ),
            unclassified_layers=sorted(unclassified, key=str.casefold),
            metadata={
                "source_layer_report_generated_at": (
                    layer_report.generated_at.isoformat()
                ),
                "source_documents": layer_report.total_documents,
                "rules_file": str(self.rules_path),
                "rules_loaded": len(self.rule_set.rules),
                "minimum_confidence": self.rule_set.minimum_confidence,
                "acceptance_policy": (
                    "exact layer rule, minimum confidence, and compatible geometry"
                ),
            },
        )

    def map_file(
        self,
        layer_analysis_path: str | Path,
        output_path: str | Path = "semantic_mapping.json",
    ) -> SemanticMappingReport:
        """Validate a layer report, map it, and save the semantic report."""

        source = Path(layer_analysis_path)
        if not source.is_file():
            raise FileNotFoundError(f"Layer analysis file not found: {source}")
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid layer analysis JSON: {source}") from error

        layer_report = CADProjectLayerReport.model_validate(payload)
        report = self.map_report(layer_report)
        report.metadata["source_layer_report"] = str(source)
        self.save_report(report, output_path)
        return report

    @staticmethod
    def save_report(
        report: SemanticMappingReport,
        path: str | Path = "semantic_mapping.json",
    ) -> Path:
        """Serialize a semantic mapping report as UTF-8 JSON."""

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return destination

    def _evaluate_rule(
        self,
        layer: CADLayerAnalysis,
        rule: SemanticRule,
        concept: SDTLElementConcept,
    ) -> SemanticLayerMapping:
        observed = set(layer.entity_types)
        expected = set(concept.expected_geometry)
        matched_geometry = sorted(observed & expected)
        warnings: list[str] = []

        if rule.confidence < self.rule_set.minimum_confidence:
            warnings.append(
                "Rule confidence is below the configured acceptance threshold"
            )
        if layer.total_entities == 0:
            warnings.append("Layer is declared but contains no modelspace entities")
        elif expected and not matched_geometry:
            warnings.append(
                "Observed DXF entity types do not match the concept geometry"
            )

        status = "review_required" if warnings else "mapped"
        return SemanticLayerMapping(
            cad_layer=layer.layer_name,
            concept_id=concept.concept_id,
            concept=concept.name,
            discipline=concept.discipline,
            category=concept.category,
            confidence=rule.confidence,
            validation_status=status,
            total_entities=layer.total_entities,
            observed_entity_types=layer.entity_types,
            matched_geometry=matched_geometry,
            source_documents=layer.source_documents,
            notes=rule.notes,
            warnings=warnings,
        )

    @staticmethod
    def _sort_layer(item: tuple[str, SemanticLayerMapping]) -> str:
        return item[0].casefold()
