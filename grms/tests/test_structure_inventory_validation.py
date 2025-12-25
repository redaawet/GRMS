from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from grms import models


class StructureInventoryValidationTests(TestCase):
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

    def test_section_must_belong_to_selected_road(self):
        section = models.RoadSection.objects.create(
            road=self.other_road,
            start_chainage_km=Decimal("0"),
            end_chainage_km=Decimal("5"),
            surface_type="Earth",
        )

        structure = models.StructureInventory(
            road=self.road,
            section=section,
            structure_category="Bridge",
            station_km=Decimal("1.0"),
        )

        with self.assertRaises(ValidationError) as ctx:
            structure.full_clean()

        self.assertIn("section", ctx.exception.error_dict)
        self.assertEqual(
            ctx.exception.error_dict["section"][0].message,
            "Selected section does not belong to the selected road.",
        )
