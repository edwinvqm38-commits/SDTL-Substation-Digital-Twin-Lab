from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.transmission_line import ConductorSpan, GeoPoint, Tower


def make_tower(**overrides) -> Tower:
    defaults = dict(
        id="TWR-001",
        source_dataset="towers.csv:row=2",
        name="Torre 1",
        tower_type="suspension",
        location=GeoPoint(latitude=-3.5, longitude=-80.4, elevation_m=25.0),
        height_m=35.0,
    )
    defaults.update(overrides)
    return Tower(**defaults)


def test_tower_starts_as_a_proposal() -> None:
    tower = make_tower()

    assert tower.state == "proposal"
    assert tower.review.approved is False


def test_tower_rejects_out_of_range_coordinates() -> None:
    with pytest.raises(ValidationError):
        GeoPoint(latitude=95.0, longitude=-80.4)


def test_tower_rejects_non_positive_height() -> None:
    with pytest.raises(ValidationError):
        make_tower(height_m=0)


def test_approve_then_activate_tower() -> None:
    tower = make_tower()

    tower.approve("engineer@sdtl.local")
    assert tower.state == "approved"
    assert tower.review.approved is True

    tower.activate()
    assert tower.state == "active"


def test_cannot_activate_without_approval() -> None:
    tower = make_tower()

    with pytest.raises(ValueError, match="approval"):
        tower.activate()


def test_cannot_approve_twice() -> None:
    tower = make_tower()
    tower.approve("engineer@sdtl.local")

    with pytest.raises(ValueError, match="proposal"):
        tower.approve("engineer@sdtl.local")


def test_conductor_span_requires_two_different_towers() -> None:
    with pytest.raises(ValidationError, match="different towers"):
        ConductorSpan(
            id="SPAN-001",
            source_dataset="spans.csv:row=2",
            from_tower_id="TWR-001",
            to_tower_id="TWR-001",
            conductor_type="ACSR 400mm2",
        )


def test_conductor_span_starts_as_a_proposal() -> None:
    span = ConductorSpan(
        id="SPAN-001",
        source_dataset="spans.csv:row=2",
        from_tower_id="TWR-001",
        to_tower_id="TWR-002",
        conductor_type="ACSR 400mm2",
    )

    assert span.state == "proposal"
    assert span.sag_m is None
