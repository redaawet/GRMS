"""Computation helpers for SRAD annual workplan tables."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
import logging
from typing import Dict, Iterable, List, Tuple

from django.db.models import Prefetch

from grms import models
from grms.services import costing

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

BUCKET_FIELDS = (
    "rm_cost",
    "pm_cost",
    "rehab_cost",
    "road_bneck_cost",
    "structure_bneck_cost",
)

BUCKET_LABELS = {
    "rm_cost": "RM cost",
    "pm_cost": "PM cost",
    "rehab_cost": "Rehab cost",
    "road_bneck_cost": "Road bottleneck cost",
    "structure_bneck_cost": "Structure bottleneck cost",
}


@dataclass
class WorkplanRow:
    rd_sec_no: str | int | None
    start_km: Decimal | None
    end_km: Decimal | None
    length_km: Decimal
    surface_type: str
    surface_cond: str | None
    rm_cost: Decimal
    pm_cost: Decimal
    rehab_cost: Decimal
    road_bneck_cost: Decimal
    structure_bneck_cost: Decimal

    @property
    def year_cost(self) -> Decimal:
        return self.rm_cost + self.pm_cost + self.rehab_cost + self.road_bneck_cost + self.structure_bneck_cost


def _decimal(value) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


def _latest_mci_category_name(section: models.RoadSection) -> str | None:
    surveys = (
        models.SegmentMCIResult.objects.filter(road_segment__section=section)
        .select_related("mci_category")
        .order_by("-survey_date", "-id")
    )
    result = surveys.first()
    return getattr(getattr(result, "mci_category", None), "name", None)


def _section_surface_type(section: models.RoadSection) -> str:
    return section.surface_type or getattr(section.road, "surface_type", "") or ""


def compute_section_workplan_rows(road: models.Road, fiscal_year: int) -> Tuple[List[WorkplanRow], Dict[str, Decimal], Dict[str, object]]:
    sections = list(
        road.sections.prefetch_related(
            Prefetch("segments"),
            Prefetch("structures"),
        ).all()
    )

    rows: List[WorkplanRow] = []
    totals = defaultdict(Decimal)

    section_costs = costing.get_section_cost_breakdown(sections=sections, fiscal_year=fiscal_year)
    road_costs = costing.get_road_cost_breakdown(roads=[road], fiscal_year=fiscal_year)
    road_cost = road_costs.get(
        road.id,
        {**{field: Decimal("0") for field in BUCKET_FIELDS}, "year_cost": Decimal("0")},
    )

    section_total_cost = sum(costs.get("year_cost", Decimal("0")) for costs in section_costs.values())
    if section_total_cost == 0 and road_cost.get("year_cost", Decimal("0")) > 0:
        total_length = sum(_decimal(section.length_km) for section in sections) or Decimal("0")
        for section in sections:
            fraction = (_decimal(section.length_km) / total_length) if total_length else Decimal("0")
            buckets = section_costs.setdefault(section.id, {field: Decimal("0") for field in BUCKET_FIELDS})
            for field in BUCKET_FIELDS:
                buckets[field] = (road_cost.get(field, Decimal("0")) * fraction).quantize(Decimal("0.01"))
            buckets["year_cost"] = sum(buckets[field] for field in BUCKET_FIELDS)

    for section in sections:
        buckets = section_costs.get(section.id, {field: Decimal("0") for field in BUCKET_FIELDS})
        length_km = _decimal(section.length_km)
        surface_cond = _latest_mci_category_name(section)

        row = WorkplanRow(
            rd_sec_no=section.section_number,
            start_km=_decimal(section.start_chainage_km),
            end_km=_decimal(section.end_chainage_km),
            length_km=length_km,
            surface_type=_section_surface_type(section),
            surface_cond=surface_cond,
            rm_cost=buckets.get("rm_cost", Decimal("0")),
            pm_cost=buckets.get("pm_cost", Decimal("0")),
            rehab_cost=buckets.get("rehab_cost", Decimal("0")),
            road_bneck_cost=buckets.get("road_bneck_cost", Decimal("0")),
            structure_bneck_cost=buckets.get("structure_bneck_cost", Decimal("0")),
        )
        rows.append(row)

        totals["length_km"] += length_km
        for field in BUCKET_FIELDS:
            totals[field] += row.__dict__[field]
        totals["year_cost"] += row.year_cost

    ranking = (
        models.RoadRankingResult.objects.filter(road=road, fiscal_year=fiscal_year)
        .order_by("rank")
        .first()
    )

    road_link_type = getattr(getattr(road, "socioeconomic", None), "road_link_type", None)
    header_context = {
        "road_class": road_link_type or getattr(road, "surface_type", ""),
        "road_name": getattr(road, "road_name_from", ""),
        "rank_no": ranking.rank if ranking else None,
    }

    return rows, totals, header_context


def compute_annual_workplan_rows(
    fiscal_year: int,
    group: str | None = None,
    *,
    budget_cap_birr: Decimal | None = None,
    include_partial_last_road: bool = True,
) -> Tuple[List[Dict[str, object]], Dict[str, Decimal], Dict[str, object]]:
    ranking_qs = models.RoadRankingResult.objects.filter(fiscal_year=fiscal_year)
    if group:
        ranking_qs = ranking_qs.filter(road_class_or_surface_group=group)

    rankings = list(ranking_qs.select_related("road").order_by("rank"))
    roads = [ranking.road for ranking in rankings]
    cost_map = costing.get_road_cost_breakdown(roads=roads, fiscal_year=fiscal_year, group=group)

    rows: List[Dict[str, object]] = []
    totals = defaultdict(Decimal)

    for ranking in rankings:
        road = ranking.road
        road_link_type = getattr(getattr(road, "socioeconomic", None), "road_link_type", None)
        costs = cost_map.get(
            road.id,
            {**{field: Decimal("0") for field in BUCKET_FIELDS}, "year_cost": Decimal("0")},
        )
        row_total = {
            "road": road,
            "road_no": road.road_identifier,
            "road_class": road_link_type or getattr(road, "surface_type", ""),
            "road_length_km": _decimal(getattr(road, "total_length_km", None)),
            "rank": ranking.rank,
            **{field: costs.get(field, Decimal("0")) for field in BUCKET_FIELDS},
        }
        row_total["year_cost"] = costs.get("year_cost", sum(row_total[key] for key in BUCKET_FIELDS))

        rows.append(row_total)

    rows.sort(key=lambda entry: entry.get("rank", 0) or 0)

    funded_rows: List[Dict[str, object]] = []
    remaining_budget = Decimal(budget_cap_birr) if budget_cap_birr else None

    for row_total in rows:
        road_cost = row_total["year_cost"]
        selection_factor = Decimal("0")
        funding_status = "NO COST DATA" if road_cost <= 0 else "FULL"

        totals["planned_year_cost"] += road_cost

        if remaining_budget is None:
            selection_factor = Decimal("1") if road_cost > 0 else Decimal("0")
        else:
            if road_cost <= 0:
                selection_factor = Decimal("0")
            elif road_cost <= remaining_budget:
                selection_factor = Decimal("1")
                remaining_budget -= road_cost
            elif include_partial_last_road and remaining_budget > 0:
                selection_factor = remaining_budget / road_cost
                funding_status = "PARTIAL"
                remaining_budget = Decimal("0")
            else:
                funding_status = "NOT FUNDED"

        if funding_status == "NOT FUNDED" and include_partial_last_road is False and remaining_budget is not None:
            # Stop iteration when budget is exhausted without partial funding
            break

        funded_row = dict(row_total)
        funded_row["funding_status"] = funding_status
        funded_row["funded_percent"] = (selection_factor * Decimal(100)).quantize(Decimal("0.01"))
        funded_amount = Decimal("0")
        totals["road_length_km"] += row_total.get("road_length_km", Decimal("0"))
        for field in BUCKET_FIELDS:
            funded_value = (row_total[field] * selection_factor).quantize(Decimal("0.01"))
            funded_row[f"funded_{field}"] = funded_value
            funded_amount += funded_value
            totals[field] += funded_value
        funded_row["funded_amount"] = funded_amount
        totals["year_cost"] += funded_amount
        funded_row["year_cost"] = row_total["year_cost"]
        funded_row["unfunded_amount"] = row_total["year_cost"] - funded_amount
        funded_rows.append(funded_row)

        if remaining_budget is not None and remaining_budget <= 0:
            break

    rows = funded_rows if funded_rows else rows

    first_ranking = rankings[0] if rankings else None
    header_context = {
        "annual_work_plan_FY": fiscal_year,
        "region_name": getattr(
            getattr(getattr(first_ranking, "road", None), "admin_zone", None), "name", ""
        ),
        "debug_counts": {},
        "remaining_budget": remaining_budget if budget_cap_birr is not None else None,
    }

    return rows, totals, header_context
