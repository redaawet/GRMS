from __future__ import annotations

from decimal import Decimal

from django.db import migrations

ROAD_LINK_TYPES = [
    {"name": "Trunk Road", "code": "A", "score": 12},
    {"name": "Link Road", "code": "B", "score": 8},
    {"name": "Main Access Road", "code": "C", "score": 5},
    {"name": "Collector Road", "code": "D", "score": 3},
    {"name": "Feeder Road", "code": "E", "score": 2},
]

BENEFIT_DEFINITION = {
    "BF1": {
        "weight": Decimal("40"),
        "criteria": {
            "ADT": {
                "weight": Decimal("12"),
                "scales": [
                {"min": Decimal("0"), "max": Decimal("24.99"), "score": 5},
                {"min": Decimal("25"), "max": Decimal("50"), "score": 8},
                {"min": Decimal("50.01"), "max": None, "score": 12},
                ],
            },
            "Trading Centers": {
                "weight": Decimal("8"),
                "scales": [
                {"min": Decimal("0"), "max": Decimal("24.99"), "score": 5},
                {"min": Decimal("25"), "max": Decimal("50"), "score": 8},
                {"min": Decimal("50.01"), "max": None, "score": 12},
                ],
            },
            "Villages": {
                "weight": Decimal("8"),
                "scales": [
                {"min": Decimal("0"), "max": Decimal("24.99"), "score": 5},
                {"min": Decimal("25"), "max": Decimal("50"), "score": 8},
                {"min": Decimal("50.01"), "max": None, "score": 12},
                ],
            },
            "Road Link Type": {"weight": Decimal("12"), "scales": []},
        },
    },
    "BF2": {
        "weight": Decimal("30"),
        "criteria": {
            "Farmland %": {
                "weight": Decimal("10"),
                "scales": [
                {"min": Decimal("0"), "max": Decimal("24.99"), "score": 5},
                {"min": Decimal("25"), "max": Decimal("50"), "score": 8},
                {"min": Decimal("50.01"), "max": None, "score": 12},
                ],
            },
            "Cooperative Centers": {
                "weight": Decimal("10"),
                "scales": [
                {"min": Decimal("0"), "max": Decimal("24.99"), "score": 5},
                {"min": Decimal("25"), "max": Decimal("50"), "score": 8},
                {"min": Decimal("50.01"), "max": None, "score": 12},
                ],
            },
            "Markets": {
                "weight": Decimal("10"),
                "scales": [
                {"min": Decimal("0"), "max": Decimal("24.99"), "score": 5},
                {"min": Decimal("25"), "max": Decimal("50"), "score": 8},
                {"min": Decimal("50.01"), "max": None, "score": 12},
                ],
            },
        },
    },
    "BF3": {
        "weight": Decimal("30"),
        "criteria": {
            "Health Centers": {
                "weight": Decimal("12"),
                "scales": [
                {"min": Decimal("0"), "max": Decimal("24.99"), "score": 5},
                {"min": Decimal("25"), "max": Decimal("50"), "score": 8},
                {"min": Decimal("50.01"), "max": None, "score": 12},
                ],
            },
            "Education Centers": {
                "weight": Decimal("12"),
                "scales": [
                {"min": Decimal("0"), "max": Decimal("24.99"), "score": 5},
                {"min": Decimal("25"), "max": Decimal("50"), "score": 8},
                {"min": Decimal("50.01"), "max": None, "score": 12},
                ],
            },
            "Development Projects": {
                "weight": Decimal("6"),
                "scales": [
                {"min": Decimal("0"), "max": Decimal("24.99"), "score": 5},
                {"min": Decimal("25"), "max": Decimal("50"), "score": 8},
                {"min": Decimal("50.01"), "max": None, "score": 12},
                ],
            },
        },
    },
}


def seed_link_types(apps, schema_editor):
    Lookup = apps.get_model("grms", "RoadLinkTypeLookup")
    for definition in ROAD_LINK_TYPES:
        Lookup.objects.update_or_create(code=definition["code"], defaults=definition)


def seed_benefit_lookups(apps, schema_editor):
    Category = apps.get_model("grms", "BenefitCategory")
    Criterion = apps.get_model("grms", "BenefitCriterion")
    Scale = apps.get_model("grms", "BenefitCriterionScale")

    for name, details in BENEFIT_DEFINITION.items():
        category, _ = Category.objects.update_or_create(
            name=name, defaults={"weight_percent": details["weight"]}
        )
        for criterion_name, entry in details["criteria"].items():
            criterion, _ = Criterion.objects.update_or_create(
                category=category,
                name=criterion_name,
                defaults={"weight_percent": entry.get("weight", Decimal("0"))},
            )
            scales = entry.get("scales", [])
            if criterion_name == "Road Link Type":
                Scale.objects.filter(criterion=criterion).delete()
                continue
            for scale_def in scales:
                Scale.objects.update_or_create(
                    criterion=criterion,
                    min_value=scale_def["min"],
                    max_value=scale_def["max"],
                    defaults={"score": scale_def["score"]},
                )


def remove_seeded_data(apps, schema_editor):
    Category = apps.get_model("grms", "BenefitCategory")
    Criterion = apps.get_model("grms", "BenefitCriterion")
    Scale = apps.get_model("grms", "BenefitCriterionScale")
    Lookup = apps.get_model("grms", "RoadLinkTypeLookup")

    Scale.objects.filter(criterion__name__in={name for c in BENEFIT_DEFINITION.values() for name in c["criteria"].keys()}).delete()
    Criterion.objects.filter(name__in={name for c in BENEFIT_DEFINITION.values() for name in c["criteria"].keys()}).delete()
    Category.objects.filter(name__in=BENEFIT_DEFINITION.keys()).delete()
    Lookup.objects.filter(code__in=[item["code"] for item in ROAD_LINK_TYPES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("grms", "0027_alter_benefitcategory_options_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_link_types, remove_seeded_data),
        migrations.RunPython(seed_benefit_lookups, remove_seeded_data),
    ]
