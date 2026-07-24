from __future__ import annotations

import pytest

from backend.geometry_3d import ConductorSpanGenerator, TowerGenerator
from backend.transmission_line import ConductorSpan, GeoPoint, Tower


def make_tower(**overrides) -> Tower:
    defaults = dict(
        id="TWR-001",
        source_dataset="towers.csv:row=2",
        name="Torre 1",
        tower_type="suspension",
        location=GeoPoint(latitude=-3.5, longitude=-80.4, elevation_m=20.0),
        height_m=30.0,
    )
    defaults.update(overrides)
    tower = Tower(**defaults)
    tower.approve("engineer@sdtl.local")
    return tower


def test_tower_generates_shaft_and_crossarm() -> None:
    model = TowerGenerator().generate(make_tower())

    assert model.type == "Tower"
    assert model.component_names == ["Shaft", "Crossarm"]
    assert model.metadata["height_m"] == 30.0
    assert model.metadata["base_width_assumed"] is True


def test_tower_uses_explicit_base_width_when_given() -> None:
    model = TowerGenerator().generate(make_tower(base_width_m=3.0))

    assert model.metadata["base_width_m"] == 3.0
    assert model.metadata["base_width_assumed"] is False
    shaft_vertices = model.components[0].mesh.vertices
    assert max(point[0] for point in shaft_vertices) == pytest.approx(3.0)


def test_tower_rejects_unapproved_source() -> None:
    tower = Tower(
        id="TWR-002",
        source_dataset="towers.csv:row=3",
        name="Torre 2",
        tower_type="suspension",
        location=GeoPoint(latitude=-3.5, longitude=-80.4),
        height_m=30.0,
    )

    with pytest.raises(ValueError, match="approved"):
        TowerGenerator().generate(tower)


def _positioned_towers() -> tuple[Tower, Tower]:
    start = make_tower(id="TWR-001")
    end = make_tower(id="TWR-002", name="Torre 2")
    start.properties = {**start.properties, "position": [0.0, 0.0, 0.0]}
    end.properties = {**end.properties, "position": [300.0, 0.0, 0.0]}
    return start, end


def make_span(**overrides) -> ConductorSpan:
    defaults = dict(
        id="SPAN-001",
        source_dataset="spans.csv:row=2",
        from_tower_id="TWR-001",
        to_tower_id="TWR-002",
        conductor_type="ACSR 400mm2",
    )
    defaults.update(overrides)
    span = ConductorSpan(**defaults)
    span.approve("engineer@sdtl.local")
    return span


def test_span_generates_a_sagging_ribbon() -> None:
    start, end = _positioned_towers()
    towers_by_id = {start.id: start, end.id: end}
    span = make_span(sag_m=6.0)

    model = ConductorSpanGenerator().generate(span, towers_by_id)

    assert model.type == "ConductorSpan"
    assert model.metadata["horizontal_span_m"] == pytest.approx(300.0)
    assert model.metadata["sag_m"] == pytest.approx(6.0)
    assert model.metadata["sag_assumed"] is False
    assert model.metadata["visual_width_m"] == pytest.approx(5.0)
    assert model.metadata["visual_width_not_to_scale"] is True
    vertices = model.components[0].mesh.vertices
    midpoint_z_values = [v[2] for v in vertices if abs(v[0] - 150.0) < 20]
    # The middle of the span should sag below both attachment heights.
    attachment_z = start.height_m * 0.85
    assert min(midpoint_z_values) < attachment_z


def test_span_assumes_a_sag_ratio_when_not_given() -> None:
    start, end = _positioned_towers()
    towers_by_id = {start.id: start, end.id: end}
    span = make_span()

    model = ConductorSpanGenerator().generate(span, towers_by_id)

    assert model.metadata["sag_assumed"] is True
    assert model.metadata["sag_m"] == pytest.approx(300.0 / 20)


def test_visual_width_has_a_floor_on_short_spans() -> None:
    start = make_tower(id="TWR-001")
    end = make_tower(id="TWR-002", name="Torre 2")
    start.properties = {**start.properties, "position": [0.0, 0.0, 0.0]}
    end.properties = {**end.properties, "position": [10.0, 0.0, 0.0]}
    towers_by_id = {start.id: start, end.id: end}
    span = make_span(sag_m=0.2)

    model = ConductorSpanGenerator().generate(span, towers_by_id)

    assert model.metadata["visual_width_m"] == pytest.approx(0.5)


def test_visual_width_has_a_ceiling_on_long_spans() -> None:
    start = make_tower(id="TWR-001")
    end = make_tower(id="TWR-002", name="Torre 2")
    start.properties = {**start.properties, "position": [0.0, 0.0, 0.0]}
    end.properties = {**end.properties, "position": [2000.0, 0.0, 0.0]}
    towers_by_id = {start.id: start, end.id: end}
    span = make_span(sag_m=20.0)

    model = ConductorSpanGenerator().generate(span, towers_by_id)

    assert model.metadata["visual_width_m"] == pytest.approx(5.0)


def test_span_rejects_unknown_tower_reference() -> None:
    start, _ = _positioned_towers()
    span = make_span(to_tower_id="TWR-999")

    with pytest.raises(ValueError, match="unknown tower"):
        ConductorSpanGenerator().generate(span, {start.id: start})


def test_span_rejects_tower_missing_projected_position() -> None:
    start = make_tower(id="TWR-001")
    end = make_tower(id="TWR-002", name="Torre 2")
    span = make_span()

    with pytest.raises(ValueError, match="projected local position"):
        ConductorSpanGenerator().generate(span, {start.id: start, end.id: end})
