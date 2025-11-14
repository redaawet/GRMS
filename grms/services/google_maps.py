"""Lightweight wrapper around the Google Maps Directions API."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, List, Optional
from urllib import error, parse, request

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
TRAVEL_MODES = {"DRIVING", "WALKING", "BICYCLING", "TRANSIT"}


class GoogleMapsError(RuntimeError):
    """Raised when the Google Maps API returns an error response."""


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
        }


def get_api_key() -> str:
    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
    if not api_key:
        raise ImproperlyConfigured("GOOGLE_MAPS_API_KEY environment variable is not configured.")
    return api_key


def get_directions(
    *, start_lat: float, start_lng: float, end_lat: float, end_lng: float, travel_mode: str = "DRIVING"
) -> Dict[str, Any]:
    """Query Google Maps for the preferred route between two coordinates."""

    if travel_mode.upper() not in TRAVEL_MODES:
        raise GoogleMapsError(f"Unsupported travel mode '{travel_mode}'.")

    api_key = get_api_key()
    query = parse.urlencode(
        {
            "origin": f"{start_lat},{start_lng}",
            "destination": f"{end_lat},{end_lng}",
            "mode": travel_mode.lower(),
            "key": api_key,
        }
    )
    url = f"{DIRECTIONS_URL}?{query}"

    try:
        with request.urlopen(url, timeout=10) as response:  # pragma: no cover - requires network
            payload = json.loads(response.read())
    except error.URLError as exc:  # pragma: no cover - network errors
        raise GoogleMapsError(str(exc)) from exc

    status = payload.get("status")
    if status != "OK":
        message = payload.get("error_message") or status or "Unknown Google Maps error"
        raise GoogleMapsError(message)

    route = payload["routes"][0]
    leg = route["legs"][0]
    summary = RouteSummary(
        distance_meters=int(leg["distance"]["value"]),
        distance_text=leg["distance"]["text"],
        duration_seconds=int(leg["duration"]["value"]),
        duration_text=leg["duration"]["text"],
        start_address=leg.get("start_address", ""),
        end_address=leg.get("end_address", ""),
        overview_polyline=route.get("overview_polyline", {}).get("points", ""),
        warnings=route.get("warnings", []),
    )
    return summary.as_dict()


def get_admin_area_viewport(zone_name: str, woreda_name: Optional[str] = None) -> Dict[str, Any]:
    """Return a Google Maps viewport for the supplied zone/woreda."""

    if not zone_name:
        raise GoogleMapsError("Zone name is required to determine the map viewport.")

    api_key = get_api_key()
    address_parts = [part for part in [woreda_name, zone_name, "Tigray", "Ethiopia"] if part]
    query = parse.urlencode({"address": ", ".join(address_parts), "key": api_key, "region": "et"})
    url = f"{GEOCODE_URL}?{query}"

    try:
        with request.urlopen(url, timeout=10) as response:  # pragma: no cover - requires network
            payload = json.loads(response.read())
    except error.URLError as exc:  # pragma: no cover - network errors
        raise GoogleMapsError(str(exc)) from exc

    status = payload.get("status")
    if status != "OK":
        message = payload.get("error_message") or status or "Unknown Google Maps error"
        raise GoogleMapsError(message)

    result = payload["results"][0]
    geometry = result.get("geometry") or {}
    location = geometry.get("location") or {}
    if not location:
        raise GoogleMapsError("Unable to determine the map location for the specified admin area.")

    return {
        "formatted_address": result.get("formatted_address", ""),
        "center": {"lat": float(location.get("lat", 0.0)), "lng": float(location.get("lng", 0.0))},
        "bounds": geometry.get("bounds"),
        "viewport": geometry.get("viewport"),
    }
