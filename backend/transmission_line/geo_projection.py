from __future__ import annotations

from math import cos, radians

from .models import GeoPoint

_METERS_PER_DEGREE_LATITUDE = 111_320.0


class LocalEnuProjection:
    """Project WGS84 lat/long/elevation onto a local East-North-Up plane in meters.

    This is a flat-earth equirectangular approximation anchored at one
    origin point, not a rigorous geodesic projection (UTM, etc). It stays
    accurate to a few meters over the tens-of-kilometers a transmission
    line typically spans, which is adequate for 3D visualization and
    quantity takeoff, but this projection must not be used for legal
    survey, cadastral, or right-of-way boundary work.
    """

    def __init__(self, origin: GeoPoint) -> None:
        self.origin = origin
        self._meters_per_degree_longitude = _METERS_PER_DEGREE_LATITUDE * cos(
            radians(origin.latitude)
        )

    def to_local(self, point: GeoPoint) -> tuple[float, float, float]:
        """Return (east, north, up) meters relative to the projection origin."""

        east = (point.longitude - self.origin.longitude) * self._meters_per_degree_longitude
        north = (point.latitude - self.origin.latitude) * _METERS_PER_DEGREE_LATITUDE
        up = point.elevation_m - self.origin.elevation_m
        return (east, north, up)
