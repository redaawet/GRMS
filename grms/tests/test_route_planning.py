"""Tests for capturing road endpoints and retrieving Google Maps routes."""

from __future__ import annotations

from unittest import mock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from grms.services import google_maps
from grms.tests.test_prioritization import RoadNetworkMixin


class RoutePlanningTests(RoadNetworkMixin, APITestCase):
    """Integration-style tests for the road route endpoint."""

    def test_missing_coordinates_return_validation_error(self):
        road, _, _ = self.create_network("Missing")
        url = reverse("road_route", args=[road.id])
        response = self.client.post(url, {"start": {"lat": 1.0}}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end", response.json())

    @mock.patch("grms.services.google_maps.get_directions")
    def test_route_endpoint_updates_coordinates_and_returns_summary(self, mock_get):
        mock_get.return_value = {
            "distance_meters": 5000,
            "distance_text": "5 km",
            "duration_seconds": 600,
            "duration_text": "10 mins",
            "start_address": "Start",
            "end_address": "End",
            "overview_polyline": "encoded",
            "warnings": [],
        }
        road, _, _ = self.create_network("Route")
        url = reverse("road_route", args=[road.id])
        payload = {
            "start": {"lat": 13.5, "lng": 39.5},
            "end": {"lat": 13.6, "lng": 39.6},
            "travel_mode": "driving",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get.assert_called_once()
        road.refresh_from_db()
        start_geom = road.road_start_coordinates
        if isinstance(start_geom, dict):
            coords = start_geom["coordinates"]
        else:  # pragma: no cover - exercised when GEOS is installed
            coords = [start_geom.x, start_geom.y]
        self.assertEqual(coords, [39.5, 13.5])
        self.assertEqual(response.json()["route"]["distance_meters"], 5000)

    @mock.patch("grms.services.google_maps.get_directions", side_effect=google_maps.GoogleMapsError("NO_ROUTE"))
    def test_route_endpoint_returns_error_when_google_fails(self, mock_get):
        road, _, _ = self.create_network("Error")
        url = reverse("road_route", args=[road.id])
        payload = {
            "start": {"lat": 13.5, "lng": 39.5},
            "end": {"lat": 13.6, "lng": 39.6},
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("NO_ROUTE", response.json()["detail"])
        mock_get.assert_called_once()

    @mock.patch("grms.services.google_maps.get_directions")
    def test_get_route_uses_saved_coordinates(self, mock_get):
        mock_get.return_value = {"distance_meters": 1000}
        road, _, _ = self.create_network("Saved")
        road.road_start_coordinates = {"type": "Point", "coordinates": [39.0, 13.0], "srid": 4326}
        road.road_end_coordinates = {"type": "Point", "coordinates": [39.5, 13.5], "srid": 4326}
        road.save(update_fields=["road_start_coordinates", "road_end_coordinates"])

        url = reverse("road_route", args=[road.id])
        response = self.client.get(url + "?travel_mode=walking")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get.assert_called_once_with(start_lat=13.0, start_lng=39.0, end_lat=13.5, end_lng=39.5, travel_mode="WALKING")
        payload = response.json()
        self.assertEqual(payload["start"], {"lat": 13.0, "lng": 39.0})
        self.assertEqual(payload["end"], {"lat": 13.5, "lng": 39.5})

    def test_get_route_returns_error_when_coordinates_missing(self):
        road, _, _ = self.create_network("MissingSaved")
        url = reverse("road_route", args=[road.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.json())
