from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from grms.models import (
    AdminZone,
    Road,
    RoadSection,
    RoadSegment,
    RoadSocioEconomic,
    StructureInventory,
)
from traffic.models import TrafficSurveyOverall, TrafficSurveySummary


@dataclass
class ImportSummary:
    created: dict[str, int]
    updated: dict[str, int]
    skipped: dict[str, int]

    def bump(self, bucket: dict[str, int], key: str, count: int = 1) -> None:
        bucket[key] = bucket.get(key, 0) + count

    def record_created(self, model: str) -> None:
        self.bump(self.created, model)

    def record_updated(self, model: str) -> None:
        self.bump(self.updated, model)

    def record_skipped(self, model: str) -> None:
        self.bump(self.skipped, model)


ROAD_FIELDS = {
    "design_standard": "Basic Access",
    "surface_type": "Earth",
    "managing_authority": "Regional",
}

SECTION_SURFACE_THICKNESS_CM = Decimal("20.00")

TERRAIN_MAP = {
    "F": "Flat",
    "R": "Rolling",
    "M": "Mountainous",
    "E": "Escarpment",
}

CROSS_SECTION_MAP = {
    "F": "Flat",
    "E": "Embankment",
    "C": "Cut/Embankment",
    "X": "Cutting",
}

STRUCTURE_CATEGORY_MAP = {
    "bridge": "Bridge",
    "culvert": "Culvert",
    "other": "Other",
    "quarry_site": "Other",
}

TRAFFIC_COLUMN_MAP = {
    "Buses_avg": "Bus",
    "Cars_avg": "Car",
    "Heavy Goods_avg": "HeavyGoods",
    "Light Goods_avg": "LightGoods",
    "Medium Goods_avg": "MediumGoods",
    "Mini-buses_avg": "MiniBus",
    "Motor Cycle_avg": "Motorcycle",
    "Tractors_avg": "Tractor",
}


def _normalize_key(value: str) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _road_key_from_fields(road_from: str, road_to: str) -> str:
    return _normalize_key(f"{road_from}{road_to}")


def _road_key_from_csv(value: str, road_from: str, road_to: str) -> str:
    key = _normalize_key(value)
    if key:
        return key
    return _road_key_from_fields(road_from, road_to)


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    value_str = str(value).strip()
    if not value_str or value_str.lower() == "nan":
        return None
    try:
        return Decimal(value_str)
    except Exception:
        return None


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    value_str = str(value).strip().lower()
    return value_str in {"true", "1", "yes", "y"}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _next_road_identifier() -> tuple[int, int]:
    max_seq = 0
    for identifier in Road.objects.values_list("road_identifier", flat=True):
        if not identifier:
            continue
        match = re.match(r"RTR-(\d+)", identifier)
        if match:
            max_seq = max(max_seq, int(match.group(1)))
    return max_seq + 1, max_seq


def _fallback_geometry(length_km: Decimal) -> dict[str, Any]:
    if length_km <= 0:
        length_km = Decimal("0.001")
    lat_delta = float(length_km) / 111.0
    return {
        "type": "LineString",
        "coordinates": [[0.0, 0.0], [0.0, lat_delta]],
        "srid": 4326,
    }


def _ensure_section_surface(section: RoadSection) -> None:
    if section.surface_type in {"Gravel", "DBST", "Asphalt", "Sealed"}:
        if section.surface_thickness_cm is None:
            section.surface_thickness_cm = SECTION_SURFACE_THICKNESS_CM


