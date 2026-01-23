from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString
from django.test import RequestFactory, TestCase

from grms import models
from grms.admin import RoadSectionAdmin, RoadSegmentAdmin, grms_admin_site


class AdminAutocompleteFilterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.zone = models.AdminZone.objects.create(name="Zone")
        self.woreda = models.AdminWoreda.objects.create(name="Woreda", zone=self.zone)
        self.road_a = self._make_road("RTR-1", LineString((0, 0), (0, 0.1)))
        self.road_b = self._make_road("RTR-2", LineString((1, 0), (1, 0.1)))

        self.section_a = self._make_section(self.road_a, Decimal("0"), Decimal("1"))
        self.section_b = self._make_section(self.road_b, Decimal("0"), Decimal("1"))

        self.segment_a = self._make_segment(self.section_a, Decimal("0"), Decimal("0.5"))
        self.segment_b = self._make_segment(self.section_b, Decimal("0"), Decimal("0.5"))

    def _make_road(self, identifier, geometry):
        return models.Road.objects.create(
            road_identifier=identifier,
            road_name_from="Start",
            road_name_to="End",
            design_standard="DC1",
            admin_zone=self.zone,
            admin_woreda=self.woreda,
            total_length_km=Decimal("10.0"),
            surface_type="Earth",
            managing_authority="Federal",
            remarks="",
            geometry=geometry,
        )

    def _make_section(self, road, start_km, end_km):
        return models.RoadSection.objects.create(
            road=road,
            start_chainage_km=start_km,
            end_chainage_km=end_km,
            surface_type="Earth",
        )

    def _make_segment(self, section, start_km, end_km):
        return models.RoadSegment.objects.create(
            section=section,
            station_from_km=start_km,
            station_to_km=end_km,
            cross_section="Cutting",
            terrain_transverse="Flat",
            terrain_longitudinal="Flat",
        )

    def test_section_autocomplete_filters_by_road_id(self):
        request = self.factory.get("/admin/autocomplete/", {"road_id": str(self.road_a.id)})
        request.user = self.user
        admin_instance = RoadSectionAdmin(models.RoadSection, grms_admin_site)

        queryset, _ = admin_instance.get_search_results(
            request, models.RoadSection.objects.all(), ""
        )

        self.assertEqual(set(queryset), {self.section_a})

    def test_section_autocomplete_returns_all_without_road_id(self):
        request = self.factory.get("/admin/autocomplete/")
        request.user = self.user
        admin_instance = RoadSectionAdmin(models.RoadSection, grms_admin_site)

        queryset, _ = admin_instance.get_search_results(
            request, models.RoadSection.objects.all(), ""
        )

        self.assertEqual(set(queryset), {self.section_a, self.section_b})

    def test_segment_autocomplete_filters_by_section_id(self):
        request = self.factory.get("/admin/autocomplete/", {"section_id": str(self.section_a.id)})
        request.user = self.user
        admin_instance = RoadSegmentAdmin(models.RoadSegment, grms_admin_site)

        queryset, _ = admin_instance.get_search_results(
            request, models.RoadSegment.objects.all(), ""
        )

        self.assertEqual(set(queryset), {self.segment_a})
