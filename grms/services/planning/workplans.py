"""Computation helpers for SRAD annual workplan tables."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Tuple

from django.db.models import Prefetch

from grms import models
from grms.services import workplan_costs
from grms.utils import geometry_length_km, geos_length_km

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


def segment_length_km(segment: models.RoadSegment) -> Decimal:
    length = getattr(segment, "length_km", None)
    if length:
        return _decimal(length)

    if segment.station_from_km is not None and segment.station_to_km is not None:
        return _decimal(segment.station_to_km - segment.station_from_km)

    geometry = getattr(segment, "geometry", None)
    return _decimal(geometry_length_km(geometry) if geometry else 0)


def _structure_length_m(structure: models.StructureInventory) -> Decimal | None:
    bridge_detail = getattr(structure, "bridgedetail", None)
    if bridge_detail and bridge_detail.length_m:
        return _decimal(bridge_detail.length_m)

    culvert_detail = getattr(structure, "culvertdetail", None)
    if culvert_detail and culvert_detail.span_m:
        return _decimal(culvert_detail.span_m)

    if structure.start_chainage_km is not None and structure.end_chainage_km is not None:
        return _decimal(structure.end_chainage_km - structure.start_chainage_km) * Decimal(1000)

    line_geom = getattr(structure, "location_line", None)
    if line_geom:
        return _decimal(geos_length_km(line_geom) * 1000)

    return None


def structure_quantity(structure: models.StructureInventory, work_item: models.InterventionWorkItem) -> Decimal:
    quantity_m = _structure_length_m(structure)
    if quantity_m is None:
        return Decimal(1)
    unit_normalized = (getattr(work_item, "unit", "") or "").lower()

    if unit_normalized == "km":
        return quantity_m / Decimal(1000)
    if unit_normalized == "m":
        return quantity_m
    return quantity_m


def _bucket_for_work_code(work_code: str | None) -> str | None:
    if work_code == "01":
        return "rm_cost"
    if work_code == "02":
        return "pm_cost"
    if work_code == "05":
        return "rehab_cost"
    if work_code in {"101", "102"}:
        return "road_bneck_cost"
    return None


def _latest_mci_category_name(section: models.RoadSection) -> str | None:
    surveys = (
        models.SegmentMCIResult.objects.filter(road_segment__section=section)
        .select_related("mci_category")
        .order_by("-survey_date", "-id")
    )
    result = surveys.first()
    return getattr(getattr(result, "mci_category", None), "name", None)


def _ensure_bucket_default() -> Dict[str, Decimal]:
    return {field: Decimal("0") for field in BUCKET_FIELDS}


def _apply_segment_needs(section: models.RoadSection, fiscal_year: int, buckets: Dict[str, Decimal]):
    segment_items = (
        models.SegmentInterventionNeedItem.objects.filter(
            need__fiscal_year=fiscal_year, need__segment__section=section
        )
        .select_related("need__segment", "intervention_item")
        .all()
    )

    for item in segment_items:
        segment = item.need.segment
        length_km = segment_length_km(segment)
        unit_cost = _decimal(getattr(item.intervention_item, "unit_cost", None))
        bucket = _bucket_for_work_code(getattr(item.intervention_item, "work_code", ""))
        if bucket:
            buckets[bucket] += unit_cost * length_km


def _apply_structure_needs(section: models.RoadSection, fiscal_year: int, buckets: Dict[str, Decimal]):
    structure_items = (
        models.StructureInterventionNeedItem.objects.filter(
            need__fiscal_year=fiscal_year, need__structure__section=section
        )
        .select_related("need__structure", "intervention_item")
        .all()
    )

    for item in structure_items:
        structure = item.need.structure
        unit_cost = _decimal(getattr(item.intervention_item, "unit_cost", None))
        quantity = structure_quantity(structure, item.intervention_item)
        buckets["structure_bneck_cost"] += unit_cost * quantity


def _section_surface_type(section: models.RoadSection) -> str:
    return section.surface_type or getattr(section.road, "surface_type", "") or ""


def compute_section_workplan_rows(road: models.Road, fiscal_year: int) -> Tuple[List[WorkplanRow], Dict[str, Decimal], Dict[str, object]]:
    sections = road.sections.prefetch_related(
        Prefetch("segments"),
        Prefetch("structures"),
    ).all()

    rows: List[WorkplanRow] = []
    totals = defaultdict(Decimal)

    for section in sections:
        buckets = _ensure_bucket_default()
        _apply_segment_needs(section, fiscal_year, buckets)
        _apply_structure_needs(section, fiscal_year, buckets)

        length_km = _decimal(section.length_km)
        surface_cond = _latest_mci_category_name(section)

        row = WorkplanRow(
            rd_sec_no=section.section_number,
            start_km=_decimal(section.start_chainage_km),
            end_km=_decimal(section.end_chainage_km),
            length_km=length_km,
            surface_type=_section_surface_type(section),
            surface_cond=surface_cond,
            rm_cost=buckets["rm_cost"],
            pm_cost=buckets["pm_cost"],
            rehab_cost=buckets["rehab_cost"],
            road_bneck_cost=buckets["road_bneck_cost"],
            structure_bneck_cost=buckets["structure_bneck_cost"],
        )
        rows.append(row)

        totals["length_km"] += length_km
        for field in BUCKET_FIELDS:
            totals[field] += buckets[field]
        totals["year_cost"] += row.year_cost

    ranking = (
        models.RoadRankingResult.objects.filter(road=road, fiscal_year=fiscal_year)
        .order_by("rank")
        .first()
    )

    road_link_type = getattr(getattr(road, "socioeconomic", None), "road_link_type", None)
    header_context = {
        "woreda_name": getattr(getattr(road, "admin_woreda", None), "name", ""),
        "road_class": road_link_type or getattr(road, "surface_type", ""),
        "road_name": getattr(road, "road_name_from", ""),
        "rank_no": ranking.rank if ranking else None,
    }

    return rows, totals, header_context


def compute_annual_workplan_rows(
    fiscal_year: int, group: str | None = None
) -> Tuple[List[Dict[str, object]], Dict[str, Decimal], Dict[str, object]]:
    ranking_qs = models.RoadRankingResult.objects.filter(fiscal_year=fiscal_year)
    if group:
        ranking_qs = ranking_qs.filter(road_class_or_surface_group=group)

    rankings = list(ranking_qs.select_related("road").order_by("rank"))
    rows: List[Dict[str, object]] = []
    totals = defaultdict(Decimal)

    cost_rows, _cost_totals, debug_counts = workplan_costs.compute_global_costs_by_road(
        include_debug=True
    )
    cost_map = {row["road"].id: row for row in cost_rows}
    debug_counts["cost_map_roads"] = len(cost_map)

    for ranking in rankings:
        road = ranking.road
        cost_row = cost_map.get(road.id)
        if not cost_row:
            continue

        road_link_type = getattr(getattr(road, "socioeconomic", None), "road_link_type", None)
        row_total = {
            "road": road,
            "road_no": road.road_identifier,
            "road_class": road_link_type or getattr(road, "surface_type", ""),
            "road_length_km": cost_row.get("road_length_km", Decimal("0")),
            "rank": ranking.rank,
            "rm_cost": cost_row.get("rm_cost", Decimal("0")),
            "pm_cost": cost_row.get("pm_cost", Decimal("0")),
            "rehab_cost": cost_row.get("rehab_cost", Decimal("0")),
            "road_bneck_cost": cost_row.get("road_bneck_cost", Decimal("0")),
            "structure_bneck_cost": cost_row.get("structure_bneck_cost", Decimal("0")),
        }
        row_total["year_cost"] = cost_row.get(
            "total_cost", sum(row_total[key] for key in BUCKET_FIELDS)
        )

        rows.append(row_total)
        for field in ("road_length_km", *BUCKET_FIELDS, "year_cost"):
            totals[field] += row_total[field]

    rows.sort(key=lambda entry: entry.get("rank", 0) or 0)

    first_ranking = rankings[0] if rankings else None
    header_context = {
        "annual_work_plan_FY": fiscal_year,
        "region_name": getattr(
            getattr(getattr(first_ranking, "road", None), "admin_zone", None), "name", ""
        ),
        "woreda_name": getattr(
            getattr(getattr(first_ranking, "road", None), "admin_woreda", None), "name", ""
        ),
        "debug_counts": debug_counts,
    }

    return rows, totals, header_context
