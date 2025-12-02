from decimal import Decimal

from django.db import migrations


BENEFIT_DATA = [
    {
        "code": "BF1",
        "name": "Transportation and Connectivity",
        "weight": Decimal("0.40"),
        "criteria": [
            {
                "code": "ADT",
                "name": "Traffic (vehicles per day)",
                "weight": Decimal("1"),
                "scales": [
                    {"min": None, "max": Decimal("24.999"), "score": Decimal("2")},
                    {"min": Decimal("25"), "max": Decimal("50"), "score": Decimal("3")},
                    {"min": Decimal("50.001"), "max": None, "score": Decimal("5")},
                ],
            },
            {
                "code": "TC",
                "name": "Number of trading centers along the road",
                "weight": Decimal("1"),
                "scales": [
                    {"min": None, "max": Decimal("4.999"), "score": Decimal("1")},
                    {"min": Decimal("5"), "max": Decimal("10"), "score": Decimal("2")},
                    {"min": Decimal("10.001"), "max": None, "score": Decimal("3")},
                ],
            },
            {
                "code": "VC",
                "name": "Number of kebeles/villages/communities connected by the road",
                "weight": Decimal("1"),
                "scales": [
                    {"min": None, "max": Decimal("9.999"), "score": Decimal("5")},
                    {"min": Decimal("10"), "max": Decimal("20"), "score": Decimal("10")},
                    {"min": Decimal("20.001"), "max": None, "score": Decimal("15")},
                ],
            },
            {
                "code": "LT",
                "name": "Termination or origination point of the road",
                "weight": Decimal("1"),
                "scales": [
                    {"min": Decimal("0.9"), "max": None, "score": Decimal("2")},
                    {"min": None, "max": Decimal("0.899"), "score": Decimal("1")},
                ],
            },
        ],
    },
    {
        "code": "BF2",
        "name": "Agriculture and Market Access",
        "weight": Decimal("0.30"),
        "criteria": [
            {
                "code": "FARMLAND",
                "name": "Road traverses through farmland (percent of alignment)",
                "weight": Decimal("1"),
                "scales": [
                    {"min": None, "max": Decimal("19.999"), "score": Decimal("0")},
                    {"min": Decimal("20"), "max": Decimal("50"), "score": Decimal("2")},
                    {"min": Decimal("50.001"), "max": None, "score": Decimal("4")},
                ],
            },
            {
                "code": "COOP",
                "name": "Number of cooperative centres along the road",
                "weight": Decimal("1"),
                "scales": [
                    {"min": None, "max": Decimal("4.999"), "score": Decimal("1")},
                    {"min": Decimal("5"), "max": Decimal("10"), "score": Decimal("2")},
                    {"min": Decimal("10.001"), "max": None, "score": Decimal("3")},
                ],
            },
            {
                "code": "MARKET",
                "name": "Number of markets connected by the road",
                "weight": Decimal("1"),
                "scales": [
                    {"min": None, "max": Decimal("1.999"), "score": Decimal("1")},
                    {"min": Decimal("2"), "max": Decimal("5"), "score": Decimal("2")},
                    {"min": Decimal("5.001"), "max": None, "score": Decimal("3")},
                ],
            },
        ],
    },
    {
        "code": "BF3",
        "name": "Education, Health and Community Development Projects",
        "weight": Decimal("0.30"),
        "criteria": [
            {
                "code": "HEALTH",
                "name": "Number of health centres connected by the road",
                "weight": Decimal("1"),
                "scales": [
                    {"min": None, "max": Decimal("1.999"), "score": Decimal("2")},
                    {"min": Decimal("2"), "max": Decimal("4"), "score": Decimal("3")},
                    {"min": Decimal("4.001"), "max": None, "score": Decimal("5")},
                ],
            },
            {
                "code": "EDU",
                "name": "Number of education centres/schools connected by the road",
                "weight": Decimal("1"),
                "scales": [
                    {"min": None, "max": Decimal("4.999"), "score": Decimal("2")},
                    {"min": Decimal("5"), "max": Decimal("8"), "score": Decimal("3")},
                    {"min": Decimal("8.001"), "max": None, "score": Decimal("5")},
                ],
            },
            {
                "code": "DEV",
                "name": "Number of other ongoing development projects connected by the road",
                "weight": Decimal("1"),
                "scales": [
                    {"min": None, "max": Decimal("4.999"), "score": Decimal("2")},
                    {"min": Decimal("5"), "max": Decimal("8"), "score": Decimal("4")},
                    {"min": Decimal("8.001"), "max": None, "score": Decimal("5")},
                ],
            },
        ],
    },
]


def _get_or_create_category(models, definition):
    Category = models["Category"]
    category, _ = Category.objects.get_or_create(
        code=definition["code"],
        defaults={"name": definition["name"], "weight": definition["weight"]},
    )
    return category


def _get_or_create_criterion(models, category, definition):
    Criterion = models["Criterion"]
    criterion, _ = Criterion.objects.get_or_create(
        code=definition["code"],
        defaults={
            "name": definition["name"],
            "weight": definition["weight"],
            "category": category,
        },
    )
    return criterion


def _get_or_create_scale(models, criterion, definition):
    Scale = models["Scale"]
    Scale.objects.get_or_create(
        criterion=criterion,
        min_value=definition["min"],
        max_value=definition["max"],
        score=definition["score"],
        defaults={"notes": "Seeded from SRAD benefit scoring table"},
    )


def populate_benefit_tables(apps, schema_editor):
    models = {
        "Category": apps.get_model("grms", "BenefitCategory"),
        "Criterion": apps.get_model("grms", "BenefitCriterion"),
        "Scale": apps.get_model("grms", "BenefitCriterionScale"),
    }

    for category_def in BENEFIT_DATA:
        category = _get_or_create_category(models, category_def)
        for criterion_def in category_def["criteria"]:
            criterion = _get_or_create_criterion(models, category, criterion_def)
            for scale_def in criterion_def["scales"]:
                _get_or_create_scale(models, criterion, scale_def)


def remove_seeded_benefit_tables(apps, schema_editor):
    Category = apps.get_model("grms", "BenefitCategory")
    Criterion = apps.get_model("grms", "BenefitCriterion")
    Scale = apps.get_model("grms", "BenefitCriterionScale")

    criterion_codes = [c["code"] for cat in BENEFIT_DATA for c in cat["criteria"]]
    Scale.objects.filter(criterion__code__in=criterion_codes).delete()
    Criterion.objects.filter(code__in=criterion_codes).delete()
    Category.objects.filter(code__in={definition["code"] for definition in BENEFIT_DATA}).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("grms", "0025_alter_roadsocioeconomic_options_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_benefit_tables, remove_seeded_benefit_tables),
    ]
