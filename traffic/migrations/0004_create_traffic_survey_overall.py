from django.db import migrations, models
import django.db.models.deletion


DELETE_DUPLICATE_SUMMARIES = """
DELETE FROM traffic_survey_summary t
USING (
    SELECT road_id, vehicle_class, fiscal_year, MIN(survey_summary_id) AS keep_id
    FROM traffic_survey_summary
    GROUP BY road_id, vehicle_class, fiscal_year
    HAVING COUNT(*) > 1
) d
WHERE t.road_id = d.road_id
  AND t.vehicle_class = d.vehicle_class
  AND t.fiscal_year = d.fiscal_year
  AND t.survey_summary_id <> d.keep_id;
"""

POPULATE_OVERALL_SQL = """
INSERT INTO traffic_survey_overall (road_id, fiscal_year, adt_total, pcu_total, confidence_score, computed_at)
SELECT
    road_id,
    fiscal_year,
    SUM(adt_final) AS adt_total,
    SUM(pcu_final) AS pcu_total,
    AVG(confidence_score) AS confidence_score,
    NOW() AS computed_at
FROM traffic_survey_summary
GROUP BY road_id, fiscal_year
ON CONFLICT (road_id, fiscal_year)
DO UPDATE SET
    adt_total = EXCLUDED.adt_total,
    pcu_total = EXCLUDED.pcu_total,
    confidence_score = EXCLUDED.confidence_score,
    computed_at = NOW();
"""

CREATE_VIEW_SQL = """
CREATE MATERIALIZED VIEW IF NOT EXISTS vw_road_traffic_summary AS
SELECT * FROM traffic_survey_overall;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("traffic", "0003_rename_final_value_trafficforprioritization_value_and_more"),
        ("grms", "0022_add_road_identifier"),
    ]

    operations = [
        migrations.RunSQL(DELETE_DUPLICATE_SUMMARIES, migrations.RunSQL.noop),
        migrations.CreateModel(
            name="TrafficSurveyOverall",
            fields=[
                ("overall_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("fiscal_year", models.IntegerField()),
                ("adt_total", models.DecimalField(decimal_places=3, max_digits=14)),
                ("pcu_total", models.DecimalField(decimal_places=3, max_digits=14)),
                ("confidence_score", models.DecimalField(decimal_places=2, max_digits=5)),
                ("computed_at", models.DateTimeField(auto_now=True)),
                (
                    "road",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="grms.road"),
                ),
            ],
            options={
                "db_table": "traffic_survey_overall",
                "unique_together": {("road", "fiscal_year")},
                "verbose_name": "Traffic survey overall",
                "verbose_name_plural": "Traffic survey overall",
            },
        ),
        migrations.RunSQL(
            POPULATE_OVERALL_SQL,
            reverse_sql="DELETE FROM traffic_survey_overall;",
        ),
        migrations.RunSQL(
            CREATE_VIEW_SQL,
            reverse_sql="DROP MATERIALIZED VIEW IF EXISTS vw_road_traffic_summary;",
        ),
    ]
