from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SDTLElementConcept(BaseModel):
    """Engineering meaning assigned to one or more traceable CAD layers."""

    model_config = ConfigDict(extra="forbid")

    concept_id: str
    name: str
    discipline: str
    category: str
    source_layers: list[str] = Field(default_factory=list)
    expected_geometry: list[str] = Field(default_factory=list)
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SemanticRule(BaseModel):
    """External rule linking an exact native CAD layer to an SDTL concept."""

    model_config = ConfigDict(extra="forbid")

    cad_layer: str
    concept_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None


class SemanticRuleSet(BaseModel):
    """Versioned catalog of concepts, rules, and semantic acceptance policy."""

    model_config = ConfigDict(extra="forbid")

    version: str
    minimum_confidence: float = Field(ge=0.0, le=1.0)
    concepts: list[SDTLElementConcept] = Field(default_factory=list)
    rules: list[SemanticRule] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> SemanticRuleSet:
        concept_ids = [concept.concept_id for concept in self.concepts]
        if len(concept_ids) != len(set(concept_ids)):
            raise ValueError("Concept IDs must be unique")

        cad_layers = [rule.cad_layer for rule in self.rules]
        if len(cad_layers) != len(set(cad_layers)):
            raise ValueError("Each CAD layer can have only one semantic rule")

        concept_by_id = {
            concept.concept_id: concept for concept in self.concepts
        }
        unknown_concepts = sorted(
            {rule.concept_id for rule in self.rules} - set(concept_ids)
        )
        if unknown_concepts:
            raise ValueError(
                "Semantic rules reference unknown concepts: "
                + ", ".join(unknown_concepts)
            )

        inconsistent_rules = [
            f"{rule.cad_layer}->{rule.concept_id}"
            for rule in self.rules
            if rule.cad_layer not in concept_by_id[rule.concept_id].source_layers
        ]
        if inconsistent_rules:
            raise ValueError(
                "Semantic rule layers must be declared by their concepts: "
                + ", ".join(inconsistent_rules)
            )
        return self


class SemanticLayerMapping(BaseModel):
    """Semantic match with CAD evidence and an explicit validation status."""

    model_config = ConfigDict(extra="forbid")

    cad_layer: str
    concept_id: str
    concept: str
    discipline: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    validation_status: Literal["mapped", "review_required"]
    total_entities: int = Field(ge=0)
    observed_entity_types: dict[str, int] = Field(default_factory=dict)
    matched_geometry: list[str] = Field(default_factory=list)
    source_documents: list[str] = Field(default_factory=list)
    notes: str | None = None
    warnings: list[str] = Field(default_factory=list)


class SemanticMappingReport(BaseModel):
    """Versioned result of mapping project CAD layers to SDTL concepts."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    version: str
    layers_analyzed: int = Field(ge=0)
    concepts_found: list[str] = Field(default_factory=list)
    mapped_layers: dict[str, SemanticLayerMapping] = Field(default_factory=dict)
    review_required_layers: dict[str, SemanticLayerMapping] = Field(
        default_factory=dict
    )
    unclassified_layers: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
