"""Tests for prioritization workflow and survey calculations."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from grms import models
from grms.utils import make_point, utm_to_wgs84
from traffic import models as traffic_models


class RoadNetworkMixin:
    """Utility helpers to create minimal road/segment hierarchies for tests."""

    def create_network(self, prefix: str = "Test"):
        zone, _ = models.AdminZone.objects.get_or_create(name="Zone")
        woreda, _ = models.AdminWoreda.objects.get_or_create(name="Woreda", zone=zone)
        missing_coords = "Missing" in prefix
        start_lat, start_lng = utm_to_wgs84(500000, 1000000, zone=37)
        end_lat, end_lng = utm_to_wgs84(500000, 1010000, zone=37)

        road_kwargs = dict(
            road_name_from=f"{prefix} From",
            road_name_to=f"{prefix} To",
            design_standard="DC1",
            admin_zone=zone,
            admin_woreda=woreda,
            total_length_km=Decimal("10.0"),
            surface_type="Earth",
            managing_authority="Federal",
            population_served=1000,
            remarks="",
        )

        if not missing_coords:
            road_kwargs.update(
                start_easting=Decimal("500000.00"),
                start_northing=Decimal("1000000.00"),
                road_start_coordinates=make_point(start_lat, start_lng),
                end_easting=Decimal("500000.00"),
                end_northing=Decimal("1010000.00"),
                road_end_coordinates=make_point(end_lat, end_lng),
            )

        road = models.Road.objects.create(**road_kwargs)
        section_start_lat, section_start_lng = utm_to_wgs84(500000, 1000000, zone=37)
        section_end_lat, section_end_lng = utm_to_wgs84(500000, 1010000, zone=37)

        section = models.RoadSection.objects.create(
            road=road,
            section_number=1,
            start_chainage_km=Decimal("0"),
            end_chainage_km=Decimal("10"),
            length_km=Decimal("10"),
            surface_type="Earth",
            start_easting=Decimal("500000.00"),
            start_northing=Decimal("1000000.00"),
            section_start_coordinates=make_point(section_start_lat, section_start_lng),
            end_easting=Decimal("500000.00"),
            end_northing=Decimal("1010000.00"),
            section_end_coordinates=make_point(section_end_lat, section_end_lng),
        )
        segment = models.RoadSegment.objects.create(
            section=section,
            station_from_km=Decimal("0"),
            station_to_km=Decimal("5"),
            cross_section="Cutting",
            terrain_transverse="Flat",
            terrain_longitudinal="Flat",
        )
        return road, section, segment


class RoadConditionSurveyTests(RoadNetworkMixin, TestCase):
    """Unit tests for the automatic MCI calculation."""

    def test_save_populates_calculated_mci(self):
        _, _, segment = self.create_network("MCI")
        survey = models.RoadConditionSurvey.objects.create(
            road_segment=segment,
            surface_condition_factor=Decimal("3.5"),
            drainage_condition_left=Decimal("4.0"),
            drainage_condition_right=Decimal("3.0"),
            shoulder_condition_left=Decimal("4.5"),
            shoulder_condition_right=Decimal("2.0"),
            inspection_date=date(2024, 1, 1),
        )
        # Average of the five factors is 3.4 -> 68.0 after scaling.
        self.assertEqual(survey.calculated_mci, Decimal("68.0"))


class PrioritizationViewTests(RoadNetworkMixin, APITestCase):
    """Integration tests for the prioritization API endpoint."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        user = get_user_model().objects.create_user(username="tester", password="pass1234")
        self.client.force_authenticate(user=user)
        self.fiscal_year = 2024

    def _create_inputs(self, prefix: str, pcu_value: Decimal, benefit_score: Decimal, survey_values: list[Decimal]):
        road, _, segment = self.create_network(prefix)
        models.RoadConditionSurvey.objects.create(
            road_segment=segment,
            surface_condition_factor=survey_values[0],
            drainage_condition_left=survey_values[1],
            drainage_condition_right=survey_values[2],
            shoulder_condition_left=survey_values[3],
            shoulder_condition_right=survey_values[4],
            inspection_date=date(2024, 1, 1),
        )
        traffic_models.TrafficForPrioritization.objects.create(
            road=road,
            fiscal_year=self.fiscal_year,
            value_type="PCU",
            value=pcu_value,
        )
        models.BenefitFactor.objects.create(
            road=road,
            fiscal_year=self.fiscal_year,
            total_benefit_score=benefit_score,
        )
        return road

    def _expected_score(self, cs_norm: float, pcu_value: float, ei_score: float, weights: dict[str, float], pcu_min: float, pcu_max: float) -> Decimal:
        if pcu_max != pcu_min:
            pcu_norm = 100.0 * (pcu_value - pcu_min) / (pcu_max - pcu_min)
            pcu_norm = max(0.0, min(100.0, pcu_norm))
        else:
            pcu_norm = 0.0
        priority_score = (
            weights["w1"] * cs_norm
            + weights["w2"] * pcu_norm
            + weights["w3"] * ei_score
            + weights["w4"] * 0.0
            + weights["w5"] * 0.0
        )
        return Decimal(f"{priority_score:.4f}")

    def test_prioritization_orders_roads_and_returns_expected_scores(self):
        weights = {"w1": 0.40, "w2": 0.25, "w3": 0.15, "w4": 0.10, "w5": 0.10}
        high = self._create_inputs(
            prefix="Alpha",
            pcu_value=Decimal("200"),
            benefit_score=Decimal("70"),
            survey_values=[Decimal("4.5"), Decimal("4.0"), Decimal("4.0"), Decimal("4.0"), Decimal("3.5")],
        )
        low = self._create_inputs(
            prefix="Beta",
            pcu_value=Decimal("80"),
            benefit_score=Decimal("40"),
            survey_values=[Decimal("3.0"), Decimal("2.5"), Decimal("3.0"), Decimal("2.5"), Decimal("2.5")],
        )

        url = reverse("run_prioritization")
        response = self.client.post(url, {"fiscal_year": self.fiscal_year, "weights": weights}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual([item["priority_rank"] for item in data], [1, 2])
        self.assertEqual(data[0]["road"], high.id)

        surveys = models.RoadConditionSurvey.objects.order_by("road_segment__section__road__id")
        cs_values = [float(s.calculated_mci) for s in surveys]
        pcu_values = [float(t.value) for t in traffic_models.TrafficForPrioritization.objects.all()]
        benefits = [float(b.total_benefit_score) for b in models.BenefitFactor.objects.all()]

        expected_high = self._expected_score(cs_values[0], pcu_values[0], benefits[0], weights, min(pcu_values), max(pcu_values))
        expected_low = self._expected_score(cs_values[1], pcu_values[1], benefits[1], weights, min(pcu_values), max(pcu_values))

        self.assertEqual(Decimal(data[0]["ranking_index"]), expected_high)
        self.assertEqual(Decimal(data[1]["ranking_index"]), expected_low)
        self.assertEqual(models.PrioritizationResult.objects.count(), 2)

    def test_prioritization_handles_constant_pcu_values(self):
        weights = {"w1": 0.6, "w2": 0.2, "w3": 0.2, "w4": 0.0, "w5": 0.0}
        road = self._create_inputs(
            prefix="Gamma",
            pcu_value=Decimal("120"),
            benefit_score=Decimal("55"),
            survey_values=[Decimal("4.0"), Decimal("3.5"), Decimal("3.5"), Decimal("3.0"), Decimal("3.0")],
        )

        url = reverse("run_prioritization")
        response = self.client.post(url, {"fiscal_year": self.fiscal_year, "weights": weights}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["priority_rank"], 1)
        self.assertEqual(data[0]["road"], road.id)

        survey = models.RoadConditionSurvey.objects.get(road_segment__section__road=road)
        expected = self._expected_score(float(survey.calculated_mci), 120.0, 55.0, weights, 120.0, 120.0)
        self.assertEqual(Decimal(data[0]["ranking_index"]), expected)
