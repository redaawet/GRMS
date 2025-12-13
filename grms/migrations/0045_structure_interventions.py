from django.db import migrations, models
import django.db.models.deletion


CONDITIONS = (
    (1, "Good", "No work required"),
    (2, "Fair", "Minor work required"),
    (3, "Poor", "Major work required"),
    (4, "Bad", "In danger of failure / failed"),
)

STRUCTURE_RULES = {
    "bridge": ((2, "105"), (3, "104"), (4, "103")),
    "culvert": ((2, "108"), (3, "107"), (4, "106")),
    "drift": ((4, "109"),),
    "vented_drift": ((4, "110"),),
}


def seed_condition_lookups(apps, schema_editor):
    Condition = apps.get_model("grms", "StructureConditionLookup")

    for code, name, description in CONDITIONS:
        Condition.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": description},
        )


def seed_structure_rules(apps, schema_editor):
    Condition = apps.get_model("grms", "StructureConditionLookup")
    Rule = apps.get_model("grms", "StructureConditionInterventionRule")
    WorkItem = apps.get_model("grms", "InterventionWorkItem")

    conditions = {cond.code: cond for cond in Condition.objects.all()}
    work_items = {
        item.work_code: item
        for item in WorkItem.objects.filter(
            work_code__in={code for rules in STRUCTURE_RULES.values() for _, code in rules}
        )
    }

    for structure_type, rules in STRUCTURE_RULES.items():
        for condition_code, work_code in rules:
            condition = conditions.get(condition_code)
            work_item = work_items.get(work_code)
            if not condition or not work_item:
                continue
            Rule.objects.update_or_create(
                structure_type=structure_type,
                condition=condition,
                defaults={"intervention_item": work_item, "is_active": True},
            )


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0044_update_mci_road_rules"),
    ]

    operations = [
        migrations.CreateModel(
            name="StructureConditionLookup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.PositiveSmallIntegerField(unique=True)),
                ("name", models.CharField(max_length=50)),
                ("description", models.CharField(max_length=200)),
            ],
            options={
                "ordering": ["code"],
                "verbose_name": "Structure condition lookup",
                "verbose_name_plural": "Structure condition lookups",
            },
        ),
        migrations.CreateModel(
            name="StructureConditionInterventionRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "structure_type",
                    models.CharField(
                        choices=[
                            ("bridge", "Bridge"),
                            ("culvert", "Culvert"),
                            ("drift", "Drift"),
                            ("vented_drift", "Vented drift"),
                            ("other", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "condition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="intervention_rules",
                        to="grms.structureconditionlookup",
                    ),
                ),
                (
                    "intervention_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="structure_rules",
                        to="grms.interventionworkitem",
                        to_field="work_code",
                    ),
                ),
            ],
            options={
                "ordering": ["structure_type", "condition__code"],
                "verbose_name": "Structure condition intervention rule",
                "verbose_name_plural": "Structure condition intervention rules",
                "unique_together": {("structure_type", "condition")},
            },
        ),
        migrations.CreateModel(
            name="StructureInterventionRecommendation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "structure_type",
                    models.CharField(
                        choices=[
                            ("bridge", "Bridge"),
                            ("culvert", "Culvert"),
                            ("drift", "Drift"),
                            ("vented_drift", "Vented drift"),
                            ("other", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("condition_code", models.PositiveSmallIntegerField()),
                ("calculated_on", models.DateTimeField(auto_now_add=True)),
                (
                    "recommended_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="structure_recommendations",
                        to="grms.interventionworkitem",
                        to_field="work_code",
                    ),
                ),
                (
                    "structure",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="structure_recommendations",
                        to="grms.structureinventory",
                    ),
                ),
            ],
            options={
                "ordering": ["structure_type", "recommended_item__work_code"],
                "verbose_name": "Structure intervention recommendation",
                "verbose_name_plural": "Structure intervention recommendations",
                "unique_together": {("structure", "recommended_item")},
            },
        ),
        migrations.RunPython(seed_condition_lookups, migrations.RunPython.noop),
        migrations.RunPython(seed_structure_rules, migrations.RunPython.noop),
    ]
