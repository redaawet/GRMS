from __future__ import annotations

import random
from decimal import Decimal
from typing import Iterable

from django.contrib.gis.geos import LineString
from django.core.management.base import BaseCommand
from django.db.models import Max
from django.utils import timezone

from grms.models import (
    BridgeConditionSurvey,
    ConditionFactorLookup,
    CulvertConditionSurvey,
    OtherStructureConditionSurvey,
    QAStatus,
    Road,
    RoadConditionSurvey,
    RoadSection,
    RoadSegment,
    SegmentMCIResult,
    StructureConditionSurvey,
    StructureInventory,
)


def _fallback_geometry(length_km: Decimal, *, srid: int = 4326) -> LineString:
    """Create a placeholder linestring when geometry is missing."""
    safe_length = length_km if length_km and length_km > 0 else Decimal("0.001")
    degrees = float(safe_length) / 111.32
    return LineString((0.0, 0.0), (degrees, 0.0), srid=srid)


def _ensure_factor_lookups() -> dict[str, list[ConditionFactorLookup]]:
    defaults = {
        "drainage": [
            (1, Decimal("1.00"), "Drainage: Good"),
            (2, Decimal("0.75"), "Drainage: Fair"),
            (3, Decimal("0.50"), "Drainage: Poor"),
            (4, Decimal("0.25"), "Drainage: Bad"),
        ],
        "shoulder": [
            (1, Decimal("1.00"), "Shoulder: Good"),
            (2, Decimal("0.75"), "Shoulder: Fair"),
            (3, Decimal("0.50"), "Shoulder: Poor"),
            (4, Decimal("0.25"), "Shoulder: Bad"),
        ],
        "surface": [
            (1, Decimal("1.00"), "Surface: Good"),
            (2, Decimal("0.75"), "Surface: Fair"),
            (3, Decimal("0.50"), "Surface: Poor"),
            (4, Decimal("0.25"), "Surface: Bad"),
        ],
    }

    result: dict[str, list[ConditionFactorLookup]] = {}
    for factor_type, entries in defaults.items():
        lookups = list(
            ConditionFactorLookup.objects.filter(factor_type=factor_type).order_by("rating")
        )
        if not lookups:
            for rating, value, description in entries:
                ConditionFactorLookup.objects.get_or_create(
                    factor_type=factor_type,
                    rating=rating,
                    defaults={"factor_value": value, "description": description},
                )
            lookups = list(
                ConditionFactorLookup.objects.filter(factor_type=factor_type).order_by("rating")
            )
        result[factor_type] = lookups
    return result


def _pick_lookup(lookups: list[ConditionFactorLookup], seed: int) -> ConditionFactorLookup | None:
    if not lookups:
        return None
    return lookups[seed % len(lookups)]


