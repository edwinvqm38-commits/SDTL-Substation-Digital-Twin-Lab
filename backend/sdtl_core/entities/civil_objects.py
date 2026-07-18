from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ObjectLifecycleState = Literal[
    "candidate",
    "proposal",
    "approved",
    "active",
    "modified",
    "retired",
]


class HumanReview(BaseModel):
    """Human approval attached to every generated SDTL civil object."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    required: bool = True
    approved: bool = False
    reviewer: str | None = None


class CivilObject(BaseModel):
    """Persistent civil SDTL object preserving drawing geometry and provenance."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str
    type: str
    source_geometry: str
    coordinates: list[list[float]] = Field(default_factory=list)
    dimensions: dict[str, float] | list[dict[str, Any]] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)
    source_pdf: str
    page: int = Field(ge=1)
    state: ObjectLifecycleState = "proposal"
    review: HumanReview = Field(default_factory=HumanReview)

    _allowed_transitions = {
        "candidate": {"proposal"},
        "proposal": {"approved"},
        "approved": {"active"},
        "active": {"modified", "retired"},
        "modified": {"active", "retired"},
        "retired": set(),
    }

    def approve(self, reviewer: str) -> None:
        """Record the required human decision and approve this proposal."""

        if not reviewer.strip():
            raise ValueError("A reviewer is required to approve an SDTL object")
        if self.state != "proposal":
            raise ValueError("Only an object proposal can be approved")
        self.review = self.review.model_copy(
            update={"approved": True, "reviewer": reviewer}
        )
        self._transition_to("approved")

    def activate(self) -> None:
        """Activate an object only after an explicit human approval."""

        if not self.review.approved or not self.review.reviewer:
            raise ValueError("Human approval is required before activation")
        self._transition_to("active")

    def mark_modified(self) -> None:
        """Mark an active digital object as modified."""

        self._transition_to("modified")

    def retire(self) -> None:
        """Retire an active or modified digital object."""

        self._transition_to("retired")

    def _transition_to(self, target: ObjectLifecycleState) -> None:
        if target not in self._allowed_transitions[self.state]:
            raise ValueError(f"Invalid SDTL object transition: {self.state} -> {target}")
        self.state = target


class ElectricalRoom(CivilObject):
    """Civil enclosure intended for electrical or control equipment."""

    type: Literal["ElectricalRoom"] = "ElectricalRoom"


class CableTrench(CivilObject):
    """Civil trench providing a documented route for electrical cables."""

    type: Literal["CableTrench"] = "CableTrench"


class Foundation(CivilObject):
    """Civil foundation supporting equipment or substation structures."""

    type: Literal["Foundation"] = "Foundation"


class Fence(CivilObject):
    """Civil perimeter or safety fence represented in an engineering drawing."""

    type: Literal["Fence"] = "Fence"


class Road(CivilObject):
    """Civil access or internal road represented in an engineering drawing."""

    type: Literal["Road"] = "Road"
