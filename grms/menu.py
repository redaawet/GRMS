from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Iterable, List, Sequence, Tuple

from django.utils.text import camel_case_to_spaces

MenuTarget = Tuple[str, str]
MenuGroup = OrderedDict[str, List[MenuTarget]]

GROUP_ORDER: Sequence[str] = (
    "Road Network",
    "Structures",
    "Condition",
    "Distress",
    "Traffic",
    "Maintenance & Planning",
    "Reference & Lookups",
    "System",
)

TAIL_WORDS = {
    "detail",
    "details",
    "detailed",
    "survey",
    "surveys",
    "summary",
    "summaries",
    "record",
    "records",
    "result",
    "results",
}


def _normalise(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("_", "").replace(" ", "").strip().lower()


def _split_model_name(model_name: str) -> Iterable[str]:
    return camel_case_to_spaces(model_name).replace("_", " ").split()


def _preferred_label(model) -> str:
    meta = getattr(model, "_meta", None)
    verbose_plural = getattr(meta, "verbose_name_plural", "") if meta else ""
    verbose_single = getattr(meta, "verbose_name", "") if meta else ""
    raw = verbose_plural or verbose_single or camel_case_to_spaces(model.__name__)
    return str(raw).strip().title()


def _clean_label(label: str, had_tail: bool) -> str:
    words = label.split()
    filtered: List[str] = []
    for word in words:
        lower = word.lower()
        if lower == "summaries":
            filtered.append("Summary")
            continue
        if lower in TAIL_WORDS:
            continue
        filtered.append(word)

    if not filtered:
        filtered = words[:1]

    if had_tail and len(filtered) == 1:
        base = filtered[0]
        if not base.endswith("s"):
            filtered[0] = f"{base}s"

    return " ".join(filtered[:2])


def _classify(normalised_name: str, app_label: str) -> str | None:
    road_network = {
        "road",
        "roadsection",
        "roadsegment",
        "roadsocioeconomic",
    }
    structures = {
        "structureinventory",
        "bridgedetail",
        "culvertdetail",
        "forddetail",
        "retainingwalldetail",
        "gabionwalldetail",
        "furnitureinventory",
    }
    condition = {
        "roadconditionsurvey",
        "structureconditionsurvey",
        "bridgeconditionsurvey",
        "culvertconditionsurvey",
        "otherstructureconditionsurvey",
        "furnitureconditionsurvey",
    }
    distress = {
        "roadconditiondetailedsurvey",
        "structureconditiondetailedsurvey",
        "furnitureconditiondetailedsurvey",
        "distresstype",
        "distresscondition",
        "distressactivity",
    }
    traffic = {
        "trafficsurvey",
        "trafficcountrecord",
        "trafficcyclesummary",
        "trafficsurveysummary",
        "trafficsurveyoverall",
        "trafficqc",
        "trafficforprioritization",
        "nightadjustmentlookup",
        "pculookup",
    }
    maintenance_planning = {
        "segmentmciresult",
        "segmentinterventionrecommendation",
        "structureintervention",
        "roadsectionintervention",
        "benefitfactor",
        "prioritizationresult",
        "annualworkplan",
        "mciroadmaintenancerule",
        "mcicategorylookup",
        "mciweightconfig",
        "benefitcategory",
        "benefitcriterion",
        "benefitcriterionscale",
    }
    reference = {
        "activitylookup",
        "interventioncategory",
        "interventionworkitem",
        "interventionlookup",
        "unitcost",
        "conditionfactorlookup",
        "qastatus",
        "roadlinktypelookup",
        "adminzone",
        "adminworeda",
    }
    system = {"user", "group"}

    if normalised_name in road_network:
        return "Road Network"
    if normalised_name in structures:
        return "Structures"
    if normalised_name in condition:
        return "Condition"
    if normalised_name in distress:
        return "Distress"
    if normalised_name in traffic or app_label == "traffic":
        return "Traffic"
    if normalised_name in maintenance_planning:
        return "Maintenance & Planning"
    if normalised_name in reference:
        return "Reference & Lookups"
    if normalised_name in system:
        return "System"
    return "Reference & Lookups"


def build_menu_groups(admin_site) -> MenuGroup:
    groups: Dict[str, List[MenuTarget]] = OrderedDict((title, []) for title in GROUP_ORDER)
    excluded = {admin_site._normalise(name) for name in getattr(admin_site, "EXCLUDED_MODEL_NAMES", [])}

    for model in admin_site._registry:
        meta = getattr(model, "_meta", None)
        if not meta:
            continue
        name_options = {
            _normalise(meta.object_name),
            _normalise(getattr(meta, "model_name", "")),
            _normalise(getattr(meta, "verbose_name", "")),
            _normalise(getattr(meta, "verbose_name_plural", "")),
        }
        if any(value in excluded for value in name_options):
            continue

        normalised = _normalise(meta.object_name)
        group = _classify(normalised, meta.app_label)
        if not group:
            continue

        label = _preferred_label(model)
        has_tail = any(word.lower().rstrip("s") in TAIL_WORDS for word in label.split())
        clean_label = _clean_label(label, has_tail)

        entry = (meta.object_name, clean_label)
        if entry not in groups[group]:
            groups[group].append(entry)

    ordered = OrderedDict()
    for title in GROUP_ORDER:
        items = groups.get(title, [])
        if items:
            ordered[title] = sorted(items, key=lambda pair: pair[1].lower())
    return ordered
