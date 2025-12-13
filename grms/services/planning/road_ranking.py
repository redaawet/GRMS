"""Road ranking/prioritisation service based on SRAD Section 2.6."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple

from django.db import transaction

from grms import models
from grms.services.workplan_costs import compute_global_costs_by_road

logger = logging.getLogger(__name__)


@dataclass
class _RankingRow:
    road: models.Road
    population_served: Decimal
    benefit_factor: Decimal
    cost_of_improvement: Decimal
    road_index: Decimal


def _road_surface_group(road: models.Road) -> str:
    surface = (road.surface_type or "").lower()
    return "paved" if surface == "paved" else "unpaved"


def _decimal_or_zero(value) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


def compute_road_ranking(fiscal_year: int) -> Dict[str, Dict[str, object]]:
    """
    Compute road rankings for the provided fiscal year.

    Returns a summary dictionary keyed by surface group containing the number of
    roads processed and the sorted rows for further inspection.
    """

    cost_rows, _totals = compute_global_costs_by_road(fiscal_year)
    cost_map: Dict[int, Decimal] = {
        row["road"].id: _decimal_or_zero(row.get("total_cost")) for row in cost_rows
    }

    benefit_map: Dict[int, Decimal] = {
        bf.road_id: _decimal_or_zero(bf.total_benefit_score)
        for bf in models.BenefitFactor.objects.filter(fiscal_year=fiscal_year)
    }

    roads = models.Road.objects.select_related("socioeconomic")

    grouped_rows: Dict[str, List[_RankingRow]] = defaultdict(list)
    for road in roads:
        population = _decimal_or_zero(getattr(road.socioeconomic, "population_served", None))
        benefit_factor = benefit_map.get(road.id, Decimal("0"))
        cost_of_improvement = cost_map.get(road.id, Decimal("0"))

        if cost_of_improvement <= 0:
            road_index = Decimal("0")
            logger.warning(
                "Cost of improvement missing or non-positive for road %s; road index set to 0",
                road,
            )
        else:
            road_index = (population * benefit_factor) / cost_of_improvement

        group = _road_surface_group(road)
        grouped_rows[group].append(
            _RankingRow(
                road=road,
                population_served=population,
                benefit_factor=benefit_factor,
                cost_of_improvement=cost_of_improvement,
                road_index=road_index,
            )
        )

    summary: Dict[str, Dict[str, object]] = {}
    with transaction.atomic():
        for group, rows in grouped_rows.items():
            rows.sort(key=lambda row: (row.road_index, row.road.road_identifier), reverse=True)

            models.RoadRankingResult.objects.filter(
                fiscal_year=fiscal_year, road_class_or_surface_group=group
            ).delete()

            ranking_results = []
            top_rows: List[Tuple[int, _RankingRow]] = []
            for idx, row in enumerate(rows, start=1):
                ranking_results.append(
                    models.RoadRankingResult(
                        road=row.road,
                        fiscal_year=fiscal_year,
                        road_class_or_surface_group=group,
                        population_served=row.population_served,
                        benefit_factor=row.benefit_factor,
                        cost_of_improvement=row.cost_of_improvement,
                        road_index=row.road_index,
                        rank=idx,
                    )
                )
                if idx <= 10:
                    top_rows.append((idx, row))

            if ranking_results:
                models.RoadRankingResult.objects.bulk_create(ranking_results)

            summary[group] = {
                "processed": len(rows),
                "top": top_rows,
            }

    return summary
