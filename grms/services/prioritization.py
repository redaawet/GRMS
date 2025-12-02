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


def map_indicator_to_score(criterion: models.BenefitCriterion, value) -> Decimal:
    """Resolve a criterion score using the configured scale rows.

    Args:
        criterion: Benefit criterion definition.
        value: Numeric measurement or categorical code.

    Returns:
        Score defined in :class:`BenefitCriterionScale` or ``0`` when no match is
        found or the value is empty.
    """

    if value is None:
        return Decimal("0")

    # Handle categorical matching first.
    if isinstance(value, str):
        code = value.strip().lower()
        for scale in criterion.scales.all():
            if scale.exact_match_code and scale.exact_match_code.lower() == code:
                return Decimal(scale.score)
        return Decimal("0")

    try:
        numeric_value = Decimal(str(value))
    except Exception:
        return Decimal("0")

    for scale in criterion.scales.all():
        if scale.exact_match_code:
            continue
        min_ok = scale.min_value is None or numeric_value >= scale.min_value
        max_ok = scale.max_value is None or numeric_value <= scale.max_value
        if min_ok and max_ok:
            return Decimal(scale.score)

    return Decimal("0")


def _lookup_adt(road: models.Road, fiscal_year: int) -> Decimal:
    fallback = models.TrafficForPrioritization.objects.filter(
        road=road, fiscal_year=fiscal_year, value_type="ADT"
    ).order_by("-prepared_at").values_list("value", flat=True).first()
    if fallback is None:
        return Decimal("0")
    return Decimal(fallback)


def _population_served(road: models.Road, socioeconomic: models.RoadSocioEconomic) -> int:
    if socioeconomic.population_served_override is not None:
        return socioeconomic.population_served_override
    return socioeconomic.road.population_served or 0


def _criterion_inputs(
    road: models.Road, socioeconomic: models.RoadSocioEconomic, fiscal_year: int
) -> Dict[str, object]:
    link_type = socioeconomic.link_type_override or road.link_type
    adt_value = socioeconomic.adt_value if socioeconomic.adt_value is not None else _lookup_adt(road, fiscal_year)
    return {
        "BF1_ADT": adt_value,
        "BF1_TRADING": socioeconomic.trading_centers_count,
        "BF1_VILLAGES": socioeconomic.villages_connected_count,
        "BF1_LINKTYPE": link_type.code if link_type else None,
        "BF2_FARMLAND": socioeconomic.farmland_percentage,
        "BF2_COOPS": socioeconomic.cooperative_centers_count,
        "BF2_MARKETS": socioeconomic.markets_connected_count,
        "BF3_HEALTH": socioeconomic.health_centers_count,
        "BF3_EDU": socioeconomic.educational_institutions_count,
        "BF3_DEVPROJ": socioeconomic.development_projects_count,
    }


def compute_benefit_factors_for_road(
    road: models.Road, fiscal_year: int
) -> Optional[models.BenefitFactor]:
    """Compute benefit factor scores for a road and fiscal year.

    Socio-economic inputs and lookup tables drive all scoring. The function
    updates or creates :class:`BenefitFactor` records but does not expose the
    values via road fields.
    """

    socioeconomic = (
        models.RoadSocioEconomic.objects.select_related("road", "link_type_override")
        .filter(road=road, fiscal_year=fiscal_year)
        .first()
    )
    if socioeconomic is None:
        return None

    inputs = _criterion_inputs(road, socioeconomic, fiscal_year)
    category_totals: Dict[str, Decimal] = {}
    category_weights: Dict[str, Decimal] = {}

    for criterion in models.BenefitCriterion.objects.select_related("category"):
        raw_value = inputs.get(criterion.code)
        score = map_indicator_to_score(criterion, raw_value)
        weighted_score = score * Decimal(criterion.indicator_weight)
        code = criterion.category.code
        category_totals[code] = category_totals.get(code, Decimal("0")) + weighted_score
        category_weights.setdefault(code, Decimal(criterion.category.weight))

    weighted_categories: Dict[str, Decimal] = {}
    for code, subtotal in category_totals.items():
        weight = category_weights.get(code, Decimal("0"))
        weighted_categories[code] = subtotal * weight

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


def compute_prioritization_for_year(fiscal_year: int) -> Iterable[models.PrioritizationResult]:
    """Compute prioritization rankings for all roads with socio-economic data."""

    candidates = (
        models.Road.objects.filter(socioeconomic_inputs__fiscal_year=fiscal_year)
        .select_related("admin_zone", "admin_woreda")
        .distinct()
    )

    scoring: list[Tuple[models.Road, Decimal, int, Decimal, Decimal]] = []
    for road in candidates:
        benefit = compute_benefit_factors_for_road(road, fiscal_year)
        if benefit is None or benefit.total_benefit_score is None:
            continue

        socioeconomic = models.RoadSocioEconomic.objects.filter(road=road, fiscal_year=fiscal_year).first()
        if socioeconomic is None:
            continue

        population = _population_served(road, socioeconomic)
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
