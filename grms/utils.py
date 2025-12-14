"""Utility helpers for shared functionality across modules."""

from __future__ import annotations

import json
import math
from math import sqrt
from typing import Dict, Iterable, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

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

try:
    from django.contrib.gis.geos import GEOSGeometry, LineString

    GEOS_AVAILABLE = True
except Exception:  # pragma: no cover - runtime fallback when GIS libs are missing
    GEOS_AVAILABLE = False

    class _MissingGEOS:
        def __init__(self, *args, **kwargs):
            raise ImportError("GEOS library is required for geometry operations.")

    def GEOSGeometry(*args, **kwargs):  # type: ignore[override]
        raise ImportError("GEOS library is required for geometry operations.")

    class LineString(_MissingGEOS):  # type: ignore[override]
        pass

# Mean Earth radius according to IUGG (km)
EARTH_RADIUS_KM = 6371.0088


def _haversine_km(start: Sequence[float], end: Sequence[float]) -> float:
    """Return the haversine distance between two ``(lng, lat)`` points in km."""

    lon1, lat1 = float(start[0]), float(start[1])
    lon2, lat2 = float(end[0]), float(end[1])

    lon1_rad, lat1_rad, lon2_rad, lat2_rad = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_KM * c


def _extract_coordinates(geometry) -> list[Tuple[float, float]]:
    """Return a list of ``(lng, lat)`` pairs from a GEOS or GeoJSON geometry."""

    if geometry is None:
        return []

    if hasattr(geometry, "coords"):
        return [(float(x), float(y)) for x, y in geometry.coords]

    if isinstance(geometry, dict):
        coords = geometry.get("coordinates") or []
        if coords and isinstance(coords[0][0], (list, tuple)):
            # GeoJSON LineString structure
            return [(float(x), float(y)) for x, y in coords]
    return []


def geometry_length_km(geometry) -> float:
    """Calculate the total length of a linestring geometry in kilometres."""

    coordinates = _extract_coordinates(geometry)
    if len(coordinates) < 2:
        return 0.0

    total = 0.0
    for start, end in zip(coordinates[:-1], coordinates[1:]):
        total += _haversine_km(start, end)
    return total


def geos_length_km(geometry: GEOSGeometry | None) -> float:
    """Return metric length for a GEOS geometry by transforming to EPSG:3857."""

    if geometry is None:
        return 0.0

    if isinstance(geometry, (list, tuple, dict)):
        return geometry_length_km(geometry)

    empty_flag = getattr(geometry, "empty", None)
    if empty_flag is True:
        return 0.0

    try:
        geom_3857 = geometry.transform(3857, clone=True)
        return float(geom_3857.length) / 1000
    except Exception:
        # When a fallback JSON geometry or stub is provided, fail gracefully
        return 0.0


def _interpolate_coordinate(start: Tuple[float, float], end: Tuple[float, float], fraction: float) -> Tuple[float, float]:
    return (
        float(start[0]) + (float(end[0]) - float(start[0])) * fraction,
        float(start[1]) + (float(end[1]) - float(start[1])) * fraction,
    )


def _build_linestring(coordinates: Iterable[Tuple[float, float]], *, srid: int | None, as_geos: bool):
    coords_list = list(coordinates)
    if as_geos:
        from django.contrib.gis.geos import LineString  # pragma: no cover - requires GEOS

        line = LineString(coords_list)
        if srid:
            line.srid = srid
        return line
    return {"type": "LineString", "coordinates": coords_list, "srid": srid or 4326}


