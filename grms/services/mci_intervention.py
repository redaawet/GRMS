from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Tuple

from django.db import transaction

from grms.models import (
    InterventionWorkItem,
    RoadSegment,
    SegmentInterventionRecommendation,
    SegmentMCIResult,
)


RECOMMENDED_CODES_LOW = ["01"]
RECOMMENDED_CODES_MEDIUM = ["01", "02"]
RECOMMENDED_CODES_HIGH = ["05"]


def _latest_mci_result(segment: RoadSegment) -> SegmentMCIResult | None:
    return segment.mci_results.order_by("-survey_date", "-computed_at", "-id").first()


def _codes_for_mci(mci_value: Decimal | None) -> list[str]:
    if mci_value is None:
        return []
    if mci_value < Decimal("1.5"):
        return RECOMMENDED_CODES_LOW
    if mci_value <= Decimal("2.5"):
        return RECOMMENDED_CODES_MEDIUM
    return RECOMMENDED_CODES_HIGH


@transaction.atomic
def recommend_intervention_for_segment(segment: RoadSegment) -> int:
    """Recompute recommendations for a single segment based on the latest MCI."""

    mci_result = _latest_mci_result(segment)
    SegmentInterventionRecommendation.objects.filter(segment=segment).delete()

    if mci_result is None:
        return 0

    codes = _codes_for_mci(mci_result.mci_value)
    if not codes:
        return 0

    work_items = InterventionWorkItem.objects.in_bulk(codes, field_name="work_code")

    recommendations = [
        SegmentInterventionRecommendation(
            segment=segment,
            mci_value=mci_result.mci_value,
            recommended_item=work_items[code],
        )
        for code in codes
        if code in work_items
    ]

    SegmentInterventionRecommendation.objects.bulk_create(recommendations)
    return len(recommendations)


def recompute_interventions_for_segments(segments: Iterable[RoadSegment]) -> Tuple[int, int]:
    processed_segments = 0
    created_recommendations = 0

    for segment in segments:
        processed_segments += 1
        created_recommendations += recommend_intervention_for_segment(segment)

    return processed_segments, created_recommendations


def recompute_all_segment_interventions() -> Tuple[int, int]:
    segments = RoadSegment.objects.all().iterator()
    return recompute_interventions_for_segments(segments)
