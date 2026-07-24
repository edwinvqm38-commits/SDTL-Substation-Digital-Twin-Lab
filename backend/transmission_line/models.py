from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.sdtl_core.entities import HumanReview

AssetLifecycleState = Literal["proposal", "approved", "active", "modified", "retired"]
TowerType = Literal["suspension", "tension", "terminal"]


class GeoPoint(BaseModel):
    """WGS84 geographic position used to place transmission line assets."""

    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    elevation_m: float = 0.0


class TransmissionAsset(BaseModel):
    """Structured (non-PDF) engineering asset for the transmission-line digital twin.

    Towers and spans come from an engineer-authored CSV, not an AI-guessed
    candidate, but they still go through the same explicit-human-approval
    lifecycle CivilObject uses for drawing-derived objects (see
    backend/sdtl_core/entities/civil_objects.py) so a digital twin built
    from a spreadsheet is never treated as more authoritative than one built
    from an interpreted drawing -- both require a named reviewer before they
    can generate 3D geometry or count as "active".
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str
    source_dataset: str
    state: AssetLifecycleState = "proposal"
    review: HumanReview = Field(default_factory=HumanReview)

    _allowed_transitions = {
        "proposal": {"approved"},
        "approved": {"active"},
        "active": {"modified", "retired"},
        "modified": {"active", "retired"},
        "retired": set(),
    }

    def approve(self, reviewer: str) -> None:
        """Record the required human decision and approve this proposal."""

        if not reviewer.strip():
            raise ValueError("A reviewer is required to approve a transmission line asset")
        if self.state != "proposal":
            raise ValueError("Only an asset proposal can be approved")
        self.review = self.review.model_copy(update={"approved": True, "reviewer": reviewer})
        self._transition_to("approved")

    def activate(self) -> None:
        """Activate an asset only after an explicit human approval."""

        if not self.review.approved or not self.review.reviewer:
            raise ValueError("Human approval is required before activation")
        self._transition_to("active")

    def mark_modified(self) -> None:
        """Mark an active asset as modified."""

        self._transition_to("modified")

    def retire(self) -> None:
        """Retire an active or modified asset."""

        self._transition_to("retired")

    def _transition_to(self, target: AssetLifecycleState) -> None:
        if target not in self._allowed_transitions[self.state]:
            raise ValueError(f"Invalid transmission line asset transition: {self.state} -> {target}")
        self.state = target


class Tower(TransmissionAsset):
    """Transmission tower positioned by real-world GPS coordinates."""

    type: Literal["Tower"] = "Tower"
    name: str
    tower_type: TowerType
    location: GeoPoint
    height_m: float = Field(gt=0)
    base_width_m: float | None = Field(default=None, gt=0)
    properties: dict[str, Any] = Field(default_factory=dict)


class ConductorSpan(TransmissionAsset):
    """Conductor run between two towers of the same transmission line."""

    type: Literal["ConductorSpan"] = "ConductorSpan"
    from_tower_id: str
    to_tower_id: str
    conductor_type: str
    conductors_per_phase: int = Field(default=1, ge=1)
    sag_m: float | None = Field(default=None, gt=0)
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("to_tower_id")
    @classmethod
    def _validate_endpoints_differ(cls, value: str, info: Any) -> str:
        from_tower_id = info.data.get("from_tower_id")
        if from_tower_id is not None and value == from_tower_id:
            raise ValueError("A conductor span must connect two different towers")
        return value