class Command(BaseCommand):
    help = "Ensure road/section geometries exist and generate mock condition surveys."

    def add_arguments(self, parser):
        parser.add_argument(
            "--inspection-date",
            default=None,
            help="Inspection date in YYYY-MM-DD (default: today).",
        )

    def handle(self, *args, **options):
        inspection_date = options["inspection_date"]
        if inspection_date:
            inspection_date = timezone.datetime.fromisoformat(inspection_date).date()
        else:
            inspection_date = timezone.now().date()

        self._sync_road_geometry()
        self._sync_section_geometry()
        self._mock_road_surveys(inspection_date)
        self._mock_structure_surveys(inspection_date)

        self.stdout.write(self.style.SUCCESS("Geometry sync and mock surveys complete."))

    def _sync_road_geometry(self) -> None:
        for road in Road.objects.all():
            if road.geometry:
                if road.total_length_km is None:
                    road.total_length_km = road.compute_length_km_from_geom()
                    road.save(update_fields=["total_length_km"])
                continue

            length_km = road.total_length_km
            if length_km is None:
                max_end = (
                    RoadSection.objects.filter(road=road)
                    .aggregate(Max("end_chainage_km"))
                    .get("end_chainage_km__max")
                )
                if max_end is not None:
                    length_km = Decimal(str(max_end))
            if length_km is None:
                length_km = Decimal("0.001")

            road.geometry = _fallback_geometry(length_km)
            road.save(update_fields=["geometry", "total_length_km"])

    def _sync_section_geometry(self) -> None:
        for section in RoadSection.objects.select_related("road").all():
            if not section.road.geometry:
                continue
            try:
                section.save()
            except Exception:
                self.stdout.write(
                    self.style.WARNING(
                        f"Section {section.pk} skipped; geometry/chainage validation failed."
                    )
                )

    def _mock_road_surveys(self, inspection_date) -> None:
        lookups = _ensure_factor_lookups()
        rng = random.Random(inspection_date.toordinal())

        config = SegmentMCIResult._get_active_config(inspection_date)

        for segment in RoadSegment.objects.select_related("section").all():
            seed = segment.id or rng.randint(1, 100000)

            drainage_left = (
                _pick_lookup(lookups["drainage"], seed) if segment.ditch_left_present else None
            )
            drainage_right = (
                _pick_lookup(lookups["drainage"], seed + 1) if segment.ditch_right_present else None
            )
            shoulder_left = (
                _pick_lookup(lookups["shoulder"], seed + 2) if segment.shoulder_left_present else None
            )
            shoulder_right = (
                _pick_lookup(lookups["shoulder"], seed + 3) if segment.shoulder_right_present else None
            )
            surface_condition = _pick_lookup(lookups["surface"], seed + 4)

            survey, _ = RoadConditionSurvey.objects.update_or_create(
                road_segment=segment,
                inspection_date=inspection_date,
                defaults={
                    "drainage_left": drainage_left,
                    "drainage_right": drainage_right,
                    "shoulder_left": shoulder_left,
                    "shoulder_right": shoulder_right,
                    "surface_condition": surface_condition,
                    "gravel_thickness_mm": Decimal("100.0"),
                    "is_there_bottleneck": False,
                    "bottleneck_size_m": None,
                    "comments": "Mock survey",
                    "inspected_by": "Mock Generator",
                },
            )

            if config:
                try:
                    SegmentMCIResult.create_from_survey(survey, config=config)
                except Exception:
                    self.stdout.write(
                        self.style.WARNING(
                            f"MCI result skipped for segment {segment.pk} (missing config or lookup)."
                        )
                    )

    def _mock_structure_surveys(self, inspection_date) -> None:
        qa_status, _ = QAStatus.objects.get_or_create(status="Draft")
        for structure in StructureInventory.objects.select_related("road").all():
            survey, _ = StructureConditionSurvey.objects.update_or_create(
                structure=structure,
                inspection_date=inspection_date,
                defaults={
                    "survey_year": inspection_date.year,
                    "condition_code": 1,
                    "condition_rating": 1,
                    "inspector_name": "Mock Generator",
                    "comments": "Mock structure survey",
                    "qa_status": qa_status,
                },
            )

            if structure.structure_category == "Bridge":
                BridgeConditionSurvey.objects.update_or_create(
                    structure_survey=survey,
                    defaults={
                        "deck_condition": 1,
                        "abutment_condition": 1,
                        "pier_condition": 1,
                        "wearing_surface": 1,
                        "expansion_joint_ok": True,
                        "remarks": "Mock bridge condition",
                    },
                )
            elif structure.structure_category == "Culvert":
                CulvertConditionSurvey.objects.update_or_create(
                    structure_survey=survey,
                    defaults={
                        "inlet_condition": 1,
                        "outlet_condition": 1,
                        "barrel_condition": 1,
                        "headwall_condition": 1,
                        "remarks": "Mock culvert condition",
                    },
                )
            else:
                OtherStructureConditionSurvey.objects.update_or_create(
                    structure_survey=survey,
                    defaults={
                        "wall_condition": 1,
                        "ford_condition": 1,
                        "remarks": "Mock structure condition",
                    },
                )
