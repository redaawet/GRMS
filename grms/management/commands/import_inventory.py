from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from grms.models import Road, RoadNameAlias, RoadSection, RoadSegment, StructureInventory
from traffic.models import TrafficSurveyOverall, TrafficSurveySummary


@dataclass
class ImportCounts:
    created: int = 0
    updated: int = 0
    skipped: int = 0

    def add(self, bucket: str, amount: int = 1) -> None:
        setattr(self, bucket, getattr(self, bucket) + amount)


TRAFFIC_VEHICLE_MAP = {
    "bus": "Bus",
    "car": "Car",
    "heavy_goods": "HeavyGoods",
    "light_goods": "LightGoods",
    "medium_goods": "MediumGoods",
    "mini_bus": "MiniBus",
    "motorcycle": "Motorcycle",
    "tractor": "Tractor",
}

CROSS_SECTION_MAP = {
    "flat": "Flat",
    "f": "Flat",
    "embankment": "Embankment",
    "e": "Embankment",
    "cutembankment": "Cut/Embankment",
    "cut/embankment": "Cut/Embankment",
    "cutting": "Cutting",
    "x": "Cutting",
    "c": "Cut/Embankment",
}

TERRAIN_MAP = {
    "flat": "Flat",
    "f": "Flat",
    "rolling": "Rolling",
    "r": "Rolling",
    "mountainous": "Mountainous",
    "m": "Mountainous",
    "escarpment": "Escarpment",
    "e": "Escarpment",
}

STRUCTURE_CATEGORY_MAP = {
    "bridge": "Bridge",
    "culvert": "Culvert",
    "ford": "Ford",
    "retainingwall": "Retaining Wall",
    "gabionwall": "Gabion Wall",
    "wall": "Retaining Wall",
    "other": "Other",
}

STRUCTURE_POINT_CATEGORIES = {"Bridge", "Culvert", "Ford", "Other"}
STRUCTURE_LINE_CATEGORIES = {"Retaining Wall", "Gabion Wall"}


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def _road_alias_key(road_from: str, road_to: str) -> str:
    return f"{_normalize_key(road_from)}:{_normalize_key(road_to)}"


def _parse_decimal(value: object) -> Decimal | None:
    text = _normalize_text(value)
    if not text:
        return None
    text = text.replace(",", "")
    try:
        return Decimal(text)
    except Exception:
        return None


def _parse_bool(value: object) -> bool:
    text = _normalize_text(value).lower()
    return text in {"true", "1", "yes", "y", "√", "check", "checked", "x"}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _resolve_road(
    row: dict[str, str],
    roads_by_identifier: dict[str, Road],
    roads_by_key: dict[str, Road],
    alias_by_key: dict[str, RoadNameAlias],
    aliases_to_create: dict[str, RoadNameAlias],
) -> Road | None:
    road_identifier = _normalize_text(row.get("road_identifier"))
    road_from = _normalize_text(row.get("road_name_from"))
    road_to = _normalize_text(row.get("road_name_to"))

    if road_identifier:
        road = roads_by_identifier.get(road_identifier)
        if road and road_from and road_to:
            key = _road_alias_key(road_from, road_to)
            if key not in alias_by_key and key not in aliases_to_create:
                aliases_to_create[key] = RoadNameAlias(
                    road=road,
                    name_from=road_from,
                    name_to=road_to,
                    normalized_key=key,
                )
        return road

    if road_from and road_to:
        key = _road_alias_key(road_from, road_to)
        alias = alias_by_key.get(key)
        if alias:
            return alias.road
        road = roads_by_key.get(key)
        if road:
            if key not in aliases_to_create:
                aliases_to_create[key] = RoadNameAlias(
                    road=road,
                    name_from=road_from,
                    name_to=road_to,
                    normalized_key=key,
                )
            return road
    return None


def _bulk_create_aliases(aliases: Iterable[RoadNameAlias]) -> None:
    if aliases:
        RoadNameAlias.objects.bulk_create(list(aliases), ignore_conflicts=True)


def _normalize_choice(value: str, mapping: dict[str, str]) -> str:
    key = _normalize_key(value)
    if not key:
        return ""
    return mapping.get(key, "")


