from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class HumanReview(BaseModel):
    """Human approval record required before an SDTL proposal can become active."""

    model_config = ConfigDict(extra="forbid")

    required: bool = True
    approved: bool = False
    reviewer: str | None = None


class ObjectProposal(BaseModel):
    """Auditable proposal generated from an engineering candidate for review."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    candidate_source: str = Field(
        validation_alias=AliasChoices("candidate_source", "source_candidate")
    )
    object_type: str
    properties: dict[str, Any] = Field(default_factory=dict)
    geometry_reference: str
    traceability: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    review_status: str = Field(
        default="pending_review",
        validation_alias=AliasChoices("review_status", "status"),
    )
    state: str = "proposal"
    review: HumanReview = Field(default_factory=HumanReview)

    @property
    def source_candidate(self) -> str:
        """Compatibility alias used by early v1.8 payload examples."""

        return self.candidate_source

    @property
    def status(self) -> str:
        """Compatibility alias used by early v1.8 payload examples."""

        return self.review_status
