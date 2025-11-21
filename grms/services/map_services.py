"""Utilities for working with Leaflet/OpenStreetMap-powered maps."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, List, Optional
from urllib import error, parse, request

OSRM_URL = "https://router.project-osrm.org/route/v1"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "GRMS/1.0 (https://github.com/WorldBank-Transport/GRMS)"

TRAVEL_MODES = {"DRIVING", "WALKING", "BICYCLING"}
OSRM_PROFILES = {"DRIVING": "driving", "WALKING": "walking", "BICYCLING": "cycling"}

# Default to the centre of UTM Zone 37N so every map widget opens on a
# predictable, nationally relevant viewport even when we cannot look up a more
# specific admin area. The bounds roughly span the Ethiopian extent of Zone
# 37N; we use them both for fitting and to validate admin lookups so the map
# never recentres far outside the intended coordinate system.
DEFAULT_MAP_REGION = {
    "formatted_address": "UTM Zone 37N (Ethiopia)",
    "center": {"lat": 9.0, "lng": 39.0},
    # The bounds span the main north–south extent of Ethiopia that sits inside
    # Zone 37N; they also provide a viewport for initial map fitting.
    "bounds": {
        "northeast": {"lat": 15.0, "lng": 42.0},
        "southwest": {"lat": 3.0, "lng": 36.0},
    },
    "viewport": {
        "northeast": {"lat": 15.0, "lng": 42.0},
        "southwest": {"lat": 3.0, "lng": 36.0},
    },
}


class MapServiceError(RuntimeError):
    """Raised when the backing map services return an error response."""


@dataclass
class RouteSummary:
    distance_meters: int
    distance_text: str
    duration_seconds: int
    duration_text: str
    start_address: str
    end_address: str
    overview_polyline: str
    warnings: List[str]
    geometry: List[List[float]]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "distance_meters": self.distance_meters,
            "distance_text": self.distance_text,
            "duration_seconds": self.duration_seconds,
            "duration_text": self.duration_text,
            "start_address": self.start_address,
            "end_address": self.end_address,
            "overview_polyline": self.overview_polyline,
            "warnings": self.warnings,
            "geometry": self.geometry,
        }


def _format_distance(meters: float) -> str:
    if meters >= 1000:
        return f"{meters / 1000:.1f} km"
    return f"{int(meters)} m"


def _format_duration(seconds: float) -> str:
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _request_json(url: str) -> Any:
    req = request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with request.urlopen(req, timeout=10) as response:  # pragma: no cover - requires network
            data = response.read().decode("utf-8")
            return json.loads(data)
    except error.URLError as exc:  # pragma: no cover - network errors
        raise MapServiceError(str(exc)) from exc


def get_default_map_region() -> Dict[str, Any]:
    """Return a copy of the default UTM Zone 37N map region configuration."""

    # Copy via JSON round-trip to avoid accidental mutation of the module
    # constant in request handlers.
    return json.loads(json.dumps(DEFAULT_MAP_REGION))


def _region_center(region: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    center = region.get("center") or {}
    return center.get("lat"), center.get("lng")


def _is_within_zone_37n(lat: Optional[float], lng: Optional[float]) -> bool:
    return lat is not None and lng is not None and 3.0 <= lat <= 15.0 and 36.0 <= lng <= 42.0


def get_admin_area_viewport_or_default(
    zone_name: Optional[str] = None, woreda_name: Optional[str] = None
) -> Dict[str, Any]:
    """Resolve an admin viewport but clamp it to the UTM Zone 37N extent.

    When the lookup fails or resolves outside Zone 37N, the default map region
    centred on Zone 37N is returned so that map widgets consistently initialise
    within the desired coordinate system.
    """

    if not zone_name and not woreda_name:
        return get_default_map_region()

    try:
        region = get_admin_area_viewport(zone_name=zone_name, woreda_name=woreda_name)
    except MapServiceError:
        return get_default_map_region()

    lat, lng = _region_center(region)
    if not _is_within_zone_37n(lat, lng):
        return get_default_map_region()

    # Normalise viewport so callers can rely on it.
    if not region.get("viewport") and region.get("bounds"):
        region["viewport"] = region["bounds"]

    return region


def get_directions(
    *, start_lat: float, start_lng: float, end_lat: float, end_lng: float, travel_mode: str = "DRIVING"
) -> Dict[str, Any]:
    """Query OSRM for the preferred route between two coordinates."""

    mode = (travel_mode or "DRIVING").upper()
    if mode not in TRAVEL_MODES:
        raise MapServiceError(f"Unsupported travel mode '{travel_mode}'.")

    profile = OSRM_PROFILES[mode]
    coordinates = f"{start_lng},{start_lat};{end_lng},{end_lat}"
    query = parse.urlencode({"overview": "full", "geometries": "geojson"})
    url = f"{OSRM_URL}/{profile}/{coordinates}?{query}"
    payload = _request_json(url)

    if payload.get("code") != "Ok" or not payload.get("routes"):
        message = payload.get("message") or payload.get("code") or "Unable to calculate a route."
        raise MapServiceError(message)

    route = payload["routes"][0]
    distance = float(route.get("distance", 0.0))
    duration = float(route.get("duration", 0.0))
    geometry = route.get("geometry", {}).get("coordinates", [])
    summary = RouteSummary(
        distance_meters=int(distance),
        distance_text=_format_distance(distance),
        duration_seconds=int(duration),
        duration_text=_format_duration(duration),
        start_address="",
        end_address="",
        overview_polyline="",
        warnings=[],
        geometry=geometry,
    )
    return summary.as_dict()


def get_admin_area_viewport(zone_name: str, woreda_name: Optional[str] = None) -> Dict[str, Any]:
    """Return a viewport for the supplied zone/woreda using OpenStreetMap data."""

    if not zone_name and not woreda_name:
        raise MapServiceError("An administrative zone or woreda is required to determine the map viewport.")

    address_parts = [part for part in [woreda_name, zone_name, "Tigray", "Ethiopia"] if part]
    query = parse.urlencode({"q": ", ".join(address_parts), "format": "json", "limit": 1})
    url = f"{NOMINATIM_URL}?{query}"
    payload = _request_json(url)

    if not payload:
        raise MapServiceError("Unable to determine the map location for the specified admin area.")

    result = payload[0]
    lat = float(result.get("lat"))
    lon = float(result.get("lon"))
    bounding_box = result.get("boundingbox") or []

    bounds = None
    if len(bounding_box) == 4:
        south, north, west, east = [float(value) for value in bounding_box]
        bounds = {
            "northeast": {"lat": north, "lng": east},
            "southwest": {"lat": south, "lng": west},
        }

    return {
        "formatted_address": result.get("display_name", ""),
        "center": {"lat": lat, "lng": lon},
        "bounds": bounds,
        "viewport": bounds,
    }

