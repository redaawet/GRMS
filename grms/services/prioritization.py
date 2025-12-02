"""Prioritization helpers for computing benefit factors and rankings.

This module keeps scoring logic configurable via lookup models and avoids
hard-coded thresholds in application code.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Optional, Tuple

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from grms import models


def resolve_score(criterion: models.BenefitCriterion, value) -> Decimal:
    """Find the score for a criterion using range-based lookup rows."""

    if value is None:
        return Decimal("0")

    try:
        numeric_value = Decimal(str(value))
    except Exception:
        return Decimal("0")

    for scale in criterion.scales.all():
        min_ok = scale.min_value is None or numeric_value >= scale.min_value
        max_ok = scale.max_value is None or numeric_value <= scale.max_value
        if min_ok and max_ok:
            return Decimal(scale.score)

    return Decimal("0")


def get_final_adt(road: models.Road, fiscal_year: int) -> Decimal:
    """Apply the mandatory ADT selection rule."""

    survey_adt = (
        models.TrafficForPrioritization.objects.filter(
            road=road,
            fiscal_year=fiscal_year,
            value_type="ADT",
            road_segment__isnull=True,
        )
        .order_by("-prepared_at")
        .first()
    )

    if survey_adt:
        return Decimal(survey_adt.value)

    socio = models.RoadSocioEconomic.objects.filter(road=road).first()
    return Decimal(socio.adt_override) if socio and socio.adt_override is not None else Decimal("0")


def _criterion_inputs(
    road: models.Road, socioeconomic: models.RoadSocioEconomic, fiscal_year: int
) -> Dict[str, object]:
    link_type = socioeconomic.road_link_type or road.link_type
    return {
        "ADT": get_final_adt(road, fiscal_year),
        "TC": socioeconomic.trading_centers,
        "VC": socioeconomic.villages_connected,
        "LT": link_type.score if link_type else None,
        "FARMLAND": socioeconomic.farmland_percentage,
        "COOP": socioeconomic.cooperative_centers,
        "MARKET": socioeconomic.markets_connected,
        "HEALTH": socioeconomic.health_centers,
        "EDU": socioeconomic.education_centers,
        "DEV": socioeconomic.development_projects,
    }


def compute_benefit_factor(
    road: models.Road, fiscal_year: int
) -> Optional[models.BenefitFactor]:
    """Compute benefit factor scores using socio-economic inputs and lookups."""

    socioeconomic = models.RoadSocioEconomic.objects.select_related(
        "road_link_type", "road"
    ).filter(road=road).first()
    if socioeconomic is None:
        return None

    inputs = _criterion_inputs(road, socioeconomic, fiscal_year)
    category_totals: Dict[str, Decimal] = {}

    for criterion in models.BenefitCriterion.objects.select_related("category"):
        raw_value = inputs.get(criterion.code.upper())
        score = resolve_score(criterion, raw_value)
        weighted_score = score * Decimal(criterion.weight)
        category_code = criterion.category.code
        category_totals[category_code] = category_totals.get(category_code, Decimal("0")) + weighted_score

    weighted_categories: Dict[str, Decimal] = {}
    for category in models.BenefitCategory.objects.all():
        subtotal = category_totals.get(category.code, Decimal("0"))
        weighted_categories[category.code] = subtotal * Decimal(category.weight)

    bf1 = weighted_categories.get("BF1", Decimal("0"))
    bf2 = weighted_categories.get("BF2", Decimal("0"))
    bf3 = weighted_categories.get("BF3", Decimal("0"))
    total = bf1 + bf2 + bf3

    benefit_factor, _ = models.BenefitFactor.objects.update_or_create(
        road=road,
        fiscal_year=fiscal_year,
        defaults={
            "bf1_transport_score": bf1,
            "bf2_agriculture_score": bf2,
            "bf3_social_score": bf3,
            "total_benefit_score": total,
            "calculated_at": timezone.now(),
        },
    )
    return benefit_factor


def _derive_improvement_cost(road: models.Road, fiscal_year: int) -> Optional[Decimal]:
    """Estimate improvement cost from planned interventions or AWP budgets."""

    awp_total = models.AnnualWorkPlan.objects.filter(road=road, fiscal_year=fiscal_year).aggregate(
        total=Sum("total_budget")
    )["total"]
    section_total = (
        models.RoadSectionIntervention.objects.filter(
            section__road=road, intervention_year=fiscal_year
        ).aggregate(total=Sum("estimated_cost"))["total"]
    )

    if awp_total is not None:
        return Decimal(awp_total)
    if section_total is not None:
        return Decimal(section_total)
    return None


def compute_prioritization_result(fiscal_year: int) -> Iterable[models.PrioritizationResult]:
    """Compute prioritization rankings for all roads with socio-economic data."""

    candidates = models.Road.objects.filter(socioeconomic__isnull=False).select_related(
        "admin_zone", "admin_woreda"
    )

    scoring: list[Tuple[models.Road, Decimal, int, Decimal, Decimal]] = []
    for road in candidates:
        benefit = compute_benefit_factor(road, fiscal_year)
        if benefit is None or benefit.total_benefit_score is None:
            continue

        population = road.population_served or 0
        improvement_cost = _derive_improvement_cost(road, fiscal_year)
        if improvement_cost is None or improvement_cost == 0:
            continue

        ranking_index = (Decimal(population) * Decimal(benefit.total_benefit_score)) / Decimal(improvement_cost)
        scoring.append((road, ranking_index, population, Decimal(improvement_cost), Decimal(benefit.total_benefit_score)))

    scoring.sort(key=lambda row: row[1], reverse=True)

    results: list[models.PrioritizationResult] = []
    with transaction.atomic():
        for idx, (road, ranking_index, population, improvement_cost, benefit_score) in enumerate(scoring, start=1):
            result, _ = models.PrioritizationResult.objects.update_or_create(
                road=road,
                section=None,
                fiscal_year=fiscal_year,
                defaults={
                    "population_served": population,
                    "benefit_score": benefit_score,
                    "improvement_cost": improvement_cost,
                    "ranking_index": ranking_index,
                    "priority_rank": idx,
                },
            )
            results.append(result)

    return results


# Backwards compatibility for existing callers
def compute_prioritization_for_year(fiscal_year: int) -> Iterable[models.PrioritizationResult]:
    return compute_prioritization_result(fiscal_year)
