"""Read-only helpers for traffic values sourced from the traffic app."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.db.models import QuerySet

from grms import models


def _value_from_prioritization(record) -> Optional[Decimal]:
    if record is None:
        return None
    value = record.final_value if record.final_value is not None else record.value
    return Decimal(value) if value is not None else None


def get_traffic_value(
    road: models.Road,
    fiscal_year: Optional[int],
    value_type: str = "ADT",
) -> Optional[Decimal]:
    """Return the preferred traffic value for a road/fiscal year."""

    from traffic.models import TrafficForPrioritization, TrafficSurveyOverall, TrafficSurveySummary

    prioritization_qs: QuerySet[TrafficForPrioritization] = TrafficForPrioritization.objects.filter(
        road=road,
        value_type=value_type,
        is_active=True,
    )
    if fiscal_year is not None:
        prioritization_qs = prioritization_qs.filter(fiscal_year=fiscal_year)

    prioritization = prioritization_qs.order_by("-fiscal_year", "-prepared_at", "-prep_id").first()
    prioritization_value = _value_from_prioritization(prioritization)
    if prioritization_value is not None:
        return prioritization_value

    overall_qs = TrafficSurveyOverall.objects.filter(road=road)
    if fiscal_year is not None:
        overall_qs = overall_qs.filter(fiscal_year=fiscal_year)
    overall = overall_qs.order_by("-computed_at", "-overall_id").first()
    if overall is not None:
        return Decimal(overall.adt_total if value_type == "ADT" else overall.pcu_total)

    summary_qs = TrafficSurveySummary.objects.filter(road=road)
    if fiscal_year is not None:
        summary_qs = summary_qs.filter(fiscal_year=fiscal_year)
    summary = summary_qs.order_by("-computed_at", "-survey_summary_id").first()
    if summary is not None:
        return Decimal(summary.adt_total if value_type == "ADT" else summary.pcu_total)

    return None
