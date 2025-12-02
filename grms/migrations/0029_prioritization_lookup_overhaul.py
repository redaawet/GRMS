from decimal import Decimal

from django.db import migrations, models


CATEGORY_DEFINITION = [
    {"code": "BF1", "name": "Transportation & Connectivity", "weight": Decimal("0.40")},
    {"code": "BF2", "name": "Agriculture & Market Access", "weight": Decimal("0.30")},
    {"code": "BF3", "name": "Education, Health, Development", "weight": Decimal("0.30")},
]

CRITERIA_DEFINITION = [
    {"code": "TRAFFIC", "name": "Traffic (vehicles/day)", "weight": Decimal("0.12"), "scoring_method": "RANGE"},
    {"code": "TRADE_CTR", "name": "Trading centers", "weight": Decimal("0.08"), "scoring_method": "RANGE"},
    {"code": "VILLAGES", "name": "Kebelles/villages", "weight": Decimal("0.08"), "scoring_method": "RANGE"},
    {"code": "LINK_TYPE", "name": "Road link type", "weight": Decimal("0.12"), "scoring_method": "LOOKUP"},
    {"code": "FARMLAND", "name": "Farmland %", "weight": Decimal("0.10"), "scoring_method": "RANGE"},
    {"code": "COOPS", "name": "Cooperative centers", "weight": Decimal("0.10"), "scoring_method": "RANGE"},
    {"code": "MARKETS", "name": "Markets connected", "weight": Decimal("0.10"), "scoring_method": "RANGE"},
    {"code": "HEALTH", "name": "Health centers", "weight": Decimal("0.12"), "scoring_method": "RANGE"},
    {"code": "EDUCATION", "name": "Education centers", "weight": Decimal("0.12"), "scoring_method": "RANGE"},
    {"code": "PROJECTS", "name": "Development projects", "weight": Decimal("0.06"), "scoring_method": "RANGE"},
]


SCALE_DEFINITION = {
    "TRAFFIC": [
        {"min": None, "max": Decimal("24.99"), "score": 5, "description": "<25"},
        {"min": Decimal("25"), "max": Decimal("50"), "score": 8, "description": "25-50"},
        {"min": Decimal("50.01"), "max": None, "score": 12, "description": ">50"},
    ],
    "TRADE_CTR": [
        {"min": None, "max": Decimal("4.99"), "score": 3, "description": "<5"},
        {"min": Decimal("5"), "max": Decimal("10"), "score": 5, "description": "5-10"},
        {"min": Decimal("10.01"), "max": None, "score": 8, "description": ">10"},
    ],
    "VILLAGES": [
        {"min": None, "max": Decimal("9.99"), "score": 3, "description": "<10"},
        {"min": Decimal("10"), "max": Decimal("20"), "score": 5, "description": "10-20"},
        {"min": Decimal("20.01"), "max": None, "score": 8, "description": ">20"},
    ],
    "FARMLAND": [
        {"min": None, "max": Decimal("19.99"), "score": 3, "description": "<20%"},
        {"min": Decimal("20"), "max": Decimal("50"), "score": 5, "description": "20-50%"},
        {"min": Decimal("50.01"), "max": None, "score": 8, "description": ">50%"},
    ],
    "COOPS": [
        {"min": None, "max": Decimal("4.99"), "score": 3, "description": "<5"},
        {"min": Decimal("5"), "max": Decimal("10"), "score": 5, "description": "5-10"},
        {"min": Decimal("10.01"), "max": None, "score": 8, "description": ">10"},
    ],
    "MARKETS": [
        {"min": None, "max": Decimal("1.99"), "score": 3, "description": "<2"},
        {"min": Decimal("2"), "max": Decimal("5"), "score": 5, "description": "2-5"},
        {"min": Decimal("5.01"), "max": None, "score": 8, "description": ">5"},
    ],
    "HEALTH": [
        {"min": None, "max": Decimal("1.99"), "score": 3, "description": "<2"},
        {"min": Decimal("2"), "max": Decimal("4"), "score": 5, "description": "2-4"},
        {"min": Decimal("4.01"), "max": None, "score": 8, "description": ">4"},
    ],
    "EDUCATION": [
        {"min": None, "max": Decimal("4.99"), "score": 3, "description": "<5"},
        {"min": Decimal("5"), "max": Decimal("8"), "score": 5, "description": "5-8"},
        {"min": Decimal("8.01"), "max": None, "score": 8, "description": ">8"},
    ],
    "PROJECTS": [
        {"min": None, "max": Decimal("4.99"), "score": 3, "description": "<5"},
        {"min": Decimal("5"), "max": Decimal("8"), "score": 5, "description": "5-8"},
        {"min": Decimal("8.01"), "max": None, "score": 8, "description": ">8"},
    ],
}

