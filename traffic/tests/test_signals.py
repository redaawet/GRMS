from __future__ import annotations

import pytest

from traffic.models import (
    TrafficCountRecord,
    TrafficCycleSummary,
    TrafficSurvey,
    TrafficSurveySummary,
)
from traffic.tests.fixtures import pcu_defaults, traffic_counts

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


def test_missing_days_qc_flag_created(traffic_survey, pcu_defaults):
    TrafficCountRecord.objects.create(
        traffic_survey=traffic_survey,
        count_date=traffic_survey.count_start_date,
        cars=1,
    )
    survey = TrafficSurvey.objects.get(pk=traffic_survey.pk)
    qc_exists = survey.qc_issues.filter(issue_type="Missing days").exists()
    assert qc_exists
