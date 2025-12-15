from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

from traffic.forms import TrafficSurveyAdminForm
from traffic.models import TrafficSurvey

def test_admin_add_form_loads(admin_client):
    url = reverse("admin:traffic_trafficsurvey_add")
    response = admin_client.get(url)
    assert response.status_code == 200
    assert b"Survey details" in response.content


def test_admin_count_record_list_loads(admin_client):
    url = reverse("admin:traffic_trafficcountrecord_changelist")
    response = admin_client.get(url)
    assert response.status_code == 200


def test_station_location_validation_requires_both(road):
    form = TrafficSurveyAdminForm(
        data={
            "road": road.pk,
            "survey_year": 2024,
            "cycle_number": 1,
            "count_start_date": datetime.date(2024, 1, 1),
            "count_end_date": datetime.date(2024, 1, 7),
            "count_days_per_cycle": 7,
            "count_hours_per_day": 12,
            "night_adjustment_factor": Decimal("1.0"),
            "station_easting": 500000,
            # missing northing
        }
    )
    assert not form.is_valid()
    assert "station_northing" in form.errors


def test_admin_qc_resolution_action(admin_client, traffic_survey):
    change_url = reverse("admin:traffic_trafficsurvey_change", args=[traffic_survey.pk])
    response = admin_client.get(change_url)
    assert response.status_code == 200
    assert b"QC issues" in response.content or b"qc" in response.content.lower()
