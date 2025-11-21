from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from grms import models
from grms.utils import make_point, utm_to_wgs84


class RoadSectionValidationTests(TestCase):
    def setUp(self):
        self.zone, _ = models.AdminZone.objects.get_or_create(name="Zone")
        self.woreda, _ = models.AdminWoreda.objects.get_or_create(name="Woreda", zone=self.zone)
        start_lat, start_lng = utm_to_wgs84(500000, 1000000, zone=37)
        end_lat, end_lng = utm_to_wgs84(500000, 1010000, zone=37)
        self.road = models.Road.objects.create(
            road_name_from="Start",
            road_name_to="End",
            design_standard="DC1",
            admin_zone=self.zone,
            admin_woreda=self.woreda,
            total_length_km=Decimal("10.0"),
            surface_type="Earth",
            managing_authority="Federal",
            population_served=1000,
            remarks="",
            start_easting=Decimal("500000.00"),
            start_northing=Decimal("1000000.00"),
            road_start_coordinates=make_point(start_lat, start_lng),
            end_easting=Decimal("500000.00"),
            end_northing=Decimal("1010000.00"),
            road_end_coordinates=make_point(end_lat, end_lng),
        )

    def _coords_for_chainage(self, start_km: Decimal, end_km: Decimal):
        start_easting = Decimal("500000.00")
        end_easting = Decimal("500000.00")
        start_northing = (Decimal("1000000.00") + start_km * Decimal("1000")).quantize(Decimal("0.01"))
        end_northing = (Decimal("1000000.00") + end_km * Decimal("1000")).quantize(Decimal("0.01"))
        start_lat, start_lng = utm_to_wgs84(float(start_easting), float(start_northing), zone=37)
        end_lat, end_lng = utm_to_wgs84(float(end_easting), float(end_northing), zone=37)
        return {
            "start_easting": start_easting,
            "start_northing": start_northing,
            "start_point": make_point(start_lat, start_lng),
            "end_easting": end_easting,
            "end_northing": end_northing,
            "end_point": make_point(end_lat, end_lng),
        }

    def test_missing_alignment_coordinates_fail_validation(self):
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
        self.assertIn("start_easting", ctx.exception.error_dict)
        self.assertIn("end_easting", ctx.exception.error_dict)

    def test_gap_between_sections_is_reported(self):
        coords_first = self._coords_for_chainage(Decimal("0"), Decimal("5"))
        models.RoadSection.objects.create(
            road=self.road,
            section_number=1,
            sequence_on_road=1,
            start_chainage_km=Decimal("0"),
            end_chainage_km=Decimal("5"),
            surface_type="Earth",
            start_easting=coords_first["start_easting"],
            start_northing=coords_first["start_northing"],
            section_start_coordinates=coords_first["start_point"],
            end_easting=coords_first["end_easting"],
            end_northing=coords_first["end_northing"],
            section_end_coordinates=coords_first["end_point"],
        )

        coords_second = self._coords_for_chainage(Decimal("7"), Decimal("10"))
        gap_section = models.RoadSection(
            road=self.road,
            section_number=2,
            sequence_on_road=2,
            start_chainage_km=Decimal("7"),
            end_chainage_km=Decimal("10"),
            surface_type="Earth",
            start_easting=coords_second["start_easting"],
            start_northing=coords_second["start_northing"],
            section_start_coordinates=coords_second["start_point"],
            end_easting=coords_second["end_easting"],
            end_northing=coords_second["end_northing"],
            section_end_coordinates=coords_second["end_point"],
        )

        with self.assertRaises(ValidationError) as ctx:
            gap_section.full_clean()
        message = ctx.exception.error_dict.get("start_chainage_km", [])[0].messages[0]
        self.assertIn("Gap detected before this section", message)

    def test_coordinate_length_matches_chainage(self):
        coords = self._coords_for_chainage(Decimal("0"), Decimal("8"))
        mismatch_section = models.RoadSection(
            road=self.road,
            section_number=1,
            sequence_on_road=1,
            start_chainage_km=Decimal("0"),
            end_chainage_km=Decimal("5"),
            surface_type="Earth",
            start_easting=coords["start_easting"],
            start_northing=coords["start_northing"],
            section_start_coordinates=coords["start_point"],
            end_easting=coords["end_easting"],
            end_northing=coords["end_northing"],
            section_end_coordinates=coords["end_point"],
        )

        with self.assertRaises(ValidationError) as ctx:
            mismatch_section.full_clean()
        self.assertIn("Coordinate distance", ctx.exception.error_dict.get("end_easting", [])[0].messages[0])
