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

MODEL_GROUP_MAP: Dict[str, str] = {
    # Road Network
    "road": "Road Network",
    "roadsection": "Road Network",
    "roadsegment": "Road Network",
    "roadsocioeconomic": "Road Network",
    # Structures
    "structureinventory": "Structures",
    "bridgedetail": "Structures",
    "culvertdetail": "Structures",
    "forddetail": "Structures",
    "retainingwalldetail": "Structures",
    "gabionwalldetail": "Structures",
    "furnitureinventory": "Structures",
    # Condition
    "roadconditionsurvey": "Condition",
    "structureconditionsurvey": "Condition",
    "bridgeconditionsurvey": "Condition",
    "culvertconditionsurvey": "Condition",
    "otherstructureconditionsurvey": "Condition",
    "furnitureconditionsurvey": "Condition",
    # Distress
    "roadconditiondetailedsurvey": "Distress",
    "structureconditiondetailedsurvey": "Distress",
    "furnitureconditiondetailedsurvey": "Distress",
    # Traffic
    "trafficsurvey": "Traffic",
    "trafficcountrecord": "Traffic",
    "trafficcyclesummary": "Traffic",
    "trafficsurveysummary": "Traffic",
    "trafficsurveyoverall": "Traffic",
    "trafficqc": "Traffic",
    "nightadjustmentlookup": "Traffic",
    "pculookup": "Traffic",
    "trafficforprioritization": "Traffic",
    # Maintenance & Planning
    "segmentmciresult": "Maintenance & Planning",
    "mciroadmaintenancerule": "Maintenance & Planning",
    "segmentinterventionrecommendation": "Maintenance & Planning",
    "structureconditionlookup": "Maintenance & Planning",
    "structureconditioninterventionrule": "Maintenance & Planning",
    "roadsectionintervention": "Maintenance & Planning",
    "structureintervention": "Maintenance & Planning",
    "benefitcategory": "Maintenance & Planning",
    "benefitcriterion": "Maintenance & Planning",
    "benefitcriterionscale": "Maintenance & Planning",
    "benefitfactor": "Maintenance & Planning",
    "prioritizationresult": "Maintenance & Planning",
    "annualworkplan": "Maintenance & Planning",
    # Reference & Lookups
    "activitylookup": "Reference & Lookups",
    "interventioncategory": "Reference & Lookups",
    "interventionworkitem": "Reference & Lookups",
    "interventionlookup": "Reference & Lookups",
    "unitcost": "Reference & Lookups",
    "conditionfactorlookup": "Reference & Lookups",
    "mciweightconfig": "Reference & Lookups",
    "mcicategorylookup": "Reference & Lookups",
    "distresstype": "Reference & Lookups",
    "distresscondition": "Reference & Lookups",
    "distressactivity": "Reference & Lookups",
    "roadlinktypelookup": "Reference & Lookups",
    "adminzone": "Reference & Lookups",
    "adminworeda": "Reference & Lookups",
    "qastatus": "Reference & Lookups",
    # System
    "user": "System",
    "group": "System",
}

LABEL_OVERRIDES: Dict[str, str] = {
    "road": "Roads",
    "roadsection": "Sections",
    "roadsegment": "Segments",
    "roadsocioeconomic": "Socioeconomic",
    "structureinventory": "Structures",
    "bridgedetail": "Bridges",
    "culvertdetail": "Culverts",
    "forddetail": "Fords",
    "retainingwalldetail": "Retaining walls",
    "gabionwalldetail": "Gabion walls",
    "furnitureinventory": "Furniture",
    "roadconditionsurvey": "Road condition",
    "structureconditionsurvey": "Structure condition",
    "bridgeconditionsurvey": "Bridge condition",
    "culvertconditionsurvey": "Culvert condition",
    "otherstructureconditionsurvey": "Other structures",
    "furnitureconditionsurvey": "Furniture condition",
    "roadconditiondetailedsurvey": "Road distress",
    "structureconditiondetailedsurvey": "Structure distress",
    "furnitureconditiondetailedsurvey": "Furniture distress",
    "trafficsurvey": "Traffic survey",
    "trafficcountrecord": "Traffic count",
    "trafficcyclesummary": "Traffic cycle",
    "trafficsurveysummary": "Traffic summary",
    "trafficsurveyoverall": "Traffic overall",
    "trafficqc": "Traffic QC",
    "nightadjustmentlookup": "Night adjust",
    "pculookup": "PCU lookup",
    "trafficforprioritization": "Traffic priority",
    "segmentmciresult": "Segment MCI",
    "mciroadmaintenancerule": "MCI rules",
    "segmentinterventionrecommendation": "Segment plans",
    "structureconditionlookup": "Structure condition codes",
    "structureconditioninterventionrule": "Structure intervention rules",
    "roadsectionintervention": "Section interventions",
    "structureintervention": "Structure interventions",
    "benefitcategory": "Benefit categories",
    "benefitcriterion": "Benefit criteria",
    "benefitcriterionscale": "Criterion scale",
    "benefitfactor": "Benefit factors",
    "prioritizationresult": "Priority results",
    "annualworkplan": "Work plan",
    "activitylookup": "Activities",
    "interventioncategory": "Intervention categories",
    "interventionworkitem": "Work items",
    "interventionlookup": "Interventions",
    "unitcost": "Unit costs",
    "conditionfactorlookup": "Condition factors",
    "mciweightconfig": "MCI weights",
    "mcicategorylookup": "MCI categories",
    "distresstype": "Distress types",
    "distresscondition": "Distress conditions",
    "distressactivity": "Distress actions",
    "roadlinktypelookup": "Road links",
    "adminzone": "Zones",
    "adminworeda": "Woredas",
    "qastatus": "QA status",
}

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


def _classify(normalised_name: str, app_label: str) -> str:
    if normalised_name in MODEL_GROUP_MAP:
        return MODEL_GROUP_MAP[normalised_name]
    if app_label == "traffic":
        return "Traffic"
    if app_label == "auth":
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

        label = LABEL_OVERRIDES.get(normalised)
        if not label:
            raw_label = _preferred_label(model)
            has_tail = any(
                word.lower().rstrip("s") in TAIL_WORDS for word in raw_label.split()
            )
            label = _clean_label(raw_label, has_tail)

        entry = (meta.object_name, label)
        if entry not in groups[group]:
            groups[group].append(entry)

    ordered = OrderedDict()
    for title in GROUP_ORDER:
        items = groups.get(title, [])
        if items:
            ordered[title] = sorted(items, key=lambda pair: pair[1].lower())
    return ordered
