from __future__ import annotations

import pytest

from backend.transmission_line import GeoPoint, LocalEnuProjection


def test_origin_projects_to_zero() -> None:
    origin = GeoPoint(latitude=-3.5, longitude=-80.4, elevation_m=10.0)
    projection = LocalEnuProjection(origin)

    assert projection.to_local(origin) == pytest.approx((0.0, 0.0, 0.0))


def test_one_degree_latitude_is_about_111km_north() -> None:
    origin = GeoPoint(latitude=0.0, longitude=0.0)
    projection = LocalEnuProjection(origin)

    east, north, up = projection.to_local(GeoPoint(latitude=1.0, longitude=0.0))

    assert east == pytest.approx(0.0, abs=1e-6)
    assert north == pytest.approx(111_320.0, rel=1e-3)
    assert up == pytest.approx(0.0)


def test_longitude_scale_shrinks_away_from_the_equator() -> None:
    origin = GeoPoint(latitude=60.0, longitude=0.0)
    projection = LocalEnuProjection(origin)

    east, _, _ = projection.to_local(GeoPoint(latitude=60.0, longitude=1.0))

    # cos(60deg) == 0.5, so one degree of longitude covers about half the
    # ground distance it would at the equator.
    assert east == pytest.approx(111_320.0 * 0.5, rel=1e-3)


def test_elevation_maps_directly_to_up() -> None:
    origin = GeoPoint(latitude=-3.5, longitude=-80.4, elevation_m=10.0)
    projection = LocalEnuProjection(origin)

    _, _, up = projection.to_local(GeoPoint(latitude=-3.5, longitude=-80.4, elevation_m=42.5))

    assert up == pytest.approx(32.5)
