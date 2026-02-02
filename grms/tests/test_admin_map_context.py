from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from grms import models
from grms.utils import make_point

try:  # pragma: no cover - optional GIS import
    from django.contrib.gis.geos import LineString
except Exception:  # pragma: no cover - fallback when GEOS is unavailable
    LineString = None


def _make_linestring():
    if LineString is not None:
        return LineString((39.0, 13.5), (39.1, 13.6))
    return {
        "type": "LineString",
        "coordinates": [[39.0, 13.5], [39.1, 13.6]],
        "srid": 4326,
    }


class AdminMapContextTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username="admin",
            password="password",
            email="admin@example.com",
        )
        self.client.force_login(self.user)

        self.zone = models.AdminZone.objects.create(name="Zone")
        self.road = models.Road.objects.create(
            road_identifier="RTR-1",
            road_name_from="Alpha",
            road_name_to="Bravo",
            design_standard="DC1",
            admin_zone=self.zone,
            total_length_km=1,
            surface_type="Gravel",
            managing_authority="Regional",
            geometry=_make_linestring(),
        )
        self.section = models.RoadSection.objects.create(
            road=self.road,
            start_chainage_km=0,
            end_chainage_km=1,
            length_km=1,
            surface_type="Earth",
        )
        self.segment = models.RoadSegment.objects.create(
            section=self.section,
            station_from_km=0,
            station_to_km=1,
            cross_section="Flat",
            terrain_transverse="Flat",
            terrain_longitudinal="Flat",
        )
        self.structure = models.StructureInventory.objects.create(
            road=self.road,
            section=self.section,
            geometry_type=models.StructureInventory.POINT,
            station_km=0.5,
            location_point=make_point(13.55, 39.05),
            structure_category="Bridge",
        )
        models.BridgeDetail.objects.create(structure=self.structure, bridge_type="Concrete")

    def _assert_lon_lat(self, coordinate):
        self.assertLessEqual(abs(coordinate[0]), 180)
        self.assertLessEqual(abs(coordinate[1]), 90)

    def _assert_geometry(self, geometry):
        self.assertIsNotNone(geometry)
        self.assertIn("type", geometry)
        self.assertIn("coordinates", geometry)
        if geometry["type"] == "Point":
            self._assert_lon_lat(geometry["coordinates"])
        elif geometry["type"] == "LineString":
            self._assert_lon_lat(geometry["coordinates"][0])
        elif geometry["type"] == "MultiLineString":
            self._assert_lon_lat(geometry["coordinates"][0][0])

    def _assert_feature(self, feature):
        self.assertEqual(feature.get("type"), "Feature")
        self._assert_geometry(feature.get("geometry"))
        self.assertIn("properties", feature)
        self.assertIn("admin_url", feature["properties"])

    def test_section_map_context(self):
        url = reverse("admin:grms_roadsection_map_context", args=[self.section.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload.get("mode"), "section")
        self.assertIn("road", payload)
        self.assertIn("sections", payload)
        self.assertIn("current_section_id", payload)
        self.assertIn("structures", payload)
        self.assertEqual(payload["current_section_id"], self.section.id)

        if payload["road"]:
            self._assert_feature(payload["road"])
        for feature in payload["sections"]:
            self._assert_feature(feature)

        structure_feature = next(
            f for f in payload["structures"] if f["properties"]["id"] == self.structure.id
        )
        self._assert_feature(structure_feature)
        self.assertEqual(structure_feature["properties"]["kind"], "bridge")
        self.assertEqual(
            structure_feature["properties"]["admin_url"],
            reverse("admin:grms_bridgedetail_change", args=[self.structure.id]),
        )

    def test_segment_map_context(self):
        url = reverse("admin:grms_roadsegment_map_context", args=[self.segment.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload.get("mode"), "segment")
        self.assertIn("road", payload)
        self.assertIn("section", payload)
        self.assertIn("segments", payload)
        self.assertIn("current_segment_id", payload)
        self.assertIn("structures", payload)
        self.assertEqual(payload["current_segment_id"], self.segment.id)

        if payload["road"]:
            self._assert_feature(payload["road"])
        if payload["section"]:
            self._assert_feature(payload["section"])
        for feature in payload["segments"]:
            self._assert_feature(feature)

        structure_feature = next(
            f for f in payload["structures"] if f["properties"]["id"] == self.structure.id
        )
        self._assert_feature(structure_feature)

    def test_structure_map_context(self):
        url = reverse("admin:grms_structureinventory_map_context", args=[self.structure.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload.get("mode"), "structure")
        self.assertIn("road", payload)
        self.assertIn("section", payload)
        self.assertIn("segment", payload)
        self.assertIn("structures", payload)
        self.assertIn("current_structure_id", payload)
        self.assertEqual(payload["current_structure_id"], self.structure.id)

        if payload["road"]:
            self._assert_feature(payload["road"])
        if payload["section"]:
            self._assert_feature(payload["section"])
        if payload["segment"]:
            self._assert_feature(payload["segment"])

        structure_feature = next(
            f for f in payload["structures"] if f["properties"]["id"] == self.structure.id
        )
        self._assert_feature(structure_feature)
        self.assertIn("label", structure_feature["properties"])
        self.assertIn("station_km", structure_feature["properties"])

    def test_map_context_requires_login(self):
        self.client.logout()
        urls = [
            reverse("admin:grms_roadsection_map_context", args=[self.section.id]),
            reverse("admin:grms_roadsegment_map_context", args=[self.segment.id]),
            reverse("admin:grms_structureinventory_map_context", args=[self.structure.id]),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, {302, 403})
