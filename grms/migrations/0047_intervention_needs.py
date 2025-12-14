from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0046_roadrankingresult"),
    ]

    operations = [
        migrations.CreateModel(
            name="SegmentInterventionNeed",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fiscal_year", models.PositiveIntegerField(help_text="Fiscal year for which the need is recorded")),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "segment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="intervention_needs",
                        to="grms.roadsegment",
                    ),
                ),
            ],
            options={
                "verbose_name": "Segment intervention need",
                "verbose_name_plural": "Segment intervention needs",
                "unique_together": {("segment", "fiscal_year")},
            },
        ),
        migrations.CreateModel(
            name="StructureInterventionNeed",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fiscal_year", models.PositiveIntegerField(help_text="Fiscal year for which the need is recorded")),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "structure",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="intervention_needs",
                        to="grms.structureinventory",
                    ),
                ),
            ],
            options={
                "verbose_name": "Structure intervention need",
                "verbose_name_plural": "Structure intervention needs",
                "unique_together": {("structure", "fiscal_year")},
            },
        ),
        migrations.CreateModel(
            name="SegmentInterventionNeedItem",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notes", models.TextField(blank=True)),
                (
                    "intervention_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="segment_need_items",
                        to="grms.interventionworkitem",
                    ),
                ),
                (
                    "need",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="grms.segmentinterventionneed",
                    ),
                ),
            ],
            options={
                "verbose_name": "Segment intervention need item",
                "verbose_name_plural": "Segment intervention need items",
            },
        ),
        migrations.CreateModel(
            name="StructureInterventionNeedItem",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notes", models.TextField(blank=True)),
                (
                    "intervention_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="structure_need_items",
                        to="grms.interventionworkitem",
                    ),
                ),
                (
                    "need",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="grms.structureinterventionneed",
                    ),
                ),
            ],
            options={
                "verbose_name": "Structure intervention need item",
                "verbose_name_plural": "Structure intervention need items",
            },
        ),
    ]
