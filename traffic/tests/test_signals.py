from __future__ import annotations

import datetime
from decimal import Decimal

from traffic.models import TrafficCountRecord, TrafficCycleSummary, TrafficSurvey, TrafficSurveySummary


def test_cycle_summary_created_on_count_save(traffic_survey, pcu_defaults):
    TrafficCountRecord.objects.create(
        traffic_survey=traffic_survey,
        count_date=traffic_survey.count_start_date,
        cars=5,
    )
    summary_exists = TrafficCycleSummary.objects.filter(
        traffic_survey=traffic_survey, vehicle_class="Car"
    ).exists()
    assert summary_exists


def test_survey_summary_created_on_count_save(traffic_survey, pcu_defaults):
    TrafficCountRecord.objects.create(
        traffic_survey=traffic_survey,
        count_date=traffic_survey.count_start_date,
        cars=5,
    )
    assert TrafficSurveySummary.objects.filter(traffic_survey=traffic_survey).exists()


def test_summaries_updated_when_survey_approved(traffic_counts, pcu_defaults):
    survey = traffic_counts[0].traffic_survey
    survey.qa_status = "Approved"
    survey.save(update_fields=["qa_status"])

    assert TrafficCycleSummary.objects.filter(traffic_survey=survey).count() > 0
    assert TrafficSurveySummary.objects.filter(traffic_survey=survey).count() > 0


def test_missing_days_qc_flag_created(road, night_adjustments):
    survey = TrafficSurvey.objects.create(
        road=road,
        survey_year=2024,
        cycle_number=4,
        count_start_date=datetime.date(2024, 12, 1),
        count_end_date=datetime.date(2024, 12, 7),
        count_days_per_cycle=7,
        count_hours_per_day=12,
        night_adjustment_factor=Decimal("1.33"),
        method="MOC",
        observer="QC Bot",
    )
    TrafficCountRecord.objects.create(
        traffic_survey=survey,
        count_date=survey.count_start_date,
        cars=1,
    )
    survey.refresh_from_db()
    qc_exists = survey.qc_issues.filter(issue_type="Missing days").exists()
    assert qc_exists
