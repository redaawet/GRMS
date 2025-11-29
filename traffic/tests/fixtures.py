from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Callable, Dict, Iterable, List, Mapping

import pytest
from grms.models import AdminWoreda, AdminZone, Road
from grms.utils import make_point
from traffic.models import (
    NightAdjustmentLookup,
    PcuLookup,
    TrafficCountRecord,
    TrafficSurvey,
)

PCU_FACTORS: Mapping[str, Decimal] = {
    "Car": Decimal("1.00"),
    "LightGoods": Decimal("1.200"),
    "MiniBus": Decimal("1.500"),
    "MediumGoods": Decimal("2.500"),
    "HeavyGoods": Decimal("3.500"),
    "Bus": Decimal("3.000"),
    "Tractor": Decimal("4.000"),
    "Motorcycle": Decimal("0.500"),
    "Bicycle": Decimal("0.200"),
    "Pedestrian": Decimal("0.100"),
}

VEHICLE_CLASS_FIELDS: Mapping[str, str] = {
    "Car": "cars",
    "LightGoods": "light_goods",
    "MiniBus": "minibuses",
    "MediumGoods": "medium_goods",
    "HeavyGoods": "heavy_goods",
    "Bus": "buses",
    "Tractor": "tractors",
    "Motorcycle": "motorcycles",
    "Bicycle": "bicycles",
    "Pedestrian": "pedestrians",
}

CYCLE_BASE_COUNTS: Mapping[int, Mapping[str, int]] = {
    1: {
        "Car": 120,
        "LightGoods": 60,
        "MiniBus": 45,
        "MediumGoods": 20,
        "HeavyGoods": 8,
        "Bus": 10,
        "Tractor": 5,
        "Motorcycle": 70,
        "Bicycle": 30,
        "Pedestrian": 150,
    },
    2: {
        "Car": 160,
        "LightGoods": 90,
        "MiniBus": 60,
        "MediumGoods": 25,
        "HeavyGoods": 10,
        "Bus": 15,
        "Tractor": 6,
        "Motorcycle": 90,
        "Bicycle": 40,
        "Pedestrian": 200,
    },
    3: {
        "Car": 100,
        "LightGoods": 50,
        "MiniBus": 30,
        "MediumGoods": 15,
        "HeavyGoods": 5,
        "Bus": 8,
        "Tractor": 4,
        "Motorcycle": 60,
        "Bicycle": 25,
        "Pedestrian": 120,
    },
}

DAY_VARIATIONS: List[Mapping[str, Decimal | bool]] = [
    {"multiplier": Decimal("1.00"), "is_market_day": False},
    {"multiplier": Decimal("1.05"), "is_market_day": False},
    {"multiplier": Decimal("0.95"), "is_market_day": False},
    {"multiplier": Decimal("1.35"), "is_market_day": True},  # market day spike
    {"multiplier": Decimal("1.10"), "is_market_day": False},
    {"multiplier": Decimal("0.60"), "is_market_day": False},  # weather-disrupted day
    {"multiplier": Decimal("0.90"), "is_market_day": False},
]


@pytest.fixture
def admin_zone() -> AdminZone:
    return AdminZone.objects.create(name="Tigray")


@pytest.fixture
def admin_woreda(admin_zone: AdminZone) -> AdminWoreda:
    return AdminWoreda.objects.create(name="Mekelle Woreda", zone=admin_zone)


@pytest.fixture
def road(admin_zone: AdminZone, admin_woreda: AdminWoreda) -> Road:
    return Road.objects.create(
        road_identifier="RTR-101",
        road_name_from="Mekelle",
        road_name_to="Wukro",
        design_standard="DC2",
        admin_zone=admin_zone,
        admin_woreda=admin_woreda,
        total_length_km=Decimal("46.2"),
        surface_type="Gravel",
        managing_authority="Regional",
    )


@pytest.fixture
def night_adjustments() -> Iterable[NightAdjustmentLookup]:
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
def pcu_defaults() -> List[PcuLookup]:
    entries: List[PcuLookup] = []
    for vehicle_class, pcu_factor in PCU_FACTORS.items():
        entries.append(
            PcuLookup.objects.create(
                vehicle_class=vehicle_class,
                pcu_factor=pcu_factor,
                effective_date=datetime.date(2020, 1, 1),
            )
        )
    return entries


def _build_weekly_counts(base_counts: Mapping[str, int]) -> List[Mapping[str, int | bool]]:
    weekly_counts: List[Mapping[str, int | bool]] = []
    for idx, variation in enumerate(DAY_VARIATIONS):
        multiplier: Decimal = variation["multiplier"]  # type: ignore[assignment]
        is_market_day: bool = bool(variation.get("is_market_day", False))
        day_counts: Dict[str, int | bool] = {"is_market_day": is_market_day}
        for vehicle_class, base_value in base_counts.items():
            field_name = VEHICLE_CLASS_FIELDS[vehicle_class]
            day_counts[field_name] = int((Decimal(base_value) * multiplier).to_integral_value(rounding="ROUND_HALF_UP"))
        weekly_counts.append(day_counts)
    return weekly_counts


def _default_cycle_start_date(cycle_number: int) -> datetime.date:
    month = {1: 1, 2: 5, 3: 9}.get(cycle_number, 1)
    return datetime.date(2024, month, 1)


@pytest.fixture
def create_cycle(road: Road, night_adjustments: Iterable[NightAdjustmentLookup]) -> Callable[[int, Mapping[str, int]], TrafficSurvey]:
    def _create_cycle(cycle_number: int, daily_counts: Mapping[str, int]) -> TrafficSurvey:
        count_start_date = _default_cycle_start_date(cycle_number)
        survey = TrafficSurvey.objects.create(
            road=road,
            survey_year=2024,
            cycle_number=cycle_number,
            count_start_date=count_start_date,
            count_end_date=count_start_date + datetime.timedelta(days=6),
            count_days_per_cycle=7,
            count_hours_per_day=12,
            night_adjustment_factor=Decimal("1.33"),
            method="MOC",
            observer="ERA Test Team",
            station_location=make_point(13.49, 39.47),
        )

        weekly_counts = _build_weekly_counts(daily_counts)
        for offset, day_counts in enumerate(weekly_counts):
            TrafficCountRecord.objects.create(
                traffic_survey=survey,
                count_date=count_start_date + datetime.timedelta(days=offset),
                **day_counts,
            )
        return survey

    return _create_cycle


@pytest.fixture
def traffic_survey(create_cycle: Callable[[int, Mapping[str, int]], TrafficSurvey]) -> TrafficSurvey:
    return create_cycle(1, CYCLE_BASE_COUNTS[1])


@pytest.fixture
def traffic_counts(traffic_survey: TrafficSurvey) -> List[TrafficCountRecord]:
    return list(traffic_survey.count_records.order_by("count_date"))


@pytest.fixture
def cycle_two_survey(create_cycle: Callable[[int, Mapping[str, int]], TrafficSurvey]) -> TrafficSurvey:
    return create_cycle(2, CYCLE_BASE_COUNTS[2])


@pytest.fixture
def cycle_three_survey(create_cycle: Callable[[int, Mapping[str, int]], TrafficSurvey]) -> TrafficSurvey:
    return create_cycle(3, CYCLE_BASE_COUNTS[3])


@pytest.fixture
def all_cycle_surveys(
    traffic_survey: TrafficSurvey,
    cycle_two_survey: TrafficSurvey,
    cycle_three_survey: TrafficSurvey,
) -> Iterable[TrafficSurvey]:
    return (traffic_survey, cycle_two_survey, cycle_three_survey)
