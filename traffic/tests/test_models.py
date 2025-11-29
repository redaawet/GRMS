from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from traffic.models import (
    NightAdjustmentLookup,
    PcuLookup,
    TrafficCountRecord,
    TrafficCycleSummary,
    TrafficForPrioritization,
    TrafficQc,
    TrafficSurvey,
    TrafficSurveySummary,
    compute_confidence_score_for_survey,
    promote_survey_to_prioritization,
    recompute_cycle_summaries_for_survey,
    recompute_survey_summary_for_survey,
    run_auto_qc_for_survey,
)
from traffic.tests.fixtures import PCU_FACTORS, traffic_counts


def q3(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"))


def test_create_survey_with_valid_fields(traffic_survey):
    survey = traffic_survey
    survey.refresh_from_db()
    assert survey.road is not None
    assert survey.night_adjustment_factor == Decimal("1.33")
    assert survey.station_location is not None


def test_count_hours_validation_creates_qc_issue(traffic_survey):
    traffic_survey.count_hours_per_day = 10
    traffic_survey.save()

    run_auto_qc_for_survey(traffic_survey)
    issue = TrafficQc.objects.filter(traffic_survey=traffic_survey, issue_type="Hour mismatch").first()
    assert issue is not None
    assert issue.qc_source == "SYSTEM"


def test_night_adjustment_default_value(night_adjustments, road):
    survey = TrafficSurvey.objects.create(
        road=road,
        survey_year=2024,
        cycle_number=2,
        count_start_date=datetime.date(2024, 2, 1),
        count_end_date=datetime.date(2024, 2, 7),
        count_days_per_cycle=7,
        count_hours_per_day=12,
        night_adjustment_factor=Decimal("0"),
        method="MOC",
        observer="Auto",
    )
    survey.refresh_from_db()
    assert survey.night_adjustment_factor == Decimal("1.33")


def test_station_location_saved(traffic_survey):
    assert traffic_survey.station_location is not None


def test_qa_status_workflow(traffic_survey):
    traffic_survey.qa_status = "In Review"
    traffic_survey.save(update_fields=["qa_status"])

    traffic_survey.approve()
    traffic_survey.refresh_from_db()

    assert traffic_survey.qa_status == "Approved"
    assert traffic_survey.approved_at is not None
    assert traffic_survey.approved_at <= timezone.now()


def test_create_raw_traffic_record(traffic_survey):
    record = TrafficCountRecord.objects.create(
        traffic_survey=traffic_survey,
        count_date=traffic_survey.count_start_date,
    )
    assert record.cars == 0
    assert record.light_goods == 0
    assert record.traffic_survey.road == traffic_survey.road


def test_daily_grouping_logic(traffic_counts, pcu_defaults):
    survey = traffic_counts[0].traffic_survey
    recompute_cycle_summaries_for_survey(survey)

    car_summary = TrafficCycleSummary.objects.get(
        traffic_survey=survey, vehicle_class="Car", cycle_number=survey.cycle_number
    )
    expected_days = survey.count_days_per_cycle
    expected_sum = sum(r.cars for r in traffic_counts)
    expected_avg = Decimal(expected_sum) / Decimal(expected_days)
    expected_adt = q3(expected_avg * survey.night_adjustment_factor)

    assert car_summary.cycle_days_counted == expected_days
    assert car_summary.cycle_sum_count == expected_sum
    assert car_summary.cycle_daily_avg == q3(expected_avg)
    assert car_summary.cycle_daily_24hr == expected_adt
    assert car_summary.cycle_pcu == expected_adt * PCU_FACTORS["Car"]


def test_pcu_lookup_best_effective_date_selection(pcu_defaults):
    base = pcu_defaults[0]
    newer = PcuLookup.objects.create(
        vehicle_class="Car",
        pcu_factor=Decimal("1.5"),
        effective_date=datetime.date(2024, 1, 1),
    )
    factor = PcuLookup.get_effective_factor("Car", datetime.date(2024, 2, 1))
    assert factor == newer.pcu_factor


def test_pcu_lookup_region_preference(pcu_defaults, admin_zone):
    PcuLookup.objects.create(
        vehicle_class="Car",
        pcu_factor=Decimal("2.0"),
        effective_date=datetime.date(2024, 1, 1),
        region=admin_zone.name,
    )
    factor = PcuLookup.get_effective_factor("Car", datetime.date(2024, 2, 1), region=admin_zone.name)
    assert factor == Decimal("2.0")


def test_night_adjustment_lookup_returns_factor(night_adjustments):
    factor_12 = NightAdjustmentLookup.get_factor(12, datetime.date(2024, 1, 5))
    factor_24 = NightAdjustmentLookup.get_factor(24, datetime.date(2024, 1, 5))
    assert factor_12 == Decimal("1.33")
    assert factor_24 == Decimal("1.00")


def test_cycle_summary_computation(traffic_counts, pcu_defaults):
    survey = traffic_counts[0].traffic_survey
    recompute_cycle_summaries_for_survey(survey)

    summary = TrafficCycleSummary.objects.get(
        traffic_survey=survey, vehicle_class="MiniBus", cycle_number=survey.cycle_number
    )
    expected_sum = sum(r.minibuses for r in traffic_counts)
    expected_avg = Decimal(expected_sum) / Decimal(survey.count_days_per_cycle)
    expected_adt = q3(expected_avg * survey.night_adjustment_factor)
    expected_pcu = expected_adt * PCU_FACTORS["MiniBus"]

    assert summary.cycle_days_counted == survey.count_days_per_cycle
    assert summary.cycle_sum_count == expected_sum
    assert summary.cycle_daily_avg == q3(expected_avg)
    assert summary.cycle_daily_24hr == expected_adt
    assert summary.cycle_pcu == expected_pcu


def test_qc_flag_missing_data(traffic_survey, pcu_defaults):
    run_auto_qc_for_survey(traffic_survey)
    issue = TrafficQc.objects.filter(traffic_survey=traffic_survey, issue_type="Missing days").first()
    assert issue is None


def test_survey_summary_computation(traffic_counts, pcu_defaults):
    survey = traffic_counts[0].traffic_survey
    recompute_cycle_summaries_for_survey(survey)
    recompute_survey_summary_for_survey(survey)

    summary = TrafficSurveySummary.objects.get(traffic_survey=survey, vehicle_class="Car")
    expected_sum = sum(r.cars for r in traffic_counts)
    expected_avg = Decimal(expected_sum) / Decimal(survey.count_days_per_cycle)
    expected_adt = q3(expected_avg * survey.night_adjustment_factor)

    assert summary.avg_daily_count_all_cycles == q3(expected_avg)
    assert summary.adt_final == expected_adt
    assert summary.pcu_final == expected_adt * PCU_FACTORS["Car"]
    assert summary.adt_total == summary.adt_final
    assert summary.pcu_total == summary.pcu_final
    assert summary.confidence_score == Decimal("100.0")


def test_confidence_score_penalty(traffic_counts, pcu_defaults):
    survey = traffic_counts[0].traffic_survey
    TrafficQc.objects.create(
        traffic_survey=survey,
        road=survey.road,
        issue_type="Manual flag",
        issue_detail="Outlier day",
        qc_source="USER",
        resolved=False,
    )
    recompute_cycle_summaries_for_survey(survey)
    recompute_survey_summary_for_survey(survey)
    summary = TrafficSurveySummary.objects.get(traffic_survey=survey, vehicle_class="Car")
    assert summary.confidence_score == Decimal("95.0")


def test_promote_survey_to_prioritization(traffic_counts, pcu_defaults):
    survey = traffic_counts[0].traffic_survey
    survey.qa_status = "Approved"
    survey.save(update_fields=["qa_status"])
    recompute_cycle_summaries_for_survey(survey)
    recompute_survey_summary_for_survey(survey)

    existing = TrafficForPrioritization.objects.create(
        road=survey.road,
        fiscal_year=2024,
        value_type="ADT",
        final_value=Decimal("10"),
        source_survey=survey,
        is_active=True,
    )

    promoted = promote_survey_to_prioritization(survey, fiscal_year=2024, use_pcu=False)
    existing.refresh_from_db()

    summary = TrafficSurveySummary.objects.get(traffic_survey=survey, vehicle_class="Car")
    assert promoted is not None
    assert promoted.final_value == summary.adt_total
    assert promoted.is_active
    assert existing.is_active is False


def test_promote_requires_approval(traffic_counts, pcu_defaults):
    survey = traffic_counts[0].traffic_survey
    recompute_cycle_summaries_for_survey(survey)
    recompute_survey_summary_for_survey(survey)

    result = promote_survey_to_prioritization(survey, fiscal_year=2024, use_pcu=True)
    assert result is None


def test_compute_confidence_score_minimum(traffic_survey):
    for idx in range(10):
        TrafficQc.objects.create(
            traffic_survey=traffic_survey,
            road=traffic_survey.road,
            issue_type=f"Issue {idx}",
            issue_detail="detail",
            qc_source="SYSTEM",
            resolved=False,
        )
    score = compute_confidence_score_for_survey(traffic_survey)
    assert score == Decimal("60.0")
