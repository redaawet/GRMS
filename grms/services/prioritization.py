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


def resolve_score(criterion: models.BenefitCriterion, value) -> Decimal:
    """Find the score for a criterion using range-based lookup rows."""

    if value is None:
        raise ValidationError({criterion.name: "Value is required for scoring."})

    try:
        numeric_value = Decimal(str(value))
    except Exception:
        raise ValidationError({criterion.name: "Value must be numeric."})

    for scale in criterion.scales.all():
        min_ok = numeric_value >= scale.min_value
        max_ok = scale.max_value is None or numeric_value <= scale.max_value
        if min_ok and max_ok:
            return Decimal(scale.score)

    raise ValidationError({criterion.name: "Value does not match any scoring range."})


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
        "ADT": get_final_adt(road),
        "Trading Centers": socioeconomic.trading_centers,
        "Villages": socioeconomic.villages,
        "Road Link Type": link_type.score,
        "Farmland %": socioeconomic.farmland_percent,
        "Cooperative Centers": socioeconomic.cooperative_centers,
        "Markets": socioeconomic.markets,
        "Health Centers": socioeconomic.health_centers,
        "Education Centers": socioeconomic.education_centers,
        "Development Projects": socioeconomic.development_projects,
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

    criteria = models.BenefitCriterion.objects.select_related("category")
    for criterion in criteria:
        if criterion.name == "Road Link Type":
            score = Decimal(inputs["Road Link Type"])
        else:
            score = resolve_score(criterion, inputs[criterion.name])

        category_scores[criterion.category.name] += score

    bf1 = category_scores.get("BF1", Decimal("0"))
    bf2 = category_scores.get("BF2", Decimal("0"))
    bf3 = category_scores.get("BF3", Decimal("0"))
    total = (bf1 * Decimal("0.40")) + (bf2 * Decimal("0.30")) + (bf3 * Decimal("0.30"))

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