class Command(BaseCommand):
    help = "Seed road inventory data from CSV extracts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="Datas",
            help="Path to the folder containing the CSV seed files.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without committing changes.",
        )
        parser.add_argument(
            "--wipe-road-data",
            action="store_true",
            help="Delete segments/structures/traffic for the listed roads before importing.",
        )

    def handle(self, *args, **options):
        base_path = Path(options["path"]).expanduser().resolve()
        dry_run = options["dry_run"]
        wipe = options["wipe_road_data"]

        summary = ImportSummary(created={}, updated={}, skipped={})

        roads_path = base_path / "roads_seed.csv"
        sections_path = base_path / "road_sections_seed.csv"
        segments_path = base_path / "road_segments_seed.csv"
        structures_path = base_path / "structures_seed.csv"
        traffic_path = base_path / "traffic_seed.csv"
        socioeconomic_path = base_path / "road_socioeconomic_seed.csv"

        for path in [
            roads_path,
            sections_path,
            segments_path,
            structures_path,
            traffic_path,
            socioeconomic_path,
        ]:
            if not path.exists():
                raise FileNotFoundError(f"Missing CSV file: {path}")

        road_rows = _read_csv(roads_path)
        section_rows = _read_csv(sections_path)
        segment_rows = _read_csv(segments_path)
        structure_rows = _read_csv(structures_path)
        traffic_rows = _read_csv(traffic_path)
        socioeconomic_rows = _read_csv(socioeconomic_path)

        existing_roads = Road.objects.select_related("admin_zone").all()
        road_map: dict[str, Road] = {}
        for road in existing_roads:
            forward_key = _road_key_from_fields(road.road_name_from, road.road_name_to)
            reverse_key = _road_key_from_fields(road.road_name_to, road.road_name_from)
            road_map[forward_key] = road
            road_map[reverse_key] = road

        next_seq, _ = _next_road_identifier()

        roads_by_key: dict[str, Road] = {}
        road_ids: set[int] = set()

        with transaction.atomic():
            for row in road_rows:
                road_key = _road_key_from_csv(
                    row.get("road_name_norm", ""),
                    row.get("road_from", ""),
                    row.get("road_to", ""),
                )
                if not road_key:
                    summary.record_skipped("Road")
                    continue

                road_from = (row.get("road_from") or "").strip()
                road_to = (row.get("road_to") or "").strip()
                zone_name = (row.get("zone") or "").strip() or "Unknown"
                admin_zone, _ = AdminZone.objects.get_or_create(name=zone_name)

                length_km = (
                    _parse_decimal(row.get("length_km_preferred"))
                    or _parse_decimal(row.get("length_km_cs"))
                    or _parse_decimal(row.get("length_km_traffic"))
                    or Decimal("0")
                )

                start_easting = _parse_decimal(row.get("start_e"))
                start_northing = _parse_decimal(row.get("start_n"))
                end_easting = _parse_decimal(row.get("end_e"))
                end_northing = _parse_decimal(row.get("end_n"))

                road = road_map.get(road_key)
                created = False
                if road is None:
                    road_identifier = f"RTR-{next_seq}"
                    next_seq += 1
                    road = Road(road_identifier=road_identifier)
                    created = True

                road.road_name_from = road_from
                road.road_name_to = road_to
                road.design_standard = ROAD_FIELDS["design_standard"]
                road.surface_type = ROAD_FIELDS["surface_type"]
                road.managing_authority = ROAD_FIELDS["managing_authority"]
                road.admin_zone = admin_zone
                road.total_length_km = length_km
                road.start_easting = start_easting
                road.start_northing = start_northing
                road.end_easting = end_easting
                road.end_northing = end_northing

                if not (start_easting and start_northing and end_easting and end_northing):
                    road.geometry = _fallback_geometry(length_km)

                road.save()

                if created:
                    summary.record_created("Road")
                else:
                    summary.record_updated("Road")

                roads_by_key[road_key] = road
                road_ids.add(road.id)

            if wipe and road_ids:
                RoadSegment.objects.filter(section__road_id__in=road_ids).delete()
                StructureInventory.objects.filter(road_id__in=road_ids).delete()
                TrafficSurveySummary.objects.filter(road_id__in=road_ids).delete()
                TrafficSurveyOverall.objects.filter(road_id__in=road_ids).delete()

            sections_by_key: dict[tuple[int, int], RoadSection] = {}
            existing_sections = {
                (section.road_id, section.section_number): section
                for section in RoadSection.objects.filter(road_id__in=road_ids)
            }
            new_sections: list[RoadSection] = []
            sections_to_validate: set[int] = set()
            for row in section_rows:
                road_key = _road_key_from_csv(
                    row.get("road_name_norm", ""),
                    row.get("road_from", ""),
                    row.get("road_to", ""),
                )
                road = roads_by_key.get(road_key) or road_map.get(road_key)
                if road is None:
                    summary.record_skipped("RoadSection")
                    continue

                section_no = int(float(row.get("section_no") or 0))
                start_chainage = _parse_decimal(row.get("start_chainage_km")) or Decimal("0")
                end_chainage = _parse_decimal(row.get("end_chainage_km")) or Decimal("0")
                surface_type = road.surface_type or ROAD_FIELDS["surface_type"]
                existing_section = existing_sections.get((road.id, section_no))
                surface_thickness_cm = None
                if existing_section and existing_section.surface_thickness_cm is not None:
                    surface_thickness_cm = existing_section.surface_thickness_cm
                elif surface_type in {"Gravel", "DBST", "Asphalt", "Sealed"}:
                    surface_thickness_cm = SECTION_SURFACE_THICKNESS_CM

                section_defaults = {
                    "sequence_on_road": section_no,
                    "section_number": section_no,
                    "start_chainage_km": start_chainage,
                    "end_chainage_km": end_chainage,
                    "surface_type": surface_type,
                    "surface_thickness_cm": surface_thickness_cm,
                }

                if existing_section:
                    RoadSection.objects.filter(pk=existing_section.pk).update(**section_defaults)
                    summary.record_updated("RoadSection")
                    sections_by_key[(road.id, section_no)] = existing_section
                    sections_to_validate.add(existing_section.pk)
                else:
                    section = RoadSection(road=road, **section_defaults)
                    _ensure_section_surface(section)
                    new_sections.append(section)
                    summary.record_created("RoadSection")

            if new_sections:
                created_sections = RoadSection.objects.bulk_create(new_sections)
                for section in created_sections:
                    sections_by_key[(section.road_id, section.section_number)] = section
                    sections_to_validate.add(section.pk)

            if sections_to_validate:
                for section in RoadSection.objects.filter(pk__in=sections_to_validate):
                    section.save()

            for road_id in road_ids:
                section_count = RoadSection.objects.filter(road_id=road_id).count()
                if section_count != 3:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Road {road_id} has {section_count} sections (expected 3)."
                        )
                    )

            segments_by_section: dict[int, list[dict[str, str]]] = defaultdict(list)
            for row in segment_rows:
                road_key = _road_key_from_csv(
                    row.get("road_name_norm", ""),
                    row.get("road_from", ""),
                    row.get("road_to", ""),
                )
                road = roads_by_key.get(road_key) or road_map.get(road_key)
                if road is None:
                    summary.record_skipped("RoadSegment")
                    continue

                section_no = int(float(row.get("section_no") or 0))
                section = sections_by_key.get((road.id, section_no))
                if section is None:
                    summary.record_skipped("RoadSegment")
                    continue

                segments_by_section[section.id].append(row)

            for section_id, rows in segments_by_section.items():
                section = RoadSection.objects.get(id=section_id)
                sorted_rows = sorted(
                    rows,
                    key=lambda item: (
                        float(item.get("station_from_km") or 0),
                        float(item.get("station_to_km") or 0),
                    ),
                )
                for index, row in enumerate(sorted_rows, start=1):
                    station_from = _parse_decimal(row.get("station_from_km")) or Decimal("0")
                    station_to = _parse_decimal(row.get("station_to_km")) or Decimal("0")
                    if section.length_km and station_to > section.length_km:
                        summary.record_skipped("RoadSegment")
                        continue

                    cross_section_raw = (row.get("cross_section_raw") or "").strip().upper()
                    terrain_transverse_raw = (row.get("terrain_transverse_raw") or "").strip().upper()
                    terrain_longitudinal_raw = (row.get("terrain_longitudinal_raw") or "").strip().upper()

                    defaults = {
                        "sequence_on_section": index,
                        "station_from_km": station_from,
                        "station_to_km": station_to,
                        "cross_section": CROSS_SECTION_MAP.get(cross_section_raw, "Flat"),
                        "terrain_transverse": TERRAIN_MAP.get(terrain_transverse_raw, "Flat"),
                        "terrain_longitudinal": TERRAIN_MAP.get(terrain_longitudinal_raw, "Flat"),
                        "ditch_left_present": _parse_bool(row.get("left_ditch")),
                        "ditch_right_present": _parse_bool(row.get("right_ditch")),
                        "carriageway_width_m": _parse_decimal(row.get("carriageway_width_m")),
                        "comment": "" if str(row.get("comment", "")).lower() == "nan" else row.get("comment", ""),
                    }

                    segment, created = RoadSegment.objects.update_or_create(
                        section=section,
                        station_from_km=station_from,
                        station_to_km=station_to,
                        defaults=defaults,
                    )

                    if created:
                        summary.record_created("RoadSegment")
                    else:
                        summary.record_updated("RoadSegment")

            for row in structure_rows:
                road_key = _road_key_from_csv(
                    row.get("road_name_norm", ""),
                    row.get("road_from", ""),
                    row.get("road_to", ""),
                )
                road = roads_by_key.get(road_key) or road_map.get(road_key)
                if road is None:
                    summary.record_skipped("StructureInventory")
                    continue

                section_no = int(float(row.get("section_no") or 0))
                section = sections_by_key.get((road.id, section_no))
                if section is None:
                    summary.record_skipped("StructureInventory")
                    continue

                asset = (row.get("asset") or "").strip().lower()
                structure_category = STRUCTURE_CATEGORY_MAP.get(asset, "Other")
                station_in_section = _parse_decimal(row.get("station_km_in_section"))
                station_km = None
                if station_in_section is not None:
                    station_km = (section.start_chainage_km or Decimal("0")) + station_in_section

                defaults = {
                    "road": road,
                    "section": section,
                    "station_km": station_km,
                    "structure_category": structure_category,
                    "structure_name": "Quarry site" if asset == "quarry_site" else "",
                    "easting_m": _parse_decimal(row.get("easting")),
                    "northing_m": _parse_decimal(row.get("northing")),
                }

                structure, created = StructureInventory.objects.update_or_create(
                    road=road,
                    section=section,
                    station_km=station_km,
                    structure_category=structure_category,
                    defaults=defaults,
                )

                if created:
                    summary.record_created("StructureInventory")
                else:
                    summary.record_updated("StructureInventory")

            current_year = timezone.now().year
            for row in traffic_rows:
                road_key = _road_key_from_csv(
                    row.get("road_name_norm", ""),
                    row.get("road_from", ""),
                    row.get("road_to", ""),
                )
                road = roads_by_key.get(road_key) or road_map.get(road_key)
                if road is None:
                    summary.record_skipped("TrafficSurveySummary")
                    continue

                adt = _parse_decimal(row.get("adt")) or Decimal("0")

                overall_defaults = {
                    "adt_total": adt,
                    "pcu_total": Decimal("0"),
                    "confidence_score": Decimal("0"),
                }
                _, created = TrafficSurveyOverall.objects.update_or_create(
                    road=road,
                    fiscal_year=current_year,
                    defaults=overall_defaults,
                )
                if created:
                    summary.record_created("TrafficSurveyOverall")
                else:
                    summary.record_updated("TrafficSurveyOverall")

                for column, vehicle_class in TRAFFIC_COLUMN_MAP.items():
                    value = _parse_decimal(row.get(column))
                    if value is None:
                        continue

                    summary_defaults = {
                        "traffic_survey": None,
                        "avg_daily_count_all_cycles": value,
                        "adt_final": value,
                        "pcu_final": Decimal("0"),
                        "adt_total": adt,
                        "pcu_total": Decimal("0"),
                        "confidence_score": Decimal("0"),
                    }
                    _, created = TrafficSurveySummary.objects.update_or_create(
                        road=road,
                        fiscal_year=current_year,
                        vehicle_class=vehicle_class,
                        traffic_survey=None,
                        defaults=summary_defaults,
                    )

                    if created:
                        summary.record_created("TrafficSurveySummary")
                    else:
                        summary.record_updated("TrafficSurveySummary")

            for row in socioeconomic_rows:
                road_key = _road_key_from_csv(
                    row.get("road_name_norm", ""),
                    row.get("road_from", ""),
                    row.get("road_to", ""),
                )
                road = roads_by_key.get(road_key) or road_map.get(road_key)
                if road is None:
                    summary.record_skipped("RoadSocioEconomic")
                    continue

                population = _parse_decimal(row.get("population_served"))
                notes = row.get("notes") or ""

                defaults = {
                    "population_served": int(population) if population is not None else 10000,
                    "notes": notes,
                }

                socio, created = RoadSocioEconomic.objects.update_or_create(
                    road=road,
                    defaults=defaults,
                )

                if created:
                    summary.record_created("RoadSocioEconomic")
                else:
                    summary.record_updated("RoadSocioEconomic")

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("\nSeed import summary:")
        for label, bucket in (
            ("Created", summary.created),
            ("Updated", summary.updated),
            ("Skipped", summary.skipped),
        ):
            if not bucket:
                continue
            self.stdout.write(f"{label}:")
            for model, count in sorted(bucket.items()):
                self.stdout.write(f"  - {model}: {count}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete; no changes were saved."))
