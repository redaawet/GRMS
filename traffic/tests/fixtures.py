from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from grms.models import AdminWoreda, AdminZone, Road
from grms.utils import make_point
from traffic.models import (
    NightAdjustmentLookup,
    PcuLookup,
    TrafficCountRecord,
    TrafficSurvey,
)


@pytest.fixture
def admin_zone():
    return AdminZone.objects.create(name="Central")


@pytest.fixture
def admin_woreda(admin_zone):
    return AdminWoreda.objects.create(name="Test Woreda", zone=admin_zone)


@pytest.fixture
def road(admin_zone, admin_woreda):
    return Road.objects.create(
        road_identifier="RTR-1",
        road_name_from="A",
        road_name_to="B",
        design_standard="DC1",
        admin_zone=admin_zone,
        admin_woreda=admin_woreda,
        total_length_km=Decimal("10.5"),
        surface_type="Earth",
        managing_authority="Federal",
    )


@pytest.fixture
def night_adjustments():
    twelve = NightAdjustmentLookup.objects.create(
        hours_counted=12,
        adjustment_factor=Decimal("1.33"),
        effective_date=datetime.date(2020, 1, 1),
    )
    twenty_four = NightAdjustmentLookup.objects.create(
        hours_counted=24,
        adjustment_factor=Decimal("1.00"),
        effective_date=datetime.date(2020, 1, 1),
    )
    return twelve, twenty_four


@pytest.fixture
def pcu_defaults():
    entries = []
    for cls in [
        "Car",
        "LightGoods",
        "MiniBus",
        "MediumGoods",
        "HeavyGoods",
        "Bus",
        "Tractor",
        "Motorcycle",
        "Bicycle",
        "Pedestrian",
    ]:
        entries.append(
            PcuLookup.objects.create(
                vehicle_class=cls,
                pcu_factor=Decimal("1.0"),
                effective_date=datetime.date(2020, 1, 1),
            )
        )
    return entries


@pytest.fixture
def traffic_survey(road, night_adjustments):
    survey = TrafficSurvey.objects.create(
        road=road,
        survey_year=2024,
        cycle_number=1,
        count_start_date=datetime.date(2024, 1, 1),
        count_end_date=datetime.date(2024, 1, 7),
        count_days_per_cycle=7,
        count_hours_per_day=12,
        night_adjustment_factor=Decimal("0.00"),
        method="MOC",
        observer="Tester",
        station_location=make_point(12.0, 38.0),
    )
    return survey


@pytest.fixture
def traffic_counts(traffic_survey):
    records = []
    for idx in range(7):
        records.append(
            TrafficCountRecord.objects.create(
                traffic_survey=traffic_survey,
                count_date=traffic_survey.count_start_date + datetime.timedelta(days=idx),
                cars=10 + idx,
                light_goods=5,
                minibuses=2,
            )
        )
    return records
