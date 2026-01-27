
import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from django.utils import timezone

from grms.models import (
    AdminZone,
    Road,
    RoadSection,
    RoadSegment,
    RoadSocioEconomic,
    StructureInventory,
)
from traffic import models as traffic_models


ROAD_FILE = "Datas/roads_seed.csv"
SECTION_FILE = "Datas/road_sections_seed.csv"
SEGMENT_FILE = "Datas/road_segments_seed.csv"
STRUCTURE_FILE = "Datas/structures_seed.csv"
TRAFFIC_FILE = "Datas/traffic_seed.csv"
SOCIO_FILE = "Datas/road_socioeconomic_seed.csv"


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _normalize_road_key(road_from: str, road_to: str) -> str:
    return f"{_normalize_name(road_from)}{_normalize_name(road_to)}"


def _normalize_road_norm(value: str) -> str:
    return _normalize_name(value or "")


def _parse_decimal(value, *, default=None) -> Decimal | None:
    if value is None:
        return default
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return default
    try:
        return Decimal(text)
    except InvalidOperation:
        return default


def _parse_int(value, *, default=None):
    if value is None:
        return default
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return default
    try:
        return int(Decimal(text))
    except (InvalidOperation, ValueError):
        return default


def _parse_bool(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}


def _next_road_identifier(existing_ids: set[str]) -> str:
    max_num = 0
    for rid in existing_ids:
        match = re.match(r"RTR-(\d+)", rid or "")
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"RTR-{max_num + 1}"