ROAD_LINK_TYPES = [
    {"name": "Trunk Road", "code": "TRUNK", "score": 12},
    {"name": "Link Road", "code": "LINK", "score": 8},
    {"name": "Main Access Road", "code": "MAIN", "score": 5},
    {"name": "Collector Road", "code": "COLLECT", "score": 3},
    {"name": "Feeder Road", "code": "FEEDER", "score": 2},
]


CRITERIA_BY_CATEGORY = {
    "BF1": ["TRAFFIC", "TRADE_CTR", "VILLAGES", "LINK_TYPE"],
    "BF2": ["FARMLAND", "COOPS", "MARKETS"],
    "BF3": ["HEALTH", "EDUCATION", "PROJECTS"],
}


def seed_lookups(apps, schema_editor):
    Category = apps.get_model("grms", "BenefitCategory")
    Criterion = apps.get_model("grms", "BenefitCriterion")
    Scale = apps.get_model("grms", "BenefitCriterionScale")
    LinkType = apps.get_model("grms", "RoadLinkTypeLookup")

    Scale.objects.all().delete()
    Criterion.objects.all().delete()
    Category.objects.all().delete()

    for definition in ROAD_LINK_TYPES:
        LinkType.objects.update_or_create(name=definition["name"], defaults=definition)

    categories = {}
    for entry in CATEGORY_DEFINITION:
        category = Category.objects.create(code=entry["code"], name=entry["name"], weight=entry["weight"])
        categories[entry["code"]] = category

    criteria_lookup = {item["code"]: item for item in CRITERIA_DEFINITION}
    for category_code, criterion_codes in CRITERIA_BY_CATEGORY.items():
        category = categories[category_code]
        for code in criterion_codes:
            definition = criteria_lookup[code]
            criterion = Criterion.objects.create(
                category=category,
                code=definition["code"],
                name=definition["name"],
                weight=definition["weight"],
                scoring_method=definition["scoring_method"],
            )
            for scale_def in SCALE_DEFINITION.get(code, []):
                Scale.objects.create(
                    criterion=criterion,
                    min_value=scale_def["min"],
                    max_value=scale_def["max"],
                    score=scale_def["score"],
                    description=scale_def["description"],
                )


def unseed_lookups(apps, schema_editor):
    Category = apps.get_model("grms", "BenefitCategory")
    Criterion = apps.get_model("grms", "BenefitCriterion")
    Scale = apps.get_model("grms", "BenefitCriterionScale")

    Scale.objects.all().delete()
    Criterion.objects.all().delete()
    Category.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0028_seed_benefit_and_link_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="benefitcategory",
            name="code",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="benefitcategory",
            name="weight",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name="benefitcriterion",
            name="code",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="benefitcriterion",
            name="scoring_method",
            field=models.CharField(blank=True, choices=[("RANGE", "Range"), ("LOOKUP", "Lookup")], max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="benefitcriterion",
            name="weight",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name="benefitcriterionscale",
            name="description",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AlterField(
            model_name="benefitcriterionscale",
            name="min_value",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name="benefitcriterionscale",
            name="max_value",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name="roadlinktypelookup",
            name="code",
            field=models.CharField(max_length=10, unique=True),
        ),
        migrations.RunPython(seed_lookups, unseed_lookups),
        migrations.AlterField(
            model_name="benefitcategory",
            name="code",
            field=models.CharField(max_length=10, unique=True),
        ),
        migrations.AlterField(
            model_name="benefitcategory",
            name="weight",
            field=models.DecimalField(decimal_places=2, max_digits=4),
        ),
        migrations.AlterField(
            model_name="benefitcriterion",
            name="code",
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name="benefitcriterion",
            name="scoring_method",
            field=models.CharField(choices=[("RANGE", "Range"), ("LOOKUP", "Lookup")], max_length=10),
        ),
        migrations.AlterField(
            model_name="benefitcriterion",
            name="weight",
            field=models.DecimalField(decimal_places=2, max_digits=4),
        ),
        migrations.AlterUniqueTogether(
            name="benefitcriterion",
            unique_together={("category", "code")},
        ),
        migrations.RemoveField(
            model_name="benefitcategory",
            name="weight_percent",
        ),
        migrations.RemoveField(
            model_name="benefitcriterion",
            name="weight_percent",
        ),
    ]
