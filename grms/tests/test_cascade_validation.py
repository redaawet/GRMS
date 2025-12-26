from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from grms import models
from grms.admin import (
    FurnitureConditionSurveyForm,
    RoadConditionSurveyForm,
    RoadSegmentAdminForm,
    StructureConditionSurveyForm,
    StructureInventoryAdmin,
)
from grms.admin import grms_admin_site


class CascadeValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.factory = RequestFactory()
        self.zone, _ = models.AdminZone.objects.get_or_create(name="Zone")
        self.woreda, _ = models.AdminWoreda.objects.get_or_create(name="Woreda", zone=self.zone)
        self.road = models.Road.objects.create(
            road_name_from="Start",
            road_name_to="End",
            design_standard="DC1",
            admin_zone=self.zone,
            admin_woreda=self.woreda,
            total_length_km=Decimal("10.0"),
            surface_type="Earth",
            managing_authority="Federal",
            remarks="",
            geometry={"type": "LineString", "coordinates": [[40.0, 10.0], [40.0, 20.0]]},
        )
        self.other_road = models.Road.objects.create(
            road_name_from="Other Start",
            road_name_to="Other End",
            design_standard="DC1",
            admin_zone=self.zone,
            admin_woreda=self.woreda,
            total_length_km=Decimal("10.0"),
            surface_type="Earth",
            managing_authority="Federal",
            remarks="",
            geometry={"type": "LineString", "coordinates": [[41.0, 10.0], [41.0, 20.0]]},
        )
        self.section = models.RoadSection.objects.create(
            road=self.road,
            start_chainage_km=Decimal("0"),
            end_chainage_km=Decimal("5"),
            surface_type="Earth",
        )
        self.other_section = models.RoadSection.objects.create(
            road=self.other_road,
            start_chainage_km=Decimal("0"),
            end_chainage_km=Decimal("5"),
            surface_type="Earth",
        )
        self.segment = models.RoadSegment.objects.create(
            section=self.section,
            station_from_km=Decimal("0"),
            station_to_km=Decimal("1"),
            cross_section="Flat",
            terrain_transverse="Flat",
            terrain_longitudinal="Flat",
        )
        self.other_segment = models.RoadSegment.objects.create(
            section=self.other_section,
            station_from_km=Decimal("0"),
            station_to_km=Decimal("1"),
            cross_section="Flat",
            terrain_transverse="Flat",
            terrain_longitudinal="Flat",
        )
        self.structure = models.StructureInventory.objects.create(
            road=self.road,
            section=self.section,
            structure_category="Bridge",
            station_km=Decimal("1.0"),
        )
        self.other_structure = models.StructureInventory.objects.create(
            road=self.other_road,
            section=self.other_section,
            structure_category="Bridge",
            station_km=Decimal("1.0"),
        )
        self.furniture = models.FurnitureInventory.objects.create(
            section=self.section,
            furniture_type=models.FurnitureInventory.KM_POST,
            chainage_km=Decimal("0.5"),
        )
        self.other_furniture = models.FurnitureInventory.objects.create(
            section=self.other_section,
            furniture_type=models.FurnitureInventory.KM_POST,
            chainage_km=Decimal("0.5"),
        )

    def test_section_queryset_filters_by_road(self):
        form = RoadSegmentAdminForm(data={"road": self.road.id})
        section_ids = set(
            form.fields["section"].queryset.values_list("id", flat=True)
        )
        self.assertEqual(section_ids, {self.section.id})

    def test_section_queryset_none_without_road(self):
        form = RoadSegmentAdminForm()
        self.assertFalse(form.fields["section"].queryset.exists())

    def test_section_queryset_filters_for_structure_inventory(self):
        form = StructureInventoryAdmin.form(data={"road": self.road.id})
        section_ids = set(form.fields["section"].queryset.values_list("id", flat=True))
        self.assertEqual(section_ids, {self.section.id})

    def test_segment_queryset_filters_by_section(self):
        form = RoadConditionSurveyForm(data={"section": self.section.id})
        segment_ids = set(
            form.fields["road_segment"].queryset.values_list("id", flat=True)
        )
        self.assertEqual(segment_ids, {self.segment.id})

    def test_segment_queryset_none_without_section(self):
        form = RoadConditionSurveyForm()
        self.assertFalse(form.fields["road_segment"].queryset.exists())

    def test_structure_queryset_none_without_road(self):
        form = StructureConditionSurveyForm()
        self.assertFalse(form.fields["structure"].queryset.exists())

    def test_furniture_queryset_none_without_road(self):
        form = FurnitureConditionSurveyForm()
        self.assertFalse(form.fields["furniture"].queryset.exists())

    def test_mismatched_road_and_section_is_rejected(self):
        form = RoadSegmentAdminForm(
            data={
                "road": self.road.id,
                "section": self.other_section.id,
                "station_from_km": "0",
                "station_to_km": "1",
                "cross_section": "Flat",
                "terrain_transverse": "Flat",
                "terrain_longitudinal": "Flat",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["section"][0],
            "Selected section does not belong to the selected road.",
        )

    def test_mismatched_section_and_segment_is_rejected(self):
        form = RoadConditionSurveyForm(
            data={
                "road": self.road.id,
                "section": self.section.id,
                "road_segment": self.other_segment.id,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["road_segment"][0],
            "Selected segment does not belong to the selected section.",
        )

    def test_mismatched_road_and_structure_is_rejected(self):
        form = StructureConditionSurveyForm(
            data={
                "road_filter": self.other_road.id,
                "section_filter": self.other_section.id,
                "structure": self.structure.id,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["structure"][0],
            "Selected structure does not belong to the selected road.",
        )

    def test_mismatched_section_and_structure_is_rejected(self):
        form = StructureConditionSurveyForm(
            data={
                "road_filter": self.road.id,
                "section_filter": self.other_section.id,
                "structure": self.structure.id,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["structure"][0],
            "Selected structure does not belong to the selected section.",
        )

    def test_mismatched_road_and_furniture_is_rejected(self):
        form = FurnitureConditionSurveyForm(
            data={
                "road_filter": self.other_road.id,
                "section_filter": self.other_section.id,
                "furniture": self.furniture.id,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["furniture"][0],
            "Selected furniture does not belong to the selected road.",
        )

    def test_mismatched_section_and_furniture_is_rejected(self):
        form = FurnitureConditionSurveyForm(
            data={
                "road_filter": self.road.id,
                "section_filter": self.other_section.id,
                "furniture": self.furniture.id,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["furniture"][0],
            "Selected furniture does not belong to the selected section.",
        )

    def test_valid_hierarchy_saves(self):
        form = RoadConditionSurveyForm(
            data={
                "road": self.road.id,
                "section": self.section.id,
                "road_segment": self.segment.id,
            }
        )

        self.assertTrue(form.is_valid())
        survey = form.save()
        self.assertEqual(survey.road_segment_id, self.segment.id)

    def test_section_autocomplete_filters_by_road(self):
        admin_instance = grms_admin_site._registry[models.RoadSection]
        request = self.factory.get("/admin/grms/roadsection/autocomplete/", {"road_id": self.road.id})
        request.user = self.user
        qs, _ = admin_instance.get_search_results(request, models.RoadSection.objects.all(), "")
        self.assertEqual(set(qs), {self.section})

    def test_segment_autocomplete_filters_by_section(self):
        admin_instance = grms_admin_site._registry[models.RoadSegment]
        request = self.factory.get("/admin/grms/roadsegment/autocomplete/", {"section_id": self.section.id})
        request.user = self.user
        qs, _ = admin_instance.get_search_results(request, models.RoadSegment.objects.all(), "")
        self.assertEqual(set(qs), {self.segment})

    def test_structure_autocomplete_filters_by_road_and_section(self):
        admin_instance = grms_admin_site._registry[models.StructureInventory]
        request = self.factory.get(
            "/admin/grms/structureinventory/autocomplete/",
            {"road_id": self.road.id, "section_id": self.section.id},
        )
        request.user = self.user
        qs, _ = admin_instance.get_search_results(request, models.StructureInventory.objects.all(), "")
        self.assertEqual(set(qs), {self.structure})

    def test_furniture_autocomplete_filters_by_road_and_section(self):
        admin_instance = grms_admin_site._registry[models.FurnitureInventory]
        request = self.factory.get(
            "/admin/grms/furnitureinventory/autocomplete/",
            {"road_id": self.road.id, "section_id": self.section.id},
        )
        request.user = self.user
        qs, _ = admin_instance.get_search_results(request, models.FurnitureInventory.objects.all(), "")
        self.assertEqual(set(qs), {self.furniture})