class Command(BaseCommand):
    help = "Seed inventory tables from CSV files in the Datas folder."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="Datas",
            help="Folder containing CSV seed files (default: Datas).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate CSVs without writing to the database.",
        )
        parser.add_argument(
            "--wipe-road-data",
            action="store_true",
            help="Delete existing segments/structures/traffic for the roads in the CSVs before import.",
        )

    def handle(self, *args, **options):
        base_path = Path(options["path"]).resolve()
        if not base_path.exists():
            raise CommandError(f"Path not found: {base_path}")

        file_paths = {
            ROAD_FILE: base_path / ROAD_FILE,
            SECTION_FILE: base_path / SECTION_FILE,
            SEGMENT_FILE: base_path / SEGMENT_FILE,
            STRUCTURE_FILE: base_path / STRUCTURE_FILE,
            TRAFFIC_FILE: base_path / TRAFFIC_FILE,
            SOCIO_FILE: base_path / SOCIO_FILE,
        }

        missing = [name for name, path in file_paths.items() if not path.exists()]
        if missing:
            raise CommandError(f"Missing seed files: {', '.join(missing)}")

        dry_run = options["dry_run"]
        wipe = options["wipe_road_data"]

        summary = {
            "roads_created": 0,
            "roads_updated": 0,
            "sections_created": 0,
            "sections_updated": 0,
            "segments_created": 0,
            "segments_updated": 0,
            "structures_created": 0,
            "structures_updated": 0,
            "traffic_created": 0,
            "traffic_updated": 0,
            "socio_created": 0,
            "socio_updated": 0,
        }

        warnings = []

        with transaction.atomic():
            road_map = self._seed_roads(file_paths[ROAD_FILE], summary, warnings)
            section_map = self._seed_sections(file_paths[SECTION_FILE], road_map, summary, warnings)
            self._verify_sections_per_road(road_map, warnings)

            if wipe:
                self._wipe_road_data(set(road_map.values()))

            self._seed_segments(file_paths[SEGMENT_FILE], section_map, summary, warnings, wipe)
            self._seed_structures(file_paths[STRUCTURE_FILE], section_map, summary, warnings)
            self._seed_traffic(file_paths[TRAFFIC_FILE], road_map, summary, warnings)
        self._seed_socio(file_paths[SOCIO_FILE], road_map, summary, warnings)

        if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS("Seed summary:"))
        for key, value in summary.items():
            self.stdout.write(f"- {key.replace('_', ' ')}: {value}")

        if warnings:
            self.stdout.write(self.style.WARNING("Warnings:"))
            for warning in warnings:
                self.stdout.write(f"- {warning}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no database changes were saved."))

    def _seed_roads(self, path: Path, summary: dict, warnings: list[str]) -> dict[str, Road]:
        existing_roads = list(Road.objects.select_related("admin_zone").all())
        existing_ids = {road.road_identifier for road in existing_roads if road.road_identifier}
        road_by_norm = {
            _normalize_road_key(road.road_name_from, road.road_name_to): road for road in existing_roads
        }

        road_map: dict[str, Road] = {}
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                road_norm = _normalize_road_norm(row.get("road_name_norm"))
                road_from = row.get("road_from") or row.get("road_name_from") or row.get("road_from".upper())
                road_to = row.get("road_to") or row.get("road_name_to") or row.get("road_to".upper())
                road_from = (road_from or "").strip()
                road_to = (road_to or "").strip()

                zone_name = (row.get("zone") or "").strip() or "Unknown"
                admin_zone, _ = AdminZone.objects.get_or_create(name=zone_name)

                defaults = {
                    "road_name_from": road_from,
                    "road_name_to": road_to,
                    "design_standard": "Basic Access",
                    "admin_zone": admin_zone,
                    "admin_woreda": None,
                    "total_length_km": _parse_decimal(row.get("length_km_cs")) or Decimal("0"),
                    "start_easting": _parse_decimal(row.get("start_e")),
                    "start_northing": _parse_decimal(row.get("start_n")),
                    "end_easting": _parse_decimal(row.get("end_e")),
                    "end_northing": _parse_decimal(row.get("end_n")),
                    "surface_type": "Gravel",
                    "managing_authority": "Regional",
                }

                existing = road_by_norm.get(road_norm)
                if existing:
                    Road.objects.filter(pk=existing.pk).update(**defaults)
                    existing.refresh_from_db()
                    road_map[road_norm] = existing
                    summary["roads_updated"] += 1
                    continue

                road_identifier = _next_road_identifier(existing_ids)
                existing_ids.add(road_identifier)
                defaults["road_identifier"] = road_identifier

                road = Road.objects.create(**defaults)
                road_map[road_norm] = road
                summary["roads_created"] += 1

        return road_map

    def _seed_sections(
        self,
        path: Path,
        road_map: dict[str, Road],
        summary: dict,
        warnings: list[str],
    ) -> dict[tuple[str, int], RoadSection]:
        section_map: dict[tuple[str, int], RoadSection] = {}

        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                road_norm = _normalize_road_norm(row.get("road_name_norm"))
                section_no = _parse_int(row.get("section_no"))
                if road_norm not in road_map:
                    warnings.append(f"Section skipped; road not found for '{row.get('road_name_norm')}'.")
                    continue
                if not section_no:
                    warnings.append(f"Section skipped; invalid section number for '{row.get('road_name_norm')}'.")
                    continue

                road = road_map[road_norm]
                start_chainage = _parse_decimal(row.get("start_chainage_km")) or Decimal("0")
                end_chainage = _parse_decimal(row.get("end_chainage_km")) or Decimal("0")
                length_km = _parse_decimal(row.get("length_km"))
                if length_km is None:
                    length_km = (end_chainage - start_chainage).quantize(Decimal("0.001"))

                surface_type = road.surface_type or "Gravel"
                surface_thickness = Decimal("0") if surface_type in {"Gravel", "DBST", "Asphalt", "Sealed"} else None

                existing = RoadSection.objects.filter(road=road, section_number=section_no).first()
                update_values = {
                    "sequence_on_road": section_no,
                    "section_number": section_no,
                    "start_chainage_km": start_chainage,
                    "end_chainage_km": end_chainage,
                    "length_km": length_km,
                    "surface_type": surface_type,
                    "surface_thickness_cm": surface_thickness,
                }

                if existing:
                    RoadSection.objects.filter(pk=existing.pk).update(**update_values)
                    existing.refresh_from_db()
                    section_map[(road_norm, section_no)] = existing
                    summary["sections_updated"] += 1
                else:
                    obj = RoadSection(road=road, **update_values)
                    RoadSection.objects.bulk_create([obj])
                    created = RoadSection.objects.get(road=road, section_number=section_no)
                    section_map[(road_norm, section_no)] = created
                    summary["sections_created"] += 1

        return section_map

    def _seed_segments(
        self,
        path: Path,
        section_map: dict[tuple[str, int], RoadSection],
        summary: dict,
        warnings: list[str],
        wipe: bool,
    ):
        segment_rows: dict[tuple[str, int], list[dict]] = {}
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                road_norm = _normalize_road_norm(row.get("road_name_norm"))
                section_no = _parse_int(row.get("section_no"))
                if (road_norm, section_no) not in section_map:
                    warnings.append(f"Segment skipped; section not found for '{row.get('road_name_norm')}' S{section_no}.")
                    continue
                segment_rows.setdefault((road_norm, section_no), []).append(row)

        cross_section_map = {
            "C": "Cutting",
            "E": "Embankment",
            "F": "Flat",
            "F/C": "Cut/Embankment",
            "X": "Flat",
        }
        terrain_map = {"F": "Flat", "R": "Rolling", "M": "Mountainous"}

        for key, rows in segment_rows.items():
            road_norm, section_no = key
            section = section_map[key]
            rows.sort(key=lambda r: _parse_decimal(r.get("station_from_km")) or Decimal("0"))

            if wipe:
                RoadSegment.objects.filter(section=section).delete()

            to_create = []
            for idx, row in enumerate(rows, start=1):
                station_from = _parse_decimal(row.get("station_from_km")) or Decimal("0")
                station_to = _parse_decimal(row.get("station_to_km")) or Decimal("0")
                if section.length_km is not None and station_to > section.length_km:
                    warnings.append(
                        f"Segment skipped; station_to_km exceeds section length for "
                        f"'{row.get('road_name_norm')}' S{section_no}."
                    )
                    continue

                cross_section = cross_section_map.get((row.get("cross_section_raw") or "").strip(), "Flat")
                terrain_transverse = terrain_map.get((row.get("terrain_transverse_raw") or "").strip(), "Flat")
                terrain_longitudinal = terrain_map.get((row.get("terrain_longitudinal_raw") or "").strip(), "Flat")
                segment_identifier = f"{section.road.road_identifier}-S{section.sequence_on_road}-Sg{idx}"

                update_values = {
                    "sequence_on_section": idx,
                    "segment_identifier": segment_identifier,
                    "station_from_km": station_from,
                    "station_to_km": station_to,
                    "cross_section": cross_section,
                    "terrain_transverse": terrain_transverse,
                    "terrain_longitudinal": terrain_longitudinal,
                    "ditch_left_present": _parse_bool(row.get("left_ditch")),
                    "ditch_right_present": _parse_bool(row.get("right_ditch")),
                    "shoulder_left_present": False,
                    "shoulder_right_present": False,
                    "carriageway_width_m": _parse_decimal(row.get("carriageway_width_m")),
                    "comment": "" if (row.get("comment") or "").lower() == "nan" else (row.get("comment") or ""),
                }

                existing = RoadSegment.objects.filter(
                    section=section,
                    station_from_km=station_from,
                    station_to_km=station_to,
                ).first()
                if existing and not wipe:
                    try:
                        RoadSegment.objects.filter(pk=existing.pk).update(**update_values)
                        summary["segments_updated"] += 1
                    except IntegrityError as exc:
                        raise CommandError(
                            f"Segment update failed for {segment_identifier}. "
                            "Try using --wipe-road-data."
                        ) from exc
                else:
                    obj = RoadSegment(section=section, **update_values)
                    to_create.append(obj)

            if to_create:
                RoadSegment.objects.bulk_create(to_create)
                summary["segments_created"] += len(to_create)

    def _seed_structures(
        self,
        path: Path,
        section_map: dict[tuple[str, int], RoadSection],
        summary: dict,
        warnings: list[str],
    ):
        asset_map = {
            "bridge": "Bridge",
            "culvert": "Culvert",
            "ford": "Ford",
            "retaining_wall": "Retaining Wall",
            "gabion_wall": "Gabion Wall",
            "other": "Other",
            "quarry_site": "Other",
        }

        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            to_create = []
            for row in reader:
                road_norm = _normalize_road_norm(row.get("road_name_norm"))
                section_no = _parse_int(row.get("section_no"))
                section = section_map.get((road_norm, section_no))
                if not section:
                    warnings.append(f"Structure skipped; section not found for '{row.get('road_name_norm')}'.")
                    continue

                asset = (row.get("asset") or "").strip().lower()
                structure_category = asset_map.get(asset, "Other")
                geometry_type = StructureInventory.POINT
                if structure_category in {"Retaining Wall", "Gabion Wall"}:
                    geometry_type = StructureInventory.LINE
                station_rel = _parse_decimal(row.get("station_km_in_section"))
                station_abs = _parse_decimal(row.get("station_km"))
                if station_rel is not None:
                    station_km = (section.start_chainage_km or Decimal("0")) + station_rel
                else:
                    station_km = station_abs

                update_values = {
                    "road": section.road,
                    "section": section,
                    "structure_category": structure_category,
                    "geometry_type": geometry_type,
                    "structure_name": (row.get("type_raw") or "").strip(),
                    "station_km": station_km,
                    "easting_m": _parse_decimal(row.get("easting")),
                    "northing_m": _parse_decimal(row.get("northing")),
                    "comments": (row.get("asset") or "").strip(),
                }

                existing = StructureInventory.objects.filter(
                    road=section.road,
                    section=section,
                    station_km=station_km,
                    structure_category=structure_category,
                ).first()
                if existing:
                    StructureInventory.objects.filter(pk=existing.pk).update(**update_values)
                    summary["structures_updated"] += 1
                else:
                    to_create.append(StructureInventory(**update_values))

            if to_create:
                StructureInventory.objects.bulk_create(to_create)
                summary["structures_created"] += len(to_create)

    def _seed_traffic(
        self,
        path: Path,
        road_map: dict[str, Road],
        summary: dict,
        warnings: list[str],
    ):
        vehicle_columns = {
            "Buses_avg": "Bus",
            "Cars_avg": "Car",
            "Heavy Goods_avg": "HeavyGoods",
            "Light Goods_avg": "LightGoods",
            "Medium Goods_avg": "MediumGoods",
            "Mini-buses_avg": "MiniBus",
            "Motor Cycle_avg": "Motorcycle",
            "Tractors_avg": "Tractor",
        }
        fiscal_year = timezone.now().year

        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                road_norm = _normalize_road_norm(row.get("road_name_norm"))
                road = road_map.get(road_norm)
                if not road:
                    warnings.append(f"Traffic skipped; road not found for '{row.get('road_name_norm')}'.")
                    continue
                adt_total = _parse_decimal(row.get("adt")) or Decimal("0")

                for column, vehicle_class in vehicle_columns.items():
                    avg_value = _parse_decimal(row.get(column))
                    if avg_value is None:
                        continue

                    defaults = {
                        "avg_daily_count_all_cycles": avg_value,
                        "adt_final": avg_value,
                        "pcu_final": avg_value,
                        "adt_total": adt_total,
                        "pcu_total": adt_total,
                        "confidence_score": Decimal("0"),
                    }

                    existing = traffic_models.TrafficSurveySummary.objects.filter(
                        traffic_survey=None,
                        road=road,
                        fiscal_year=fiscal_year,
                        vehicle_class=vehicle_class,
                    ).first()
                    if existing:
                        traffic_models.TrafficSurveySummary.objects.filter(pk=existing.pk).update(**defaults)
                        summary["traffic_updated"] += 1
                    else:
                        traffic_models.TrafficSurveySummary.objects.create(
                            traffic_survey=None,
                            road=road,
                            fiscal_year=fiscal_year,
                            vehicle_class=vehicle_class,
                            **defaults,
                        )
                        summary["traffic_created"] += 1

    def _seed_socio(
        self,
        path: Path,
        road_map: dict[str, Road],
        summary: dict,
        warnings: list[str],
    ):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                road_norm = _normalize_road_norm(row.get("road_name_norm"))
                road = road_map.get(road_norm)
                if not road:
                    warnings.append(f"Socio-economic skipped; road not found for '{row.get('road_name_norm')}'.")
                    continue

                defaults = {
                    "population_served": _parse_int(row.get("population_served"), default=10000),
                    "notes": (row.get("notes") or "").strip(),
                }

                obj, created = RoadSocioEconomic.objects.update_or_create(road=road, defaults=defaults)
                if created:
                    summary["socio_created"] += 1
                else:
                    summary["socio_updated"] += 1

    def _verify_sections_per_road(self, road_map: dict[str, Road], warnings: list[str]):
        for road_norm, road in road_map.items():
            count = RoadSection.objects.filter(road=road).count()
            if count != 3:
                warnings.append(
                    f"Road '{road.road_identifier}' has {count} sections; expected 3."
                )

    def _wipe_road_data(self, roads: set[Road]):
        if not roads:
            return
        RoadSegment.objects.filter(section__road__in=roads).delete()
        StructureInventory.objects.filter(road__in=roads).delete()
        traffic_models.TrafficSurveySummary.objects.filter(road__in=roads).delete()
