"""Prioritization scoring logic aligned with SRAD specification."""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Optional, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from grms import models
from traffic import models as traffic_models


def _resolve_range_score(criterion: models.BenefitCriterion, value) -> Decimal:
    """Find the score for a criterion using range-based lookup rows."""

    if value is None:
        raise ValidationError({criterion.code: "Value is required for scoring."})

    try:
        numeric_value = Decimal(str(value))
    except Exception:
        raise ValidationError({criterion.code: "Value must be numeric."})

    for scale in criterion.scales.all():
        min_ok = scale.min_value is None or numeric_value >= scale.min_value
        max_ok = scale.max_value is None or numeric_value <= scale.max_value
        if min_ok and max_ok:
            return Decimal(scale.score)

    raise ValidationError({criterion.code: "Value does not match any scoring range."})


def get_final_adt(road: models.Road) -> Decimal:
    """Apply the mandatory ADT selection rule."""

    computed = traffic_models.TrafficSurveySummary.latest_for(road)
    if computed:
        return Decimal(computed.adt_total)

    socioeconomic = models.RoadSocioEconomic.objects.get(road=road)
    if socioeconomic.adt_override:
        return Decimal(socioeconomic.adt_override)

    raise ValidationError("ADT missing: no survey & no override.")


def _criterion_inputs(road: models.Road, socioeconomic: models.RoadSocioEconomic) -> Dict[str, object]:
    link_type = socioeconomic.road_link_type
    return {
        "TRAFFIC": get_final_adt(road),
        "TRADE_CTR": socioeconomic.trading_centers,
        "VILLAGES": socioeconomic.villages,
        "LINK_TYPE": link_type.score if link_type else None,
        "FARMLAND": socioeconomic.farmland_percent,
        "COOPS": socioeconomic.cooperative_centers,
        "MARKETS": socioeconomic.markets,
        "HEALTH": socioeconomic.health_centers,
        "EDUCATION": socioeconomic.education_centers,
        "PROJECTS": socioeconomic.development_projects,
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

    socioeconomic.full_clean(exclude=["road"])

    inputs = _criterion_inputs(road, socioeconomic)
    category_scores: Dict[str, Decimal] = {"BF1": Decimal("0"), "BF2": Decimal("0"), "BF3": Decimal("0")}

    criteria = models.BenefitCriterion.objects.select_related("category").prefetch_related("scales")
    caps = {cat.code: Decimal(cat.weight) * Decimal("100") for cat in models.BenefitCategory.objects.all()}
    for criterion in criteria:
        raw_input = inputs.get(criterion.code)
        if criterion.scoring_method == models.BenefitCriterion.ScoringMethod.LOOKUP:
            if raw_input is None:
                raise ValidationError({criterion.code: "Lookup value is required."})
            score = Decimal(raw_input)
        else:
            score = _resolve_range_score(criterion, raw_input)

        weighted = score * Decimal(criterion.weight)
        category_scores[criterion.category.code] += weighted

    bf1 = min(category_scores.get("BF1", Decimal("0")), caps.get("BF1", Decimal("40")))
    bf2 = min(category_scores.get("BF2", Decimal("0")), caps.get("BF2", Decimal("30")))
    bf3 = min(category_scores.get("BF3", Decimal("0")), caps.get("BF3", Decimal("30")))
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

        population = road.socioeconomic.population_served
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
