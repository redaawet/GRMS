"""Costing helpers shared by workplan and ranking reports."""
from __future__ import annotations

from decimal import Decimal
import logging
from typing import Dict, Iterable, Sequence

from django.conf import settings

from grms import models
from grms.services.workplan_costs import compute_global_costs_by_road
from grms.utils import geometry_length_km, geos_length_km

logger = logging.getLogger(__name__)


BUCKET_FIELDS = (
    "rm_cost",
    "pm_cost",
    "rehab_cost",
    "road_bneck_cost",
    "structure_bneck_cost",
)


def _decimal(value) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


def _segment_length_km(segment: models.RoadSegment) -> Decimal:
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


def _structure_quantity(structure: models.StructureInventory, unit: str | None) -> Decimal:
    quantity_m = _structure_length_m(structure)
    if quantity_m is None:
        return Decimal(1)

    unit_normalized = (unit or "").lower()
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
    if work_code:
        if work_code.startswith("10"):
            return "structure_bneck_cost"
    return None


def _bucket_for_section_intervention(intervention: models.RoadSectionIntervention) -> str | None:
    code = (intervention.intervention.intervention_code or "").lower()
    category = (intervention.intervention.category or "").lower()

    explicit_map = {
        "rm": "rm_cost",
        "pm": "pm_cost",
        "rehab": "rehab_cost",
        "rb": "road_bneck_cost",
        "sb": "structure_bneck_cost",
    }

    for prefix, bucket in explicit_map.items():
        if code.startswith(prefix):
            return bucket

    if category == "structure":
        return "structure_bneck_cost"
    if category == "bottleneck":
        return "road_bneck_cost"

    _log_missing("Unable to map section intervention to SRAD bucket", intervention_id=intervention.id)
    return None


def _road_surface_group(road: models.Road) -> str:
    surface = (road.surface_type or "").lower()
    return "paved" if surface == "paved" else "unpaved"


def get_road_cost_breakdown(*, roads: Iterable[models.Road], fiscal_year: int, group: str | None = None, region: str | None = None) -> Dict[int, Dict[str, Decimal]]:
    """Return SRAD bucket totals by road using the Global Cost logic."""

    global_rows, _totals = compute_global_costs_by_road(fy=fiscal_year)
    cost_map: Dict[int, Dict[str, Decimal]] = {}
    road_filter_ids = {road.id for road in roads}

    for row in global_rows:
        road = row["road"]
        if road.id not in road_filter_ids:
            continue

        if group and _road_surface_group(road) != group:
            continue

        if region and getattr(getattr(road, "admin_zone", None), "region", None) != region:
            continue

        cost_map[road.id] = {
            "rm_cost": _decimal(row.get("rm_cost")),
            "pm_cost": _decimal(row.get("pm_cost")),
            "rehab_cost": _decimal(row.get("rehab_cost")),
            "road_bneck_cost": _decimal(row.get("road_bneck_cost")),
            "structure_bneck_cost": _decimal(row.get("structure_bneck_cost")),
            "year_cost": _decimal(row.get("total_cost")),
        }

    for road in roads:
        cached = cost_map.get(road.id)
        if cached and cached.get("year_cost", Decimal("0")) > 0:
            continue
        sections = list(road.sections.all())
        section_costs = get_section_cost_breakdown(sections=sections, fiscal_year=fiscal_year)
        aggregated = {field: sum(costs.get(field, Decimal("0")) for costs in section_costs.values()) for field in BUCKET_FIELDS}
        year_cost = sum(aggregated.values())
        if year_cost > 0:
            aggregated["year_cost"] = year_cost
            cost_map[road.id] = aggregated

    return cost_map


def _default_bucket_map() -> Dict[str, Decimal]:
    return {field: Decimal("0") for field in BUCKET_FIELDS}


def _log_missing(message: str, **context):
    if settings.DEBUG:
        logger.warning(message, extra={"context": context})


def get_section_cost_breakdown(
    *,
    sections: Sequence[models.RoadSection] | Iterable[models.RoadSection],
    fiscal_year: int,
    group: str | None = None,
) -> Dict[int, Dict[str, Decimal]]:
    """Return SRAD bucket totals by section using intervention recommendations."""

    section_list = list(sections)
    section_ids = [section.id for section in section_list if section.id]
    result: Dict[int, Dict[str, Decimal]] = {sid: _default_bucket_map() for sid in section_ids}

    if group:
        allowed_ids = []
        for section in section_list:
            if not section.id:
                continue
            if _road_surface_group(section.road) == group:
                allowed_ids.append(section.id)
        section_ids = allowed_ids

    segments = models.RoadSegment.objects.filter(section_id__in=section_ids).select_related("section__road")
    segment_map = {segment.id: segment for segment in segments}

    segment_recs = models.SegmentInterventionRecommendation.objects.select_related("segment__section__road", "recommended_item").filter(segment_id__in=segment_map.keys())
    for rec in segment_recs:
        segment = segment_map.get(rec.segment_id)
        if segment is None:
            continue
        bucket = _bucket_for_work_code(getattr(rec.recommended_item, "work_code", None))
        unit_cost = getattr(rec.recommended_item, "unit_cost", None)
        if not bucket:
            _log_missing("Missing SRAD bucket for segment recommendation", segment_id=segment.id)
            continue
        if unit_cost is None:
            _log_missing("Missing unit cost for segment recommendation", segment_id=segment.id)
            continue
        cost = _decimal(unit_cost) * _segment_length_km(segment)
        result[segment.section_id][bucket] += cost

    structures = models.StructureInventory.objects.filter(section_id__in=section_ids).select_related(
        "section__road",
        "bridgedetail",
        "culvertdetail",
    )
    structure_map = {structure.id: structure for structure in structures}

    structure_recs = models.StructureInterventionRecommendation.objects.select_related("recommended_item").filter(structure_id__in=structure_map.keys())
    for rec in structure_recs:
        structure = structure_map.get(rec.structure_id)
        if structure is None:
            continue
        bucket = _bucket_for_work_code(getattr(rec.recommended_item, "work_code", None)) or "structure_bneck_cost"
        unit_cost = getattr(rec.recommended_item, "unit_cost", None)
        if not bucket:
            _log_missing("Missing SRAD bucket for structure recommendation", structure_id=structure.id)
            continue
        if unit_cost is None:
            _log_missing("Missing unit cost for structure recommendation", structure_id=structure.id)
            continue
        quantity = _structure_quantity(structure, getattr(rec.recommended_item, "unit", None))
        result[structure.section_id][bucket] += _decimal(unit_cost) * quantity

    planned_qs = models.RoadSectionIntervention.objects.filter(
        section_id__in=section_ids, intervention_year=fiscal_year
    ).select_related("intervention", "section")

    planned_sections = set()
    for intervention in planned_qs:
        bucket = _bucket_for_section_intervention(intervention)
        if not bucket:
            continue
        section_id = intervention.section_id
        if section_id not in planned_sections:
            result[section_id] = {field: Decimal("0") for field in BUCKET_FIELDS}
            planned_sections.add(section_id)
        result[section_id][bucket] += _decimal(intervention.estimated_cost)

    for section in section_list:
        buckets = result.get(section.id)
        if buckets is None:
            buckets = _default_bucket_map()
            result[section.id] = buckets
        buckets["year_cost"] = sum(buckets[field] for field in BUCKET_FIELDS)

    return result
