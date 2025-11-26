"""Utility helpers for shared functionality across modules."""

from __future__ import annotations

import json
import math
from typing import Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from django.contrib.gis.geos import LineString
from django.contrib.gis.geos import Point

try:  # pragma: no cover - optional dependency for conversion
    from pyproj import Transformer
except ImportError:  # pragma: no cover - handled at runtime for clarity
    Transformer = None


def utm_to_wgs84(easting: float, northing: float, zone: int = 37) -> tuple[float, float]:
    """Convert UTM coordinates to WGS84 latitude/longitude.

    The default UTM zone corresponds to the Tigray region (37N).
    """

    if Transformer is None:
        raise ImportError("pyproj is required for UTM to WGS84 conversion. Install pyproj to continue.")

    transformer = Transformer.from_crs(f"EPSG:326{zone}", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(easting, northing)
    return lat, lon


def wgs84_to_utm(lat: float, lon: float, zone: int = 37) -> tuple[float, float]:
    """Convert WGS84 latitude/longitude to UTM coordinates.

    The default UTM zone corresponds to the Tigray region (37N).
    """

    if Transformer is None:
        raise ImportError("pyproj is required for WGS84 to UTM conversion. Install pyproj to continue.")

    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:326{zone}", always_xy=True)
    easting, northing = transformer.transform(lon, lat)
    return easting, northing

from django.conf import settings


def make_point(lat: float, lng: float):
    """Return a geometry instance that works with and without PostGIS."""

    if getattr(settings, "USE_POSTGIS", False):
        from django.contrib.gis.geos import Point  # pragma: no cover - requires GEOS

        return Point(lng, lat, srid=4326)
    return {"type": "Point", "coordinates": [float(lng), float(lat)], "srid": 4326}


def point_to_lat_lng(point) -> Optional[Dict[str, float]]:
    """Convert a stored geometry point to a simple latitude/longitude pair."""

    if not point:
        return None
    try:
        lng = float(point.x)
        lat = float(point.y)
    except AttributeError:
        coords = None
        if isinstance(point, dict):
            coords = point.get("coordinates")
        if not coords or len(coords) < 2:
            return None
        lng, lat = float(coords[0]), float(coords[1])
    return {"lat": lat, "lng": lng}


def fetch_osrm_route(start_point, end_point) -> LineString:
    """Fetch the OSRM route geometry between two GEOS points.

    Args:
        start_point: GEOS :class:`~django.contrib.gis.geos.Point` for the start coordinate.
        end_point: GEOS :class:`~django.contrib.gis.geos.Point` for the end coordinate.

    Returns:
        A GEOS :class:`~django.contrib.gis.geos.LineString` representing the route.

    Raises:
        ValueError: If the OSRM API returns an error or lacks geometry data.
        URLError, HTTPError: If the OSRM API cannot be reached.
    """

    if not start_point or not end_point:
        raise ValueError("Start and end points are required to fetch OSRM route")

    start_lon, start_lat = float(start_point.x), float(start_point.y)
    end_lon, end_lat = float(end_point.x), float(end_point.y)

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
    )

    try:
        with urlopen(url) as response:
            data = response.read()
    except (HTTPError, URLError):  # pragma: no cover - network failures
        raise

    payload = json.loads(data)
    if payload.get("code") != "Ok":
        raise ValueError(payload.get("message", "OSRM routing failed"))

    routes = payload.get("routes") or []
    if not routes:
        raise ValueError("OSRM response did not include any routes")

    coordinates = routes[0].get("geometry", {}).get("coordinates") or []
    if not coordinates:
        raise ValueError("OSRM route geometry is missing from the response")

    line_string = LineString([(float(lon), float(lat)) for lon, lat in coordinates], srid=4326)
    return line_string


def _haversine_km(p1: Point, p2: Point) -> float:
    """Return the great-circle distance between two WGS84 points in kilometers."""

    lon1, lat1, lon2, lat2 = map(math.radians, [p1.x, p1.y, p2.x, p2.y])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return 6371.0 * c


def geometry_length_km(geometry: LineString) -> float:
    """Compute the geodesic length of a LineString in kilometers."""

    if not geometry or len(geometry.coords) < 2:
        return 0.0

    coords = list(geometry.coords)
    total = 0.0
    for idx in range(len(coords) - 1):
        total += _haversine_km(Point(*coords[idx]), Point(*coords[idx + 1]))
    return total


def slice_geometry_by_chainage(
    geometry: LineString,
    start_chainage_km: float,
    end_chainage_km: float,
) -> Optional[LineString]:
    """Return the portion of a road geometry that covers the given chainage range.

    Uses geodesic (haversine) distances to keep section start/end aligned with the
    parent road geometry even when recorded road lengths differ from true path
    length. Chainages are clamped to the actual geometry length.
    """

    if not geometry or start_chainage_km is None or end_chainage_km is None:
        return None

    coords = list(geometry.coords)
    if len(coords) < 2:
        return None

    segment_lengths = []
    total_length = 0.0
    for idx in range(len(coords) - 1):
        seg_len = _haversine_km(Point(*coords[idx]), Point(*coords[idx + 1]))
        segment_lengths.append(seg_len)
        total_length += seg_len

    if total_length == 0:
        return None

    target_start = max(0.0, min(total_length, float(start_chainage_km)))
    target_end = max(0.0, min(total_length, float(end_chainage_km)))

    if target_end <= target_start:
        return None

    def _interpolate_point(p1: Point, p2: Point, distance_along: float, segment_length: float) -> Point:
        ratio = 0 if segment_length == 0 else distance_along / segment_length
        ratio = max(0.0, min(1.0, ratio))
        x = p1.x + (p2.x - p1.x) * ratio
        y = p1.y + (p2.y - p1.y) * ratio
        return Point(x, y)

    collected = []
    walked = 0.0
    for idx in range(len(coords) - 1):
        seg_len = segment_lengths[idx]
        next_walked = walked + seg_len

        if next_walked < target_start:
            walked = next_walked
            continue

        p1 = Point(*coords[idx])
        p2 = Point(*coords[idx + 1])

        if walked <= target_start <= next_walked:
            start_point = _interpolate_point(p1, p2, target_start - walked, seg_len)
            collected.append(start_point)
        elif walked >= target_start:
            collected.append(p1)

        if walked <= target_end <= next_walked:
            end_point = _interpolate_point(p1, p2, target_end - walked, seg_len)
            collected.append(end_point)
            break

        if walked < target_end:
            collected.append(p2)

        walked = next_walked

    if len(collected) < 2:
        return None

    return LineString(collected, srid=getattr(geometry, "srid", None))
