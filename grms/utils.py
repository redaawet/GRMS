"""Utility helpers for shared functionality across modules."""

from __future__ import annotations

import json
from typing import Dict, Optional
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


def fetch_osrm_route(start_point, end_point):
    """Fetch the OSRM route geometry between two points.

    Args:
        start_point: Point geometry returned from :func:`make_point`.
        end_point: Point geometry returned from :func:`make_point`.

    Returns:
        A GEOS :class:`~django.contrib.gis.geos.LineString` or GeoJSON-like dict
        representing the route, depending on :data:`settings.USE_POSTGIS`.

    Raises:
        ValueError: If the OSRM API returns an error or lacks geometry data.
        URLError, HTTPError: If the OSRM API cannot be reached.
    """

    if not start_point or not end_point:
        raise ValueError("Start and end points are required to fetch OSRM route")

    start_coords = point_to_lat_lng(start_point)
    end_coords = point_to_lat_lng(end_point)

    if not start_coords or not end_coords:
        raise ValueError("Start and end points must be valid geometry objects")

    start_lon, start_lat = float(start_coords["lng"]), float(start_coords["lat"])
    end_lon, end_lat = float(end_coords["lng"]), float(end_coords["lat"])

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

    mapped_coordinates = [(float(lon), float(lat)) for lon, lat in coordinates]

    if getattr(settings, "USE_POSTGIS", False):
        from django.contrib.gis.geos import LineString  # pragma: no cover - requires GEOS

        return LineString(mapped_coordinates, srid=4326)

    return {"type": "LineString", "coordinates": mapped_coordinates, "srid": 4326}
