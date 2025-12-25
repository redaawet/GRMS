from __future__ import annotations

from django.core.exceptions import ValidationError


def validate_section_belongs_to_road(road, section) -> None:
    if road and section and section.road_id != road.id:
        raise ValidationError(
            {"section": "Selected section does not belong to the selected road."}
        )


def validate_segment_belongs_to_section(section, segment, *, field: str = "road_segment") -> None:
    if section and segment and segment.section_id != section.id:
        raise ValidationError(
            {field: "Selected segment does not belong to the selected section."}
        )


def validate_segment_belongs_to_road(road, segment, *, field: str = "road_segment") -> None:
    if road and segment and segment.section.road_id != road.id:
        raise ValidationError(
            {field: "Selected segment does not belong to the selected road."}
        )
