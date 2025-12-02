from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from grms import models


class RoadSectionValidationTests(TestCase):
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
        models.RoadSocioEconomic.objects.create(road=self.road, population_served=1000)

    def test_requires_parent_geometry(self):
        self.road.geometry = None
        self.road.save()

        section = models.RoadSection(
            road=self.road,
            section_number=1,
            sequence_on_road=1,
            name="Section 1",
            start_chainage_km=Decimal("0"),
            end_chainage_km=Decimal("5"),
            surface_type="Earth",
        )

        with self.assertRaises(ValidationError) as ctx:
            section.full_clean()
        self.assertIn("road", ctx.exception.error_dict)

    def test_negative_start_chainage_is_rejected(self):
        section = models.RoadSection(
            road=self.road,
            section_number=1,
            sequence_on_road=1,
            start_chainage_km=Decimal("-1"),
            end_chainage_km=Decimal("2"),
            surface_type="Earth",
        )

        with self.assertRaises(ValidationError) as ctx:
            section.full_clean()
        self.assertIn("start_chainage_km", ctx.exception.error_dict)

    def test_end_chainage_must_exceed_start(self):
        section = models.RoadSection(
            road=self.road,
            section_number=1,
            sequence_on_road=1,
            start_chainage_km=Decimal("5"),
            end_chainage_km=Decimal("5"),
            surface_type="Earth",
        )

        with self.assertRaises(ValidationError) as ctx:
            section.full_clean()
        self.assertIn("end_chainage_km", ctx.exception.error_dict)

    def test_end_chainage_cannot_exceed_road(self):
        section = models.RoadSection(
            road=self.road,
            section_number=1,
            sequence_on_road=1,
            start_chainage_km=Decimal("0"),
            end_chainage_km=Decimal("12"),
            surface_type="Earth",
        )

        with self.assertRaises(ValidationError) as ctx:
            section.full_clean()
        self.assertIn("end_chainage_km", ctx.exception.error_dict)

    def test_gap_between_sections_is_reported(self):
        models.RoadSection.objects.create(
            road=self.road,
            section_number=1,
            sequence_on_road=1,
            start_chainage_km=Decimal("0"),
            end_chainage_km=Decimal("5"),
            surface_type="Earth",
        )

        gap_section = models.RoadSection(
            road=self.road,
            section_number=2,
            sequence_on_road=2,
            start_chainage_km=Decimal("7"),
            end_chainage_km=Decimal("10"),
            surface_type="Earth",
        )

        with self.assertRaises(ValidationError) as ctx:
            gap_section.full_clean()
        message = ctx.exception.error_dict.get("start_chainage_km", [])[0].messages[0]
        self.assertIn("Gap detected before this section", message)
