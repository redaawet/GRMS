from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence

from django.db.models import Count, Max, OuterRef, Subquery

from . import models


@dataclass(frozen=True)
class RoadInventoryRow:
    road_identifier: str
    road_name: str
    total_length_km: float
    section_count: int
    segment_count: int


@dataclass(frozen=True)
class StructureInventoryRow:
    road_identifier: str
    section_label: str
    structure_category: str
    structure_name: str
    easting_m: float | None
    northing_m: float | None


@dataclass(frozen=True)
class ConditionSurveyRow:
    road_identifier: str
    section_label: str
    segment_label: str
    inspection_date: date | None
    mci_value: float | None


def road_inventory_rows() -> Sequence[RoadInventoryRow]:
    roads = (
        models.Road.objects.annotate(
            section_count=Count("sections", distinct=True),
            segment_count=Count("sections__segments", distinct=True),
        )
        .order_by("road_identifier")
        .all()
    )
    rows = []
    for road in roads:
        rows.append(
            RoadInventoryRow(
                road_identifier=road.road_identifier,
                road_name=f"{road.road_name_from} – {road.road_name_to}",
                total_length_km=float(road.total_length_km or 0),
                section_count=road.section_count,
                segment_count=road.segment_count,
            )
        )
    return rows


def structure_inventory_rows(road_id: int | None = None) -> Sequence[StructureInventoryRow]:
    structures = models.StructureInventory.objects.select_related("road", "section")
    if road_id:
        structures = structures.filter(road_id=road_id)
    rows = []
    for structure in structures.order_by("road__road_identifier", "structure_category"):
        section_label = str(structure.section) if structure.section_id else ""
        rows.append(
            StructureInventoryRow(
                road_identifier=structure.road.road_identifier,
                section_label=section_label,
                structure_category=structure.structure_category,
                structure_name=structure.structure_name or "",
                easting_m=float(structure.easting_m) if structure.easting_m is not None else None,
                northing_m=float(structure.northing_m) if structure.northing_m is not None else None,
            )
        )
    return rows


def condition_survey_rows(fiscal_year: int | None = None) -> Sequence[ConditionSurveyRow]:
    surveys = models.RoadConditionSurvey.objects.select_related(
        "road_segment__section__road"
    )
    if fiscal_year:
        surveys = surveys.filter(inspection_date__year=fiscal_year)

    latest_survey_subquery = (
        models.RoadConditionSurvey.objects.filter(road_segment=OuterRef("road_segment"))
        .order_by("-inspection_date", "-id")
        .values("id")[:1]
    )

    surveys = surveys.filter(id=Subquery(latest_survey_subquery))

    mci_lookup = (
        models.SegmentMCIResult.objects.filter(survey=OuterRef("pk"))
        .values("mci_value")[:1]
    )

    surveys = surveys.annotate(mci_value=Subquery(mci_lookup))

    rows = []
    for survey in surveys.order_by("road_segment__section__road__road_identifier"):
        segment = survey.road_segment
        rows.append(
            ConditionSurveyRow(
                road_identifier=segment.section.road.road_identifier,
                section_label=str(segment.section),
                segment_label=str(segment),
                inspection_date=survey.inspection_date,
                mci_value=float(survey.mci_value) if survey.mci_value is not None else None,
            )
        )
    return rows
