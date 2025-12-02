from django.db import migrations
from decimal import Decimal


LINK_TYPES = [
    ("TRUNK", "Trunk Road", Decimal("1.00")),
    ("LINK", "Link Road", Decimal("0.80")),
    ("MAIN", "Main Access Road", Decimal("0.70")),
    ("COLLECT", "Collector Road", Decimal("0.60")),
    ("FEEDER", "Feeder Road", Decimal("0.50")),
]


def add_link_types(apps, schema_editor):
    Lookup = apps.get_model("grms", "RoadLinkTypeLookup")
    for code, name, weight in LINK_TYPES:
        Lookup.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "priority_weight": weight,
                "effective_date": "2024-01-01",
            },
        )


def remove_link_types(apps, schema_editor):
    Lookup = apps.get_model("grms", "RoadLinkTypeLookup")
    Lookup.objects.filter(code__in=[code for code, _, _ in LINK_TYPES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("grms", "0023_benefitcategory_roadlinktypelookup_and_more"),
    ]

    operations = [migrations.RunPython(add_link_types, remove_link_types)]
