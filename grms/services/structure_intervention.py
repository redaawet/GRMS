"""Structure intervention recommendation services."""

from __future__ import annotations

import logging

from django.db import transaction

from grms import models

logger = logging.getLogger(__name__)

STRUCTURE_TYPE_MAP = {
    "bridge": models.StructureConditionInterventionRule.StructureType.BRIDGE,
    "culvert": models.StructureConditionInterventionRule.StructureType.CULVERT,
    "ford": models.StructureConditionInterventionRule.StructureType.DRIFT,
    "drift": models.StructureConditionInterventionRule.StructureType.DRIFT,
    "vented drift": models.StructureConditionInterventionRule.StructureType.VENTED_DRIFT,
    "vented_drift": models.StructureConditionInterventionRule.StructureType.VENTED_DRIFT,
    "retaining wall": models.StructureConditionInterventionRule.StructureType.OTHER,
    "gabion wall": models.StructureConditionInterventionRule.StructureType.OTHER,
    "other": models.StructureConditionInterventionRule.StructureType.OTHER,
}


def _normalise_structure_category(category: str | None) -> str | None:
    if not category:
        return None
    return category.replace("_", " ").strip().lower()


def _structure_type_for_inventory(structure: models.StructureInventory) -> str:
    normalised = _normalise_structure_category(getattr(structure, "structure_category", ""))
    return STRUCTURE_TYPE_MAP.get(normalised, models.StructureConditionInterventionRule.StructureType.OTHER)


def get_latest_structure_condition(structure: models.StructureInventory) -> int | None:
    """Return the latest available condition code for a structure."""

    latest_survey = structure.surveys.order_by("-inspection_date", "-id").first()
    if latest_survey and latest_survey.condition_code:
        return latest_survey.condition_code
    if latest_survey and latest_survey.condition_rating:
        return latest_survey.condition_rating
    return None


@transaction.atomic
def recommend_intervention_for_structure(structure: models.StructureInventory) -> int:
    """Recompute recommendation for a single structure."""

    structure_type = _structure_type_for_inventory(structure)
    condition_code = get_latest_structure_condition(structure)

    models.StructureInterventionRecommendation.objects.filter(structure=structure).delete()

    if condition_code is None or condition_code == 1:
        return 0

    rule = (
        models.StructureConditionInterventionRule.objects.filter(
            is_active=True, structure_type=structure_type, condition__code=condition_code
        )
        .select_related("intervention_item")
        .first()
    )

    if rule is None:
        logger.warning(
            "No active structure intervention rule for structure %s (type %s, condition %s)",
            structure.id,
            structure_type,
            condition_code,
        )
        return 0

    models.StructureInterventionRecommendation.objects.create(
        structure=structure,
        structure_type=structure_type,
        condition_code=condition_code,
        recommended_item=rule.intervention_item,
    )

    return 1


def recompute_all_structure_interventions() -> tuple[int, int]:
    structures = models.StructureInventory.objects.all().iterator()
    processed = 0
    created = 0

    for structure in structures:
        processed += 1
        created += recommend_intervention_for_structure(structure)

    return processed, created