class Command(BaseCommand):
    help = "Import traffic, cross-section, and structure inventory data from canonical CSVs."

    def add_arguments(self, parser):
        parser.add_argument("--traffic", type=Path, help="Canonical traffic CSV path")
        parser.add_argument("--cross_section", type=Path, help="Canonical cross-section CSV path")
        parser.add_argument("--structures", type=Path, help="Canonical structures CSV path")
        parser.add_argument("--dry-run", action="store_true", help="Validate without committing changes")

    def handle(self, *args, **options):
        traffic_path: Path | None = options.get("traffic")
        cross_section_path: Path | None = options.get("cross_section")
        structures_path: Path | None = options.get("structures")
        dry_run: bool = options.get("dry_run")

        if not any([traffic_path, cross_section_path, structures_path]):
            raise CommandError("Provide at least one CSV via --traffic, --cross_section, or --structures.")

        if traffic_path:
            if not traffic_path.exists():
                raise CommandError(f"Traffic CSV not found: {traffic_path}")
            self.stdout.write("Importing traffic CSV...")
            with transaction.atomic():
                counts = self._import_traffic(traffic_path)
                if dry_run:
                    transaction.set_rollback(True)
            self.stdout.write(self._format_counts("Traffic", counts))

        if cross_section_path:
            if not cross_section_path.exists():
                raise CommandError(f"Cross-section CSV not found: {cross_section_path}")
            self.stdout.write("Importing cross-section CSV...")
            with transaction.atomic():
                counts = self._import_cross_section(cross_section_path)
                if dry_run:
                    transaction.set_rollback(True)
            self.stdout.write(self._format_counts("Cross-section", counts))

        if structures_path:
            if not structures_path.exists():
                raise CommandError(f"Structures CSV not found: {structures_path}")
            self.stdout.write("Importing structures CSV...")
            with transaction.atomic():
                counts = self._import_structures(structures_path)
                if dry_run:
                    transaction.set_rollback(True)
            self.stdout.write(self._format_counts("Structures", counts))

    def _format_counts(self, label: str, counts: ImportCounts) -> str:
        return (
            f"{label} import: {counts.created} created, {counts.updated} updated, "
            f"{counts.skipped} skipped."
        )

    def _import_traffic(self, path: Path) -> ImportCounts:
        rows = _read_csv(path)
        counts = ImportCounts()

        roads = Road.objects.all()
        roads_by_identifier = {road.road_identifier: road for road in roads}
        roads_by_key = {
            _road_alias_key(road.road_name_from, road.road_name_to): road for road in roads
        }
        alias_by_key = {
            alias.normalized_key: alias
            for alias in RoadNameAlias.objects.select_related("road").all()
        }
        aliases_to_create: dict[str, RoadNameAlias] = {}

        resolved_rows = []
        for row in rows:
            road = _resolve_road(row, roads_by_identifier, roads_by_key, alias_by_key, aliases_to_create)
            if not road:
                counts.add("skipped")
                continue
            fiscal_year = int(row.get("fiscal_year") or timezone.now().year)
            adt_total = _parse_decimal(row.get("adt_total")) or Decimal("0")
            vehicle_values = {
                key: _parse_decimal(row.get(key)) for key in TRAFFIC_VEHICLE_MAP
            }
            resolved_rows.append((road, fiscal_year, adt_total, vehicle_values))

        _bulk_create_aliases(aliases_to_create.values())

        if not resolved_rows:
            return counts

        road_ids = {road.id for road, _, _, _ in resolved_rows}
        years = {year for _, year, _, _ in resolved_rows}

        overall_qs = TrafficSurveyOverall.objects.filter(
            road_id__in=road_ids, fiscal_year__in=years
        )
        overall_map = {(item.road_id, item.fiscal_year): item for item in overall_qs}

        summary_qs = TrafficSurveySummary.objects.filter(
            road_id__in=road_ids, fiscal_year__in=years, traffic_survey__isnull=True
        )
        summary_map = {
            (item.road_id, item.fiscal_year, item.vehicle_class): item for item in summary_qs
        }

        new_overall = []
        update_overall = []
        new_summary = []
        update_summary = []

        for road, fiscal_year, adt_total, vehicle_values in resolved_rows:
            overall_key = (road.id, fiscal_year)
            overall = overall_map.get(overall_key)
            if overall:
                overall.adt_total = adt_total
                overall.pcu_total = Decimal("0")
                overall.confidence_score = Decimal("0")
                update_overall.append(overall)
                counts.add("updated")
            else:
                new_overall.append(
                    TrafficSurveyOverall(
                        road=road,
                        fiscal_year=fiscal_year,
                        adt_total=adt_total,
                        pcu_total=Decimal("0"),
                        confidence_score=Decimal("0"),
                    )
                )
                counts.add("created")

            for key, vehicle_class in TRAFFIC_VEHICLE_MAP.items():
                value = vehicle_values.get(key)
                if value is None:
                    continue
                summary_key = (road.id, fiscal_year, vehicle_class)
                summary = summary_map.get(summary_key)
                if summary:
                    summary.avg_daily_count_all_cycles = value
                    summary.adt_final = value
                    summary.pcu_final = Decimal("0")
                    summary.adt_total = adt_total
                    summary.pcu_total = Decimal("0")
                    summary.confidence_score = Decimal("0")
                    update_summary.append(summary)
                    counts.add("updated")
                else:
                    new_summary.append(
                        TrafficSurveySummary(
                            road=road,
                            fiscal_year=fiscal_year,
                            vehicle_class=vehicle_class,
                            traffic_survey=None,
                            avg_daily_count_all_cycles=value,
                            adt_final=value,
                            pcu_final=Decimal("0"),
                            adt_total=adt_total,
                            pcu_total=Decimal("0"),
                            confidence_score=Decimal("0"),
                        )
                    )
                    counts.add("created")

        if new_overall:
            TrafficSurveyOverall.objects.bulk_create(new_overall)
        if update_overall:
            TrafficSurveyOverall.objects.bulk_update(
                update_overall, ["adt_total", "pcu_total", "confidence_score"]
            )
        if new_summary:
            TrafficSurveySummary.objects.bulk_create(new_summary)
        if update_summary:
            TrafficSurveySummary.objects.bulk_update(
                update_summary,
                [
                    "avg_daily_count_all_cycles",
                    "adt_final",
                    "pcu_final",
                    "adt_total",
                    "pcu_total",
                    "confidence_score",
                ],
            )

        return counts

    def _import_cross_section(self, path: Path) -> ImportCounts:
        rows = _read_csv(path)
        counts = ImportCounts()

        roads = Road.objects.all()
        roads_by_identifier = {road.road_identifier: road for road in roads}
        roads_by_key = {
            _road_alias_key(road.road_name_from, road.road_name_to): road for road in roads
        }
        alias_by_key = {
            alias.normalized_key: alias
            for alias in RoadNameAlias.objects.select_related("road").all()
        }
        aliases_to_create: dict[str, RoadNameAlias] = {}

        resolved_rows = []
        for row in rows:
            road = _resolve_road(row, roads_by_identifier, roads_by_key, alias_by_key, aliases_to_create)
            if not road:
                counts.add("skipped")
                continue
            section_number = _parse_decimal(row.get("section_number"))
            if section_number is None:
                counts.add("skipped")
                continue
            station_from = _parse_decimal(row.get("station_from_km"))
            station_to = _parse_decimal(row.get("station_to_km"))
            if station_from is None or station_to is None:
                counts.add("skipped")
                continue
            cross_section = _normalize_choice(row.get("cross_section", ""), CROSS_SECTION_MAP)
            terrain_transverse = _normalize_choice(row.get("terrain_transverse", ""), TERRAIN_MAP)
            terrain_longitudinal = _normalize_choice(row.get("terrain_longitudinal", ""), TERRAIN_MAP)
            if not cross_section or not terrain_transverse or not terrain_longitudinal:
                counts.add("skipped")
                continue
            resolved_rows.append(
                {
                    "road": road,
                    "section_number": int(section_number),
                    "station_from": station_from,
                    "station_to": station_to,
                    "cross_section": cross_section,
                    "terrain_transverse": terrain_transverse,
                    "terrain_longitudinal": terrain_longitudinal,
                    "ditch_left_present": _parse_bool(row.get("ditch_left_present")),
                    "ditch_right_present": _parse_bool(row.get("ditch_right_present")),
                    "shoulder_left_present": _parse_bool(row.get("shoulder_left_present")),
                    "shoulder_right_present": _parse_bool(row.get("shoulder_right_present")),
                    "carriageway_width_m": _parse_decimal(row.get("carriageway_width_m")),
                    "comment": _normalize_text(row.get("comment")),
                }
            )

        _bulk_create_aliases(aliases_to_create.values())

        if not resolved_rows:
            return counts

        road_ids = {row["road"].id for row in resolved_rows}
        sections = RoadSection.objects.filter(road_id__in=road_ids)
        section_map = {(section.road_id, section.section_number): section for section in sections}

        resolved_segments = []
        for row in resolved_rows:
            section = section_map.get((row["road"].id, row["section_number"]))
            if not section:
                counts.add("skipped")
                continue
            resolved_segments.append((section, row))

        if not resolved_segments:
            return counts

        section_ids = {section.id for section, _ in resolved_segments}
        existing_segments = RoadSegment.objects.filter(section_id__in=section_ids)
        existing_map = {
            (seg.section_id, seg.station_from_km, seg.station_to_km): seg
            for seg in existing_segments
        }
        max_sequences = {}
        for seg in existing_segments:
            max_sequences[seg.section_id] = max(
                max_sequences.get(seg.section_id, 0), seg.sequence_on_section
            )

        new_segments = []
        update_segments = []
        pending_by_section = {}
        for section, row in resolved_segments:
            key = (section.id, row["station_from"], row["station_to"])
            existing = existing_map.get(key)
            if existing:
                existing.cross_section = row["cross_section"]
                existing.terrain_transverse = row["terrain_transverse"]
                existing.terrain_longitudinal = row["terrain_longitudinal"]
                existing.ditch_left_present = row["ditch_left_present"]
                existing.ditch_right_present = row["ditch_right_present"]
                existing.shoulder_left_present = row["shoulder_left_present"]
                existing.shoulder_right_present = row["shoulder_right_present"]
                existing.carriageway_width_m = row["carriageway_width_m"]
                existing.comment = row["comment"]
                update_segments.append(existing)
                counts.add("updated")
            else:
                pending_by_section.setdefault(section.id, []).append((section, row))

        for section_id, items in pending_by_section.items():
            items.sort(key=lambda item: item[1]["station_from"])
            next_sequence = max_sequences.get(section_id, 0)
            section = items[0][0]
            for _, row in items:
                next_sequence += 1
                segment_identifier = (
                    f"{section.road.road_identifier}-S{section.sequence_on_road}-Sg{next_sequence}"
                )
                new_segments.append(
                    RoadSegment(
                        section=section,
                        sequence_on_section=next_sequence,
                        segment_identifier=segment_identifier,
                        station_from_km=row["station_from"],
                        station_to_km=row["station_to"],
                        cross_section=row["cross_section"],
                        terrain_transverse=row["terrain_transverse"],
                        terrain_longitudinal=row["terrain_longitudinal"],
                        ditch_left_present=row["ditch_left_present"],
                        ditch_right_present=row["ditch_right_present"],
                        shoulder_left_present=row["shoulder_left_present"],
                        shoulder_right_present=row["shoulder_right_present"],
                        carriageway_width_m=row["carriageway_width_m"],
                        comment=row["comment"],
                    )
                )
                counts.add("created")

        if new_segments:
            RoadSegment.objects.bulk_create(new_segments)
        if update_segments:
            RoadSegment.objects.bulk_update(
                update_segments,
                [
                    "cross_section",
                    "terrain_transverse",
                    "terrain_longitudinal",
                    "ditch_left_present",
                    "ditch_right_present",
                    "shoulder_left_present",
                    "shoulder_right_present",
                    "carriageway_width_m",
                    "comment",
                ],
            )

        return counts

    def _import_structures(self, path: Path) -> ImportCounts:
        rows = _read_csv(path)
        counts = ImportCounts()

        roads = Road.objects.all()
        roads_by_identifier = {road.road_identifier: road for road in roads}
        roads_by_key = {
            _road_alias_key(road.road_name_from, road.road_name_to): road for road in roads
        }
        alias_by_key = {
            alias.normalized_key: alias
            for alias in RoadNameAlias.objects.select_related("road").all()
        }
        aliases_to_create: dict[str, RoadNameAlias] = {}

        resolved_rows = []
        for row in rows:
            road = _resolve_road(row, roads_by_identifier, roads_by_key, alias_by_key, aliases_to_create)
            if not road:
                counts.add("skipped")
                continue
            section_number = _parse_decimal(row.get("section_number"))
            station_km = _parse_decimal(row.get("station_km"))
            start_chainage = _parse_decimal(row.get("start_chainage_km"))
            end_chainage = _parse_decimal(row.get("end_chainage_km"))
            category = _normalize_choice(row.get("structure_category", ""), STRUCTURE_CATEGORY_MAP)
            if not category:
                counts.add("skipped")
                continue
            if station_km is None and (start_chainage is None or end_chainage is None):
                counts.add("skipped")
                continue
            resolved_rows.append(
                {
                    "road": road,
                    "section_number": int(section_number) if section_number is not None else None,
                    "station_km": station_km,
                    "start_chainage_km": start_chainage,
                    "end_chainage_km": end_chainage,
                    "structure_category": category,
                    "structure_name": _normalize_text(row.get("structure_name")),
                    "easting_m": _parse_decimal(row.get("easting_m")),
                    "northing_m": _parse_decimal(row.get("northing_m")),
                    "comment": _normalize_text(row.get("comment")),
                }
            )

        _bulk_create_aliases(aliases_to_create.values())

        if not resolved_rows:
            return counts

        road_ids = {row["road"].id for row in resolved_rows}
        sections = RoadSection.objects.filter(road_id__in=road_ids)
        section_map = {(section.road_id, section.section_number): section for section in sections}

        resolved_structures = []
        for row in resolved_rows:
            section = None
            if row["section_number"] is not None:
                section = section_map.get((row["road"].id, row["section_number"]))
                if not section:
                    counts.add("skipped")
                    continue
            resolved_structures.append((section, row))

        if not resolved_structures:
            return counts

        existing_structures = StructureInventory.objects.filter(road_id__in=road_ids)
        existing_map = {
            (
                item.road_id,
                item.section_id,
                item.station_km,
                item.start_chainage_km,
                item.end_chainage_km,
                item.structure_category,
                item.structure_name,
            ): item
            for item in existing_structures
        }

        new_structures = []
        update_structures = []

        for section, row in resolved_structures:
            key = (
                row["road"].id,
                section.id if section else None,
                row["station_km"],
                row["start_chainage_km"],
                row["end_chainage_km"],
                row["structure_category"],
                row["structure_name"],
            )
            existing = existing_map.get(key)
            geometry_type = (
                StructureInventory.POINT
                if row["structure_category"] in STRUCTURE_POINT_CATEGORIES
                else StructureInventory.LINE
            )
            if existing:
                existing.geometry_type = geometry_type
                existing.section = section
                existing.station_km = row["station_km"]
                existing.start_chainage_km = row["start_chainage_km"]
                existing.end_chainage_km = row["end_chainage_km"]
                existing.easting_m = row["easting_m"]
                existing.northing_m = row["northing_m"]
                existing.comments = row["comment"]
                update_structures.append(existing)
                counts.add("updated")
            else:
                new_structures.append(
                    StructureInventory(
                        road=row["road"],
                        section=section,
                        geometry_type=geometry_type,
                        station_km=row["station_km"],
                        start_chainage_km=row["start_chainage_km"],
                        end_chainage_km=row["end_chainage_km"],
                        structure_category=row["structure_category"],
                        structure_name=row["structure_name"],
                        easting_m=row["easting_m"],
                        northing_m=row["northing_m"],
                        comments=row["comment"],
                    )
                )
                counts.add("created")

        if new_structures:
            StructureInventory.objects.bulk_create(new_structures)
        if update_structures:
            StructureInventory.objects.bulk_update(
                update_structures,
                [
                    "geometry_type",
                    "section",
                    "station_km",
                    "start_chainage_km",
                    "end_chainage_km",
                    "easting_m",
                    "northing_m",
                    "comments",
                ],
            )

        return counts
