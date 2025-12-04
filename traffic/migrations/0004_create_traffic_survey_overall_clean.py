from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0022_add_road_identifier"),
        ("traffic", "0003_rename_final_value_trafficforprioritization_value_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TrafficSurveyOverall",
            fields=[
                ("overall_id", models.BigAutoField(primary_key=True)),
                ("fiscal_year", models.IntegerField()),
                ("adt_total", models.DecimalField(max_digits=14, decimal_places=3)),
                ("pcu_total", models.DecimalField(max_digits=14, decimal_places=3)),
                ("confidence_score", models.DecimalField(max_digits=5, decimal_places=2)),
                ("computed_at", models.DateTimeField(auto_now=True)),
                (
                    "road",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="grms.road",
                    ),
                ),
            ],
            options={
                "db_table": "traffic_survey_overall",
                "unique_together": {("road", "fiscal_year")},
            },
        ),
    ]
