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
    if LineString is None:
        return None
    return LineString((39.0, 13.5), (39.2, 13.7))


class MapGeoJSONTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username="admin",
            password="password",
            email="admin@example.com",
        )
        self.client.force_login(self.user)

        self.zone = models.AdminZone.objects.create(name="Zone")
        geom = _make_linestring()
        if geom is None:
            self.skipTest("GEOS is required for map geojson tests.")

        self.road = models.Road.objects.create(
            road_identifier="RTR-1",
            road_name_from="Alpha",
            road_name_to="Bravo",
            design_standard="DC1",
            admin_zone=self.zone,
            total_length_km=2,
            surface_type="Gravel",
            managing_authority="Regional",
            geometry=geom,
        )
        self.section_a = models.RoadSection.objects.create(
            road=self.road,
            start_chainage_km=0,
            end_chainage_km=1,
            length_km=1,
            surface_type="Earth",
        )
        self.section_b = models.RoadSection.objects.create(
            road=self.road,
            start_chainage_km=1,
            end_chainage_km=2,
            length_km=1,
            surface_type="Earth",
        )
        self.segment_a1 = models.RoadSegment.objects.create(
            section=self.section_a,
            station_from_km=0,
            station_to_km=0.5,
            cross_section="Flat",
            terrain_transverse="Flat",
            terrain_longitudinal="Flat",
        )
        self.segment_a2 = models.RoadSegment.objects.create(
            section=self.section_a,
            station_from_km=0.5,
            station_to_km=1,
            cross_section="Flat",
            terrain_transverse="Flat",
            terrain_longitudinal="Flat",
        )
        self.segment_b1 = models.RoadSegment.objects.create(
            section=self.section_b,
            station_from_km=0,
            station_to_km=1,
            cross_section="Flat",
            terrain_transverse="Flat",
            terrain_longitudinal="Flat",
        )
        self.structure_a = models.StructureInventory.objects.create(
            road=self.road,
            section=self.section_a,
            geometry_type=models.StructureInventory.POINT,
            station_km=0.25,
            location_point=make_point(13.55, 39.05),
            structure_category="Bridge",
        )
        self.structure_b = models.StructureInventory.objects.create(
            road=self.road,
            section=self.section_b,
            geometry_type=models.StructureInventory.POINT,
            station_km=1.5,
            location_point=make_point(13.65, 39.15),
            structure_category="Culvert",
        )

    def test_road_sections_geojson(self):
        url = reverse("map_road_sections_current", args=[self.road.id, self.section_a.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("type"), "FeatureCollection")
        roles = {f.get("properties", {}).get("role") for f in payload.get("features", [])}
        self.assertIn("road", roles)
        self.assertIn("section", roles)
        self.assertIn("section_current", roles)

    def test_section_segments_geojson(self):
        url = reverse("map_section_segments_current", args=[self.section_a.id, self.segment_a2.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        features = payload.get("features", [])
        segment_ids = {
            f.get("properties", {}).get("id")
            for f in features
            if f.get("properties", {}).get("role", "").startswith("segment")
        }
        self.assertEqual(segment_ids, {self.segment_a1.id, self.segment_a2.id})
        roles = {f.get("properties", {}).get("role") for f in features}
        self.assertIn("section_current", roles)
        self.assertIn("segment_current", roles)

    def test_structure_geojson_section_scoped(self):
        url = reverse(
            "map_section_structures_current",
            args=[self.road.id, self.section_a.id, self.structure_a.id],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        features = payload.get("features", [])
        structure_ids = {
            f.get("properties", {}).get("id")
            for f in features
            if f.get("properties", {}).get("role", "").startswith("structure")
        }
        self.assertEqual(structure_ids, {self.structure_a.id})
        roles = {f.get("properties", {}).get("role") for f in features}
        self.assertIn("structure_current", roles)
