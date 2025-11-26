"""Tests for capturing road endpoints and retrieving Leaflet/OSM routes."""

from __future__ import annotations

from unittest import mock

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from grms import models
from grms.services import map_services
from grms.tests.test_prioritization import RoadNetworkMixin


class RoutePlanningTests(RoadNetworkMixin, APITestCase):
    """Integration-style tests for the road route endpoint."""

    def test_missing_coordinates_return_validation_error(self):
        road, _, _ = self.create_network("Missing")
        url = reverse("road_route", args=[road.id])
        response = self.client.post(url, {"start": {"lat": 1.0}}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end", response.json())

    @mock.patch("grms.services.map_services.get_directions")
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

    @mock.patch("grms.services.map_services.get_directions", side_effect=map_services.MapServiceError("NO_ROUTE"))
    def test_route_endpoint_returns_error_when_routing_service_fails(self, mock_get):
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

    @mock.patch("grms.services.map_services.get_directions")
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

    @mock.patch("grms.services.map_services.get_admin_area_viewport")
    def test_map_context_returns_zone_woreda_and_travel_modes(self, mock_geo):
        mock_geo.return_value = {
            "formatted_address": "Mekelle, Tigray, Ethiopia",
            "center": {"lat": 13.4967, "lng": 39.4753},
            "viewport": {"northeast": {"lat": 13.6, "lng": 39.6}, "southwest": {"lat": 13.4, "lng": 39.3}},
            "bounds": None,
        }
        road, _, _ = self.create_network("Context")
        road.road_start_coordinates = {"type": "Point", "coordinates": [39.1, 13.1], "srid": 4326}
        road.road_end_coordinates = {"type": "Point", "coordinates": [39.2, 13.2], "srid": 4326}
        road.save(update_fields=["road_start_coordinates", "road_end_coordinates"])

        url = reverse("road_map_context", args=[road.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["zone"], {"id": road.admin_zone_id, "name": road.admin_zone.name})
        self.assertEqual(payload["woreda"], {"id": road.admin_woreda_id, "name": road.admin_woreda.name})
        self.assertEqual(payload["road"]["start"], {"lat": 13.1, "lng": 39.1})
        self.assertEqual(payload["road_length_km"], float(road.total_length_km))
        self.assertEqual(payload["travel_modes"], sorted(map_services.TRAVEL_MODES))
        self.assertEqual(payload["map_region"]["formatted_address"], "Mekelle, Tigray, Ethiopia")
        mock_geo.assert_called_once_with(zone_name=road.admin_zone.name, woreda_name=road.admin_woreda.name)

    @mock.patch("grms.services.map_services.get_admin_area_viewport", side_effect=map_services.MapServiceError("geocode"))
    def test_map_context_falls_back_to_default_region_on_error(self, mock_geo):
        road, _, _ = self.create_network("ContextError")
        url = reverse("road_map_context", args=[road.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["map_region"]["center"], map_services.DEFAULT_MAP_REGION["center"])
        mock_geo.assert_called_once()

    @mock.patch("grms.services.map_services.get_admin_area_viewport")
    def test_map_context_allows_zone_and_woreda_overrides(self, mock_geo):
        mock_geo.return_value = {"viewport": None, "bounds": None, "center": {"lat": 10.0, "lng": 40.0}}
        road, _, _ = self.create_network("Override")
        zone = models.AdminZone.objects.create(name="Another Zone")
        woreda = models.AdminWoreda.objects.create(name="Another Woreda", zone=zone)
        url = reverse("road_map_context", args=[road.id])
        response = self.client.get(url + f"?zone_id={zone.id}&woreda_id={woreda.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["zone"], {"id": zone.id, "name": zone.name})
        self.assertEqual(payload["woreda"], {"id": woreda.id, "name": woreda.name})
        mock_geo.assert_called_once_with(zone_name=zone.name, woreda_name=woreda.name)

    @mock.patch("grms.services.map_services.get_admin_area_viewport")
    def test_map_context_validates_mismatched_overrides(self, mock_geo):
        mock_geo.return_value = {"center": {"lat": 0, "lng": 0}, "viewport": None, "bounds": None}
        road, _, _ = self.create_network("InvalidOverride")
        zone = models.AdminZone.objects.create(name="Third Zone")
        wrong_zone = models.AdminZone.objects.create(name="Wrong Zone")
        woreda = models.AdminWoreda.objects.create(name="Third Woreda", zone=zone)
        url = reverse("road_map_context", args=[road.id])
        response = self.client.get(url + f"?zone_id={wrong_zone.id}&woreda_id={woreda.id}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.json())
        mock_geo.assert_not_called()

    def test_default_map_context_returns_zone_37n_region(self):
        url = reverse("road_map_context_default")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["map_region"]["center"], map_services.DEFAULT_MAP_REGION["center"])
        self.assertIn("bounds", payload["map_region"])

    @mock.patch("grms.services.map_services.get_admin_area_viewport_or_default")
    def test_default_map_context_uses_admin_selection_when_provided(self, mock_viewport):
        mock_viewport.return_value = {"center": {"lat": 13.5, "lng": 39.5}}
        zone = models.AdminZone.objects.create(name="Zone 37N")
        woreda = models.AdminWoreda.objects.create(name="Woreda 37N", zone=zone)

        url = reverse("road_map_context_default")
        response = self.client.get(url + f"?zone_id={zone.id}&woreda_id={woreda.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["zone"], {"id": zone.id, "name": zone.name})
        self.assertEqual(payload["woreda"], {"id": woreda.id, "name": woreda.name})
        mock_viewport.assert_called_once_with(zone.name, woreda.name)


class RoadGeometryTests(RoadNetworkMixin, APITestCase):
    def setUp(self):
        super().setUp()
        user_model = get_user_model()
        user = user_model.objects.create_user("admin", password="pass1234", is_staff=True)
        self.client.force_authenticate(user=user)

    def test_post_geometry_saves_linestring_and_length(self):
        road, _, _ = self.create_network("GeomSave")
        road.total_length_km = Decimal("0")
        road.save(update_fields=["total_length_km"])

        url = reverse("road_geometry", args=[road.id])
        payload = {
            "type": "LineString",
            "coordinates": [[39.0, 13.0], [39.01, 13.0]],
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        road.refresh_from_db()
        self.assertIsNotNone(road.geometry)
        self.assertGreater(float(road.total_length_km), 0)

    def test_road_section_creation_allowed_after_geometry_saved(self):
        road, _, _ = self.create_network("SectionGeom")
        road.total_length_km = Decimal("5")
        road.save(update_fields=["total_length_km"])

        url = reverse("road_geometry", args=[road.id])
        payload = {"coordinates": [[39.0, 13.0], [39.005, 13.0], [39.01, 13.0]]}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        section = models.RoadSection.objects.create(
            road=road,
            section_number=2,
            sequence_on_road=2,
            start_chainage_km=Decimal("0"),
            end_chainage_km=Decimal("1"),
            length_km=Decimal("1"),
            surface_type="Earth",
        )

        self.assertIsNotNone(section.pk)