def slice_geometry_by_chainage(geometry, start_chainage_km: float, end_chainage_km: float):
    """Return a portion of a linestring between the given chainages.

    The function works with both GEOS :class:`~django.contrib.gis.geos.LineString`
    instances and GeoJSON-like dictionaries.
    """

    if start_chainage_km < 0 or end_chainage_km <= start_chainage_km:
        return None

    coords = _extract_coordinates(geometry)
    if len(coords) < 2:
        return None

    total_length = geometry_length_km(geometry)
    if total_length == 0:
        return None

    start_km = min(start_chainage_km, total_length)
    end_km = min(end_chainage_km, total_length)
    if start_km >= total_length:
        return None

    sliced_coords: list[Tuple[float, float]] = []
    cumulative = 0.0
    srid = getattr(geometry, "srid", None)
    as_geos = getattr(settings, "USE_POSTGIS", False) and hasattr(geometry, "coords")

    for start, end in zip(coords[:-1], coords[1:]):
        segment_length = _haversine_km(start, end)
        next_cumulative = cumulative + segment_length

        if start_km >= cumulative and start_km <= next_cumulative:
            fraction = (start_km - cumulative) / segment_length if segment_length else 0.0
            sliced_start = _interpolate_coordinate(start, end, fraction)
            sliced_coords.append(sliced_start)

        if end_km >= cumulative and end_km <= next_cumulative:
            fraction = (end_km - cumulative) / segment_length if segment_length else 0.0
            sliced_end = _interpolate_coordinate(start, end, fraction)
            if not sliced_coords:
                sliced_coords.append(_interpolate_coordinate(start, end, 0))
            sliced_coords.append(sliced_end)
            break

        if sliced_coords and end_km > next_cumulative:
            sliced_coords.append(end)

        cumulative = next_cumulative

    if len(sliced_coords) < 2:
        return None

    return _build_linestring(sliced_coords, srid=srid, as_geos=as_geos)


def line_distance(p1, p2):
    return sqrt(
        (p1[0] - p2[0]) ** 2 +
        (p1[1] - p2[1]) ** 2
    )


def slice_linestring_by_chainage(polyline, start_chainage_km, end_chainage_km):
    """Slice a LineString using chainages measured along the polyline itself."""

    if not polyline:
        return None

    try:
        geos_line = polyline if hasattr(polyline, "interpolate") else GEOSGeometry(polyline)
    except Exception:
        return None

    if geos_line.empty:
        return None

    line_4326 = geos_line if getattr(geos_line, "srid", 4326) == 4326 else geos_line.transform(4326, clone=True)
    metric_line = line_4326.transform(3857, clone=True)
    coords = list(metric_line.coords)

    if len(coords) < 2:
        return None

    cumulative = [0.0]
    for start, end in zip(coords[:-1], coords[1:]):
        cumulative.append(cumulative[-1] + line_distance(start, end))

    total_m = cumulative[-1]
    if total_m == 0:
        return None

    start_m = max(0.0, min(total_m, float(start_chainage_km) * 1000))
    end_m = max(start_m, min(total_m, float(end_chainage_km) * 1000))

    start_point_metric = metric_line.interpolate(start_m)
    end_point_metric = metric_line.interpolate(end_m)

    sliced_coords = [
        (float(start_point_metric.x), float(start_point_metric.y)),
    ]
    for idx in range(1, len(coords) - 1):
        if cumulative[idx] > start_m and cumulative[idx] < end_m:
            sliced_coords.append(coords[idx])
    sliced_coords.append((float(end_point_metric.x), float(end_point_metric.y)))

    sliced_metric = LineString(sliced_coords, srid=3857)
    sliced_4326 = sliced_metric.transform(4326, clone=True)

    start_point_wgs = start_point_metric.transform(4326, clone=True)
    end_point_wgs = end_point_metric.transform(4326, clone=True)

    return {
        "geometry": sliced_4326,
        "start_point": (float(start_point_wgs.y), float(start_point_wgs.x)),
        "end_point": (float(end_point_wgs.y), float(end_point_wgs.x)),
        "length_km": float(sliced_metric.length) / 1000,
    }


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


def fetch_osrm_route(start_lng: float, start_lat: float, end_lng: float, end_lat: float) -> list[list[float]]:
    """Fetch the decoded OSRM route geometry between two coordinates."""

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson"
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

    return [[float(lon), float(lat)] for lon, lat in coordinates]


def osrm_linestring_to_geos(coords: Sequence[Sequence[float]]) -> GEOSGeometry:
    """Convert decoded OSRM coordinates to a GEOS LineString with SRID 4326."""

    cleaned = [(float(lon), float(lat)) for lon, lat in coords]
    if len(cleaned) < 2:
        raise ValueError("At least two coordinates are required to build a LineString")

    geom = LineString(cleaned)
    geom.srid = 4326
    return geom
