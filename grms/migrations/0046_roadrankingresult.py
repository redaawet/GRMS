# Generated manually to add RoadRankingResult model
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0045_structure_interventions"),
    ]

    operations = [
        migrations.CreateModel(
            name="RoadRankingResult",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fiscal_year", models.PositiveIntegerField()),
                ("road_class_or_surface_group", models.CharField(max_length=20)),
                ("population_served", models.DecimalField(decimal_places=2, max_digits=15)),
                ("benefit_factor", models.DecimalField(decimal_places=4, max_digits=12)),
                ("cost_of_improvement", models.DecimalField(decimal_places=2, max_digits=15)),
                ("road_index", models.DecimalField(decimal_places=8, max_digits=20)),
                (
                    "rank",
                    models.PositiveIntegerField(help_text="Rank order (1 = highest priority)"),
                ),
                (
                    "road",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="ranking_results",
                        to="grms.road",
                    ),
                ),
            ],
            options={
                "verbose_name": "Road ranking result",
                "verbose_name_plural": "Road ranking results",
                "ordering": ["road_class_or_surface_group", "rank"],
                "unique_together": {("road", "fiscal_year", "road_class_or_surface_group")},
            },
        ),
    ]
