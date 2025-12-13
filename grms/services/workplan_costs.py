from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Dict, Iterable, Tuple

from grms import models
from grms.utils import geometry_length_km, geos_length_km


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


def _structure_quantity(structure: models.StructureInventory) -> Tuple[Decimal, str]:
    quantity_m = _structure_length_m(structure)
    if quantity_m is not None:
        return quantity_m, "length_m"

    # TODO: refine per-structure quantity once more detailed fields are available
    return Decimal(1), "default"


def _structure_quantity_for_unit(quantity_m: Decimal, unit: str) -> Decimal:
    unit_normalized = (unit or "").lower()
    if unit_normalized == "km":
        return quantity_m / Decimal(1000)
    if unit_normalized == "m":
        return quantity_m
    return quantity_m


def _road_length_km(road: models.Road) -> Decimal:
    if road.total_length_km is not None:
        return _decimal(road.total_length_km)

    sections = getattr(road, "sections", None)
    if sections is None:
        return Decimal("0")

    return sum(_decimal(section.length_km) for section in sections.all())


def _ensure_row(road: models.Road, rows: Dict[int, Dict[str, Decimal]]):
    if road.id in rows:
        return rows[road.id]

    rows[road.id] = {
        "road": road,
        "road_length_km": _road_length_km(road),
        "rm_cost": Decimal("0"),
        "pm_cost": Decimal("0"),
        "rehab_cost": Decimal("0"),
        "road_bneck_cost": Decimal("0"),
        "structure_bneck_cost": Decimal("0"),
    }
    return rows[road.id]


def _apply_segment_recommendations(rows: Dict[int, Dict[str, Decimal]]):
    recs = models.SegmentInterventionRecommendation.objects.select_related(
        "segment__section__road", "recommended_item"
    )

    for rec in recs:
        segment = rec.segment
        road = segment.section.road
        row = _ensure_row(road, rows)

        length_km = _segment_length_km(segment)
        unit_cost = _decimal(getattr(rec.recommended_item, "unit_cost", None))
        work_code = str(getattr(rec.recommended_item, "work_code", ""))

        bucket = None
        if work_code == "01":
            bucket = "rm_cost"
        elif work_code == "02":
            bucket = "pm_cost"
        elif work_code == "05":
            bucket = "rehab_cost"
        elif work_code in {"101", "102"}:
            bucket = "road_bneck_cost"

        if bucket:
            row[bucket] += unit_cost * length_km


def _apply_structure_recommendations(rows: Dict[int, Dict[str, Decimal]]):
    recs = models.StructureInterventionRecommendation.objects.select_related(
        "structure__road",
        "structure__section",
        "structure__bridgedetail",
        "structure__culvertdetail",
        "structure__retainingwalldetail",
        "structure__gabionwalldetail",
        "recommended_item",
    )

    for rec in recs:
        structure = rec.structure
        road = structure.road
        row = _ensure_row(road, rows)

        quantity_m, _ = _structure_quantity(structure)
        unit = getattr(rec.recommended_item, "unit", "")
        unit_cost = _decimal(getattr(rec.recommended_item, "unit_cost", None))

        quantity = _structure_quantity_for_unit(quantity_m, unit)
        row["structure_bneck_cost"] += unit_cost * quantity


def _finalise_rows(rows: Dict[int, Dict[str, Decimal]]):
    result = []
    totals = defaultdict(Decimal)
    for row in rows.values():
        total = sum(row[field] for field in BUCKET_FIELDS)
        row["total_cost"] = total
        for field in ("road_length_km", *BUCKET_FIELDS, "total_cost"):
            totals[field] += row[field]
        result.append(row)

    result.sort(key=lambda entry: str(entry["road"]))
    return result, totals


def compute_global_costs_by_road(fy=None) -> Tuple[Iterable[Dict[str, object]], Dict[str, Decimal]]:
    rows: Dict[int, Dict[str, Decimal]] = {}

    for road in models.Road.objects.prefetch_related("sections"):
        _ensure_row(road, rows)

    _apply_segment_recommendations(rows)
    _apply_structure_recommendations(rows)

    return _finalise_rows(rows)
