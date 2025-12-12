from __future__ import annotations

import logging
from typing import Iterable

from django.db import transaction

from grms.models import (
    InterventionWorkItem,
    MCIRoadMaintenanceRule,
    RoadSegment,
    SegmentInterventionRecommendation,
    SegmentMCIResult,
)


BOTTLENECK_ROAD_CODES = ["101", "102"]

logger = logging.getLogger(__name__)


def _latest_mci_result(segment: RoadSegment) -> SegmentMCIResult | None:
    return segment.mci_results.order_by("-survey_date", "-computed_at", "-id").first()


def _codes_for_rule(rule: MCIRoadMaintenanceRule | None) -> list[str]:
    if not rule:
        return []

    codes: list[str] = []
    if rule.routine:
        codes.append("01")
    if rule.periodic:
        codes.append("02")
    if rule.rehabilitation:
        codes.append("05")
    return codes


def _segment_has_bottleneck(segment: RoadSegment) -> bool:
    has_method = getattr(segment, "has_road_bottleneck", None)
    return bool(has_method()) if callable(has_method) else False


@transaction.atomic
def recommend_intervention_for_segment(segment: RoadSegment) -> int:
    """Recompute recommendations for a single segment based on the latest MCI."""

    mci_result = _latest_mci_result(segment)
    SegmentInterventionRecommendation.objects.filter(segment=segment).delete()

    if mci_result is None or mci_result.mci_value is None:
        return 0

    rule = MCIRoadMaintenanceRule.match_for_mci(mci_result.mci_value)
    if rule is None:
        message = (
            "No active MCI road maintenance rule matches segment "
            f"{segment.id} (MCI {mci_result.mci_value})."
        )
        logger.warning(message)
        raise ValueError(message)

    base_codes = _codes_for_rule(rule)
    if not base_codes:
        message = (
            "Matched MCI road maintenance rule for segment "
            f"{segment.id} but it defines no work codes."
        )
        logger.warning(message)
        raise ValueError(message)

    if "05" in base_codes:
        final_codes = ["05"]
    else:
        final_codes = list(base_codes)
        if _segment_has_bottleneck(segment):
            for code in BOTTLENECK_ROAD_CODES:
                if code not in final_codes:
                    final_codes.append(code)

    work_items = InterventionWorkItem.objects.in_bulk(final_codes, field_name="work_code")

    recommendations = [
        SegmentInterventionRecommendation(
            segment=segment,
            mci_value=mci_result.mci_value,
            recommended_item=work_items[code],
        )
        for code in final_codes
        if code in work_items
    ]

    SegmentInterventionRecommendation.objects.bulk_create(recommendations)
    return len(recommendations)


def recompute_interventions_for_segments(segments: Iterable[RoadSegment]) -> tuple[int, int]:
    processed_segments = 0
    created_recommendations = 0

    for segment in segments:
        processed_segments += 1
        created_recommendations += recommend_intervention_for_segment(segment)

    return processed_segments, created_recommendations


def recompute_all_segment_interventions() -> tuple[int, int]:
    segments = RoadSegment.objects.all().iterator()
    return recompute_interventions_for_segments(segments)
