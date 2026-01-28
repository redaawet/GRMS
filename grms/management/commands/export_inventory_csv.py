from __future__ import annotations

import csv
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from django.core.management.base import BaseCommand
from django.db.models import Max

from grms.models import Road, RoadSection, RoadSegment, RoadSocioEconomic, StructureInventory
from traffic.models import TrafficSurveyOverall, TrafficSurveySummary


def _normalize_key(value: str) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _road_key(road_from: str, road_to: str) -> str:
    return _normalize_key(f"{road_from}{road_to}")


def _quantize(value: Decimal | None, places: str) -> Decimal | None:
    if value is None:
        return None
    try:
        return value.quantize(Decimal(places))
    except (InvalidOperation, AttributeError):
        return None


def _as_str(value: Decimal | None) -> str:
    return "" if value is None else f"{value}"


class Command(BaseCommand):
    help = "Export inventory data to CSV files compatible with seed_from_inventory_csv."
    export_models = (
        Road,
        RoadSection,
        RoadSegment,
        StructureInventory,
        TrafficSurveyOverall,
        TrafficSurveySummary,
        RoadSocioEconomic,
    )
    export_files = {
        Road: "roads_seed.csv",
        RoadSection: "road_sections_seed.csv",
        RoadSegment: "road_segments_seed.csv",
        StructureInventory: "structures_seed.csv",
        TrafficSurveyOverall: "traffic_seed.csv",
        TrafficSurveySummary: "traffic_seed.csv",
        RoadSocioEconomic: "road_socioeconomic_seed.csv",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="Datas",
            help="Output folder for seed CSV files (default: Datas).",
        )

    def handle(self, *args, **options):
        base_path = Path(options["path"]).expanduser().resolve()
        base_path.mkdir(parents=True, exist_ok=True)

        warnings: list[str] = []

        roads = list(
            Road.objects.select_related("admin_zone")
            .prefetch_related("sections", "structures", "traffic_survey_summaries")
            .all()
        )

        road_key_map = {road.id: _road_key(road.road_name_from, road.road_name_to) for road in roads}

        self._write_roads(base_path / "roads_seed.csv", roads, road_key_map)
        self._write_sections(base_path / "road_sections_seed.csv", roads, road_key_map, warnings)
        self._write_segments(base_path / "road_segments_seed.csv", roads, road_key_map, warnings)
        self._write_structures(base_path / "structures_seed.csv", roads, road_key_map, warnings)
        self._write_traffic(base_path / "traffic_seed.csv", roads, road_key_map, warnings)
        self._write_socio(base_path / "road_socioeconomic_seed.csv", roads, road_key_map)
        self._write_import_order(base_path)

        if warnings:
            self.stdout.write(self.style.WARNING("Warnings:"))
            for warning in warnings:
                self.stdout.write(f"- {warning}")

        self.stdout.write(self.style.SUCCESS("CSV export complete."))

    def _write_import_order(self, base_path: Path) -> None:
        ordered = self._topological_order(self.export_models)
        lines = [
            "Import order (topological sort by FK dependencies among exported models):",
        ]
        for index, model in enumerate(ordered, start=1):
            dependencies = self._model_fk_dependencies(model)
            dependency_names = ", ".join(sorted(dep.__name__ for dep in dependencies)) if dependencies else "None"
            filename = self.export_files.get(model, "N/A")
            lines.append(
                f"{index}. {model.__name__} ({filename}) - depends on: {dependency_names}"
            )

        lines.append("")
        lines.append("Notes:")
        lines.append("- traffic_seed.csv populates both TrafficSurveyOverall and TrafficSurveySummary.")
        lines.append("- Import roads, then sections, then segments before dependent models.")

        (base_path / "IMPORT_ORDER.txt").write_text("\n".join(lines), encoding="utf-8")

    def _model_fk_dependencies(self, model) -> set[type]:
        dependencies: set[type] = set()
        model_set = set(self.export_models)
        for field in model._meta.get_fields():
            if not getattr(field, "is_relation", False):
                continue
            if not getattr(field, "many_to_one", False):
                continue
            related = getattr(field, "related_model", None)
            if related in model_set and related is not model:
                dependencies.add(related)
        return dependencies

    def _topological_order(self, models: Iterable[type]) -> list[type]:
        models_list = list(models)
        model_set = set(models_list)
        order_hint = {model: index for index, model in enumerate(models_list)}
        dependencies = {model: set() for model in models_list}
        dependents: dict[type, set[type]] = defaultdict(set)

        for model in models_list:
            deps = self._model_fk_dependencies(model)
            dependencies[model] = set(deps)
            for dep in deps:
                if dep in model_set:
                    dependents[dep].add(model)

        ready = [model for model in models_list if not dependencies[model]]
        ordered: list[type] = []

        while ready:
            ready.sort(key=lambda item: order_hint[item])
            model = ready.pop(0)
            ordered.append(model)
            for dependent in sorted(dependents.get(model, set()), key=lambda item: order_hint[item]):
                dependencies[dependent].discard(model)
                if not dependencies[dependent]:
                    if dependent not in ready and dependent not in ordered:
                        ready.append(dependent)

        remaining = [model for model in models_list if model not in ordered]
        if remaining:
            ordered.extend(sorted(remaining, key=lambda item: order_hint[item]))

        return ordered

    def _write_roads(self, path: Path, roads: Iterable[Road], road_key_map: dict[int, str]) -> None:
        fieldnames = [
            "road_name_norm",
            "road_from",
            "road_to",
            "zone",
            "length_km_preferred",
            "length_km_cs",
            "length_km_traffic",
            "start_e",
            "start_n",
            "end_e",
            "end_n",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for road in roads:
                length_km = _quantize(road.total_length_km, "0.01")
                writer.writerow(
                    {
                        "road_name_norm": road_key_map.get(road.id, ""),
                        "road_from": road.road_name_from,
                        "road_to": road.road_name_to,
                        "zone": getattr(road.admin_zone, "name", "") or "",
                        "length_km_preferred": _as_str(length_km),
                        "length_km_cs": _as_str(length_km),
                        "length_km_traffic": _as_str(length_km),
                        "start_e": _as_str(_quantize(road.start_easting, "0.01")),
                        "start_n": _as_str(_quantize(road.start_northing, "0.01")),
                        "end_e": _as_str(_quantize(road.end_easting, "0.01")),
                        "end_n": _as_str(_quantize(road.end_northing, "0.01")),
                    }
                )

    def _write_sections(
        self,
        path: Path,
        roads: Iterable[Road],
        road_key_map: dict[int, str],
        warnings: list[str],
    ) -> None:
        fieldnames = [
            "road_name_norm",
            "road_from",
            "road_to",
            "section_no",
            "start_chainage_km",
            "end_chainage_km",
        ]
        tolerance = Decimal("0.02")
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for road in roads:
                sections = list(road.sections.all())
                if not sections:
                    continue
                sections.sort(key=lambda s: (s.start_chainage_km or Decimal("0"), s.end_chainage_km or Decimal("0")))

                road_length = None
                if road.geometry:
                    road_length = road.compute_length_km_from_geom()
                elif road.total_length_km is not None:
                    road_length = Decimal(str(road.total_length_km))

                min_start = min((s.start_chainage_km or Decimal("0")) for s in sections)
                if min_start > tolerance:
                    shift = min_start
                    warnings.append(f"Road {road.road_identifier}: shifted section chainages by {shift} km.")
                else:
                    shift = Decimal("0")

                adjusted = []
                for section in sections:
                    start = (section.start_chainage_km or Decimal("0")) - shift
                    end = (section.end_chainage_km or Decimal("0")) - shift
                    if start < 0:
                        start = Decimal("0")
                    if end < 0:
                        end = Decimal("0")
                    adjusted.append(
                        {
                            "section_no": section.section_number or section.sequence_on_road or 0,
                            "start": start,
                            "end": end,
                        }
                    )

                if road_length:
                    last_idx = max(range(len(adjusted)), key=lambda i: adjusted[i]["end"])
                    adjusted[last_idx]["end"] = road_length
                    for item in adjusted:
                        if item["end"] > road_length:
                            item["end"] = road_length
                        if item["start"] > road_length:
                            item["start"] = road_length

                adjusted.sort(key=lambda item: (item["start"], item["end"]))

                previous_end = None
                for item in adjusted:
                    start = item["start"]
                    end = item["end"]
                    if previous_end is not None and start < previous_end:
                        start = previous_end
                    if end <= start:
                        continue
                    previous_end = end

                    writer.writerow(
                        {
                            "road_name_norm": road_key_map.get(road.id, ""),
                            "road_from": road.road_name_from,
                            "road_to": road.road_name_to,
                            "section_no": item["section_no"],
                            "start_chainage_km": _as_str(_quantize(start, "0.001")),
                            "end_chainage_km": _as_str(_quantize(end, "0.001")),
                        }
                    )

    def _write_segments(
        self,
        path: Path,
        roads: Iterable[Road],
        road_key_map: dict[int, str],
        warnings: list[str],
    ) -> None:
        fieldnames = [
            "road_name_norm",
            "road_from",
            "road_to",
            "section_no",
            "station_from_km",
            "station_to_km",
            "cross_section_raw",
            "terrain_transverse_raw",
            "terrain_longitudinal_raw",
            "left_ditch",
            "right_ditch",
            "carriageway_width_m",
            "comment",
        ]
        cross_section_inv = {
            "Cutting": "X",
            "Embankment": "E",
            "Cut/Embankment": "C",
            "Flat": "F",
        }
        terrain_inv = {
            "Flat": "F",
            "Rolling": "R",
            "Mountainous": "M",
            "Escarpment": "E",
        }
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for road in roads:
                sections = list(road.sections.all())
                if not sections:
                    continue
                for section in sections:
                    segments = list(section.segments.all())
                    if not segments:
                        continue
                    segments.sort(
                        key=lambda s: (s.station_from_km or Decimal("0"), s.station_to_km or Decimal("0"))
                    )
                    previous_end = None
                    for segment in segments:
                        start = segment.station_from_km or Decimal("0")
                        end = segment.station_to_km or Decimal("0")
                        start = _quantize(start, "0.001") or Decimal("0")
                        end = _quantize(end, "0.001") or Decimal("0")
                        if section.length_km and end > section.length_km:
                            end = _quantize(section.length_km, "0.001") or end
                        if previous_end is not None and start < previous_end:
                            start = previous_end
                        if end <= start:
                            warnings.append(
                                f"Segment skipped for {road.road_identifier} S{section.section_number}: invalid range."
                            )
                            continue
                        previous_end = end

                        writer.writerow(
                            {
                                "road_name_norm": road_key_map.get(road.id, ""),
                                "road_from": road.road_name_from,
                                "road_to": road.road_name_to,
                                "section_no": section.section_number,
                                "station_from_km": _as_str(start),
                                "station_to_km": _as_str(end),
                                "cross_section_raw": cross_section_inv.get(segment.cross_section, "F"),
                                "terrain_transverse_raw": terrain_inv.get(segment.terrain_transverse, "F"),
                                "terrain_longitudinal_raw": terrain_inv.get(segment.terrain_longitudinal, "F"),
                                "left_ditch": "1" if segment.ditch_left_present else "0",
                                "right_ditch": "1" if segment.ditch_right_present else "0",
                                "carriageway_width_m": _as_str(_quantize(segment.carriageway_width_m, "0.01")),
                                "comment": segment.comment or "",
                            }
                        )

    def _write_structures(
        self,
        path: Path,
        roads: Iterable[Road],
        road_key_map: dict[int, str],
        warnings: list[str],
    ) -> None:
        fieldnames = [
            "road_name_norm",
            "road_from",
            "road_to",
            "section_no",
            "asset",
            "station_km_in_section",
            "type_raw",
            "easting",
            "northing",
        ]
        category_map = {
            "Bridge": "bridge",
            "Culvert": "culvert",
            "Ford": "other",
            "Retaining Wall": "other",
            "Gabion Wall": "other",
            "Other": "other",
        }
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for road in roads:
                structures = list(road.structures.all())
                if not structures:
                    continue
                for structure in structures:
                    if structure.geometry_type == StructureInventory.LINE:
                        warnings.append(
                            f"Structure skipped for {road.road_identifier}: line structures not supported in CSV."
                        )
                        continue
                    section = structure.section
                    station_km_in_section = None
                    if section and structure.station_km is not None:
                        station_km_in_section = structure.station_km - (section.start_chainage_km or Decimal("0"))
                        station_km_in_section = _quantize(station_km_in_section, "0.001")
                    elif structure.station_km is not None:
                        station_km_in_section = _quantize(structure.station_km, "0.001")
                    section_no = section.section_number if section else ""

                    writer.writerow(
                        {
                            "road_name_norm": road_key_map.get(road.id, ""),
                            "road_from": road.road_name_from,
                            "road_to": road.road_name_to,
                            "section_no": section_no,
                            "asset": category_map.get(structure.structure_category, "other"),
                            "station_km_in_section": _as_str(station_km_in_section),
                            "type_raw": structure.structure_name or "",
                            "easting": _as_str(_quantize(structure.easting_m, "0.01")),
                            "northing": _as_str(_quantize(structure.northing_m, "0.01")),
                        }
                    )

    def _write_traffic(
        self,
        path: Path,
        roads: Iterable[Road],
        road_key_map: dict[int, str],
        warnings: list[str],
    ) -> None:
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
        fieldnames = ["road_name_norm", "road_from", "road_to", "adt"] + list(vehicle_columns.keys())

        summaries_by_road: dict[int, dict[int, list[TrafficSurveySummary]]] = defaultdict(lambda: defaultdict(list))
        for summary in TrafficSurveySummary.objects.all():
            summaries_by_road[summary.road_id][summary.fiscal_year].append(summary)

        overalls_by_road: dict[int, list[TrafficSurveyOverall]] = defaultdict(list)
        for overall in TrafficSurveyOverall.objects.all():
            overalls_by_road[overall.road_id].append(overall)

        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()

            for road in roads:
                road_id = road.id
                year_candidates = set(summaries_by_road.get(road_id, {}).keys())
                if overalls_by_road.get(road_id):
                    year_candidates.update({overall.fiscal_year for overall in overalls_by_road[road_id]})
                if not year_candidates:
                    continue

                latest_year = max(year_candidates)
                summaries = summaries_by_road.get(road_id, {}).get(latest_year, [])
                summary_map = {}
                for summary in summaries:
                    summary_map[summary.vehicle_class] = summary

                overall = None
                if overalls_by_road.get(road_id):
                    overall = max(overalls_by_road[road_id], key=lambda o: (o.fiscal_year, o.computed_at))
                adt = None
                if overall and overall.fiscal_year == latest_year:
                    adt = overall.adt_total
                elif summaries:
                    adt = summaries[0].adt_total

                row = {
                    "road_name_norm": road_key_map.get(road_id, ""),
                    "road_from": road.road_name_from,
                    "road_to": road.road_name_to,
                    "adt": _as_str(_quantize(adt, "0.001")),
                }
                for column, vehicle_class in vehicle_columns.items():
                    summary = summary_map.get(vehicle_class)
                    value = summary.avg_daily_count_all_cycles if summary else None
                    row[column] = _as_str(_quantize(value, "0.001"))

                writer.writerow(row)

    def _write_socio(
        self,
        path: Path,
        roads: Iterable[Road],
        road_key_map: dict[int, str],
    ) -> None:
        fieldnames = ["road_name_norm", "road_from", "road_to", "population_served", "notes"]
        socio_map = {entry.road_id: entry for entry in RoadSocioEconomic.objects.all()}
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for road in roads:
                socio = socio_map.get(road.id)
                if not socio:
                    continue
                writer.writerow(
                    {
                        "road_name_norm": road_key_map.get(road.id, ""),
                        "road_from": road.road_name_from,
                        "road_to": road.road_name_to,
                        "population_served": socio.population_served or "",
                        "notes": socio.notes or "",
                    }
                )
