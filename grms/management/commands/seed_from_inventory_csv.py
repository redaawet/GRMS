from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.contrib.gis.geos import LineString
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
from traffic.models import TrafficSurveyOverall, TrafficSurveySummary


@dataclass
class ImportSummary:
    created: Dict[str, int] = field(default_factory=dict)
    updated: Dict[str, int] = field(default_factory=dict)
    skipped: Dict[str, int] = field(default_factory=dict)

    def bump(self, bucket: str, model: str, amount: int = 1) -> None:
        target = getattr(self, bucket)
        target[model] = target.get(model, 0) + amount


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


def _geometry_srid() -> int:
    return Road._meta.get_field("geometry").srid or 4326


def _fallback_geometry(length_km: Decimal) -> LineString:
    safe_length = length_km if length_km > 0 else Decimal("0.001")
    end_x = float(safe_length * Decimal("1000"))
    return LineString((0.0, 0.0), (end_x, 0.0), srid=_geometry_srid())


def _build_geometry(
    start_easting: Decimal | None,
    start_northing: Decimal | None,
    end_easting: Decimal | None,
    end_northing: Decimal | None,
    length_km: Decimal,
) -> LineString:
    if all(value is not None for value in (start_easting, start_northing, end_easting, end_northing)):
        return LineString(
            (float(start_easting), float(start_northing)),
            (float(end_easting), float(end_northing)),
            srid=_geometry_srid(),
        )
    return _fallback_geometry(length_km)


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

        missing_files = []
        for path in [
            roads_path,
            sections_path,
            segments_path,
            structures_path,
            traffic_path,
            socioeconomic_path,
        ]:
            if not path.exists():
                missing_files.append(str(path))
        if missing_files:
            missing_list = ", ".join(missing_files)
            raise CommandError(
                "Missing seed files: "
                f"{missing_list}. Provide --path to the folder containing the CSVs."
            )

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
        missing_coords: list[str] = []
        missing_lengths: list[str] = []
        geometry_by_road_id: dict[int, LineString] = {}

        with transaction.atomic():
            for row in road_rows:
                road_key = _road_key_from_csv(
                    row.get("road_name_norm", ""),
                    row.get("road_from", ""),
                    row.get("road_to", ""),
                )
                if not road_key:
                    summary.bump("skipped", "Road")
                    continue

                road_from = (row.get("road_from") or "").strip()
                road_to = (row.get("road_to") or "").strip()
                zone_name = (row.get("zone") or "").strip() or "Unknown"
                admin_zone, _ = AdminZone.objects.get_or_create(name=zone_name)

                length_km = (
                    _parse_decimal(row.get("length_km_preferred"))
                    or _parse_decimal(row.get("length_km_cs"))
                )
                if length_km is None:
                    missing_lengths.append(road_key or f"{road_from}-{road_to}")
                    length_km = Decimal("0")

                start_easting = _parse_decimal(row.get("start_e"))
                start_northing = _parse_decimal(row.get("start_n"))
                end_easting = _parse_decimal(row.get("end_e"))
                end_northing = _parse_decimal(row.get("end_n"))
                if not all(value is not None for value in (start_easting, start_northing, end_easting, end_northing)):
                    missing_coords.append(road_key or f"{road_from}-{road_to}")

                geometry = _build_geometry(start_easting, start_northing, end_easting, end_northing, length_km)

                road = road_map.get(road_key)
                created = False
                if road is None:
                    road_identifier = f"RTR-{next_seq}"
                    next_seq += 1
                    road = Road(road_identifier=road_identifier)
                    created = True

                if created:
                    road.road_name_from = road_from
                    road.road_name_to = road_to
                    road.design_standard = ROAD_FIELDS["design_standard"]
                    road.surface_type = ROAD_FIELDS["surface_type"]
                    road.managing_authority = ROAD_FIELDS["managing_authority"]
                    road.admin_zone = admin_zone
                    road.total_length_km = length_km
                    road.save()
                else:
                    Road.objects.filter(pk=road.pk).update(geometry=None)

                Road.objects.filter(pk=road.pk).update(
                    road_name_from=road_from,
                    road_name_to=road_to,
                    design_standard=ROAD_FIELDS["design_standard"],
                    surface_type=ROAD_FIELDS["surface_type"],
                    managing_authority=ROAD_FIELDS["managing_authority"],
                    admin_zone=admin_zone,
                    total_length_km=length_km,
                    start_easting=start_easting,
                    start_northing=start_northing,
                    end_easting=end_easting,
                    end_northing=end_northing,
                    geometry=None,
                )
                road.refresh_from_db()

                if created:
                    summary.bump("created", "Road")
                else:
                    summary.bump("updated", "Road")

                roads_by_key[road_key] = road
                road_ids.add(road.id)
                geometry_by_road_id[road.id] = geometry

            if wipe and road_ids:
                RoadSegment.objects.filter(section__road_id__in=road_ids).delete()
                StructureInventory.objects.filter(road_id__in=road_ids).delete()
                TrafficSurveySummary.objects.filter(road_id__in=road_ids).delete()
                TrafficSurveyOverall.objects.filter(road_id__in=road_ids).delete()

            sections_by_key: dict[tuple[int, int], RoadSection] = {}
            for row in section_rows:
                road_key = _road_key_from_csv(
                    row.get("road_name_norm", ""),
                    row.get("road_from", ""),
                    row.get("road_to", ""),
                )
                road = roads_by_key.get(road_key) or road_map.get(road_key)
                if road is None:
                    summary.bump("skipped", "RoadSection")
                    continue

                section_no = int(float(row.get("section_no") or 0))
                start_chainage = _parse_decimal(row.get("start_chainage_km")) or Decimal("0")
                end_chainage = _parse_decimal(row.get("end_chainage_km")) or Decimal("0")

                section_defaults = {
                    "sequence_on_road": section_no,
                    "section_number": section_no,
                    "start_chainage_km": start_chainage,
                    "end_chainage_km": end_chainage,
                    "surface_type": road.surface_type or ROAD_FIELDS["surface_type"],
                }

                section, created = RoadSection.objects.update_or_create(
                    road=road,
                    section_number=section_no,
                    defaults=section_defaults,
                )
                _ensure_section_surface(section)
                section.save()

                if created:
                    summary.bump("created", "RoadSection")
                else:
                    summary.bump("updated", "RoadSection")

                sections_by_key[(road.id, section_no)] = section

            for road_id in road_ids:
                road = Road.objects.get(id=road_id)
                section_count = RoadSection.objects.filter(road_id=road_id).count()
                if section_count == 0:
                    road_length = Decimal(str(road.total_length_km or 0))
                    third_length = (road_length / Decimal("3")).quantize(Decimal("0.001"))
                    second_end = (third_length * 2).quantize(Decimal("0.001"))
                    chainages = [
                        (Decimal("0"), third_length),
                        (third_length, second_end),
                        (second_end, road_length),
                    ]
                    for idx, (start_km, end_km) in enumerate(chainages, start=1):
                        RoadSection.objects.create(
                            road=road,
                            section_number=idx,
                            sequence_on_road=idx,
                            start_chainage_km=start_km,
                            end_chainage_km=end_km,
                            surface_type=road.surface_type or ROAD_FIELDS["surface_type"],
                        )
                    section_count = 3

                if section_count != 3:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Road {road_id} has {section_count} sections (expected 3)."
                        )
                    )

            for road_id, geometry in geometry_by_road_id.items():
                Road.objects.filter(pk=road_id).update(geometry=geometry)

            segments_by_section: dict[int, list[dict[str, str]]] = defaultdict(list)
            for row in segment_rows:
                road_key = _road_key_from_csv(
                    row.get("road_name_norm", ""),
                    row.get("road_from", ""),
                    row.get("road_to", ""),
                )
                road = roads_by_key.get(road_key) or road_map.get(road_key)
                if road is None:
                    summary.bump("skipped", "RoadSegment")
                    continue

                section_no = int(float(row.get("section_no") or 0))
                section = sections_by_key.get((road.id, section_no))
                if section is None:
                    summary.bump("skipped", "RoadSegment")
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
                        summary.bump("skipped", "RoadSegment")
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
                        summary.bump("created", "RoadSegment")
                    else:
                        summary.bump("updated", "RoadSegment")

            for row in structure_rows:
                road_key = _road_key_from_csv(
                    row.get("road_name_norm", ""),
                    row.get("road_from", ""),
                    row.get("road_to", ""),
                )
                road = roads_by_key.get(road_key) or road_map.get(road_key)
                if road is None:
                    summary.bump("skipped", "StructureInventory")
                    continue

                section_no = int(float(row.get("section_no") or 0))
                section = sections_by_key.get((road.id, section_no))
                if section is None:
                    summary.bump("skipped", "StructureInventory")
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
                    summary.bump("created", "StructureInventory")
                else:
                    summary.bump("updated", "StructureInventory")

            current_year = timezone.now().year
            for row in traffic_rows:
                road_key = _road_key_from_csv(
                    row.get("road_name_norm", ""),
                    row.get("road_from", ""),
                    row.get("road_to", ""),
                )
                road = roads_by_key.get(road_key) or road_map.get(road_key)
                if road is None:
                    summary.bump("skipped", "TrafficSurveySummary")
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
                    summary.bump("created", "TrafficSurveyOverall")
                else:
                    summary.bump("updated", "TrafficSurveyOverall")

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
                        summary.bump("created", "TrafficSurveySummary")
                    else:
                        summary.bump("updated", "TrafficSurveySummary")

            for row in socioeconomic_rows:
                road_key = _road_key_from_csv(
                    row.get("road_name_norm", ""),
                    row.get("road_from", ""),
                    row.get("road_to", ""),
                )
                road = roads_by_key.get(road_key) or road_map.get(road_key)
                if road is None:
                    summary.bump("skipped", "RoadSocioEconomic")
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
                    summary.bump("created", "RoadSocioEconomic")
                else:
                    summary.bump("updated", "RoadSocioEconomic")

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

        if missing_coords:
            self.stdout.write(
                self.style.WARNING(
                    "Roads missing coordinates: " + ", ".join(sorted(set(missing_coords)))
                )
            )
        if missing_lengths:
            self.stdout.write(
                self.style.WARNING(
                    "Roads missing length: " + ", ".join(sorted(set(missing_lengths)))
                )
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete; no changes were saved."))
