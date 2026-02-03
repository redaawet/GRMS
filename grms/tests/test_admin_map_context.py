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
    return LineString((39.0, 13.5), (39.1, 13.6))


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
        geom = _make_linestring()
        if geom is None:
            self.skipTest("GEOS is required for map context tests.")

        self.road = models.Road.objects.create(
            road_identifier="RTR-1",
            road_name_from="Alpha",
            road_name_to="Bravo",
            design_standard="DC1",
            admin_zone=self.zone,
            total_length_km=1,
            surface_type="Gravel",
            managing_authority="Regional",
            geometry=geom,
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

    def test_map_context_roles(self):
        url = reverse("grms_maps:map_context")
        response = self.client.get(
            url,
            {
                "road_id": self.road.id,
                "section_id": self.section.id,
                "segment_id": self.segment.id,
                "structure_id": self.structure.id,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("type"), "FeatureCollection")
        features = payload.get("features", [])
        roles = {f.get("properties", {}).get("role") for f in features}
        self.assertIn("road", roles)
        self.assertIn("section_current", roles)
        self.assertIn("segment_current", roles)
        self.assertIn("structure_current", roles)

    def test_map_context_requires_staff(self):
        self.client.logout()
        url = reverse("grms_maps:map_context")
        response = self.client.get(url, {"road_id": self.road.id})
        self.assertIn(response.status_code, {302, 403})
