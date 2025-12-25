from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from grms import models
from grms.admin import RoadConditionSurveyForm, RoadSegmentAdminForm


class CascadeValidationTests(TestCase):
    def setUp(self):
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
