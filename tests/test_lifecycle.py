from __future__ import annotations

from datetime import datetime, timezone

from backend.core.models import (
    LifecycleEvent,
    LifecycleState,
    ObjectVersion,
    SDTLObject,
)


def test_lifecycle_state_creation() -> None:
    state = LifecycleState(
        state_id="commissioned",
        name="Commissioned",
        description="Asset released for normal operation",
    )

    assert state.state_id == "commissioned"
    assert state.name == "Commissioned"


def test_lifecycle_state_transition() -> None:
    transition = LifecycleEvent(
        event_id="LCE-001",
        timestamp=datetime(2026, 7, 17, 14, 30, tzinfo=timezone.utc),
        state_from="installed",
        state_to="commissioned",
        description="Commissioning tests completed successfully",
        responsible="Commissioning Team",
    )

    assert transition.state_from == "installed"
    assert transition.state_to == "commissioned"
    assert transition.responsible == "Commissioning Team"


def test_object_version_creation() -> None:
    version = ObjectVersion(
        version_id="VER-001",
        created_date=datetime(2026, 7, 17, 15, 0, tzinfo=timezone.utc),
        author="SDTL Engineering",
        description="Updated equipment geometry",
        change_type="geometry_changed",
    )

    assert version.version_id == "VER-001"
    assert version.change_type == "geometry_changed"


def test_sdtl_object_with_lifecycle_history() -> None:
    installed = LifecycleState(
        state_id="installed",
        name="Installed",
        description="Asset installed at its final location",
    )
    transition = LifecycleEvent(
        event_id="LCE-002",
        timestamp=datetime(2026, 7, 17, 16, 0, tzinfo=timezone.utc),
        state_from="construction",
        state_to="installed",
        description="Installation accepted after inspection",
        responsible="Site Supervisor",
    )
    version = ObjectVersion(
        version_id="VER-002",
        created_date=datetime(2026, 7, 17, 16, 5, tzinfo=timezone.utc),
        author="SDTL Engineering",
        description="Recorded installation state",
        change_type="status_changed",
    )

    obj = SDTLObject(
        id="TR-001",
        object_type="power_transformer",
        category="electrical",
        name="220/60 kV Power Transformer",
        lifecycle_states=[installed],
        history=[transition],
        versions=[version],
    )

    assert obj.lifecycle_states[0].state_id == "installed"
    assert obj.history[0].state_to == "installed"
    assert obj.versions[0].change_type == "status_changed"
