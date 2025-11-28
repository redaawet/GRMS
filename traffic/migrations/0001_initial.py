from django.db import migrations, models
import grms.gis_fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("grms", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TrafficSurvey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("survey_year", models.IntegerField(help_text="Year of survey (e.g. 2025).")),
                ("cycle_number", models.PositiveSmallIntegerField(help_text="Economic-season cycle (1–3).")),
                ("count_start_date", models.DateField()),
                ("count_end_date", models.DateField()),
                (
                    "count_days_per_cycle",
                    models.PositiveSmallIntegerField(default=7, help_text="Number of days counted in this cycle (usually 7)."),
                ),
                (
                    "count_hours_per_day",
                    models.PositiveSmallIntegerField(default=12, help_text="Hours counted per day (12 or 24)."),
                ),
                (
                    "night_adjustment_factor",
                    models.DecimalField(decimal_places=3, help_text="Night adjustment factor used for this survey (frozen).", max_digits=6),
                ),
                (
                    "override_night_factor",
                    models.BooleanField(
                        default=False,
                        help_text="Tick only if you manually override the computed night adjustment factor.",
                    ),
                ),
                (
                    "method",
                    models.CharField(
                        choices=[
                            ("MOC", "Manual Overall Count (MOC)"),
                            ("MTS", "Manual Turning/Section (MTS)"),
                            ("Automated", "Automated counter"),
                            ("Other", "Other"),
                        ],
                        default="MOC",
                        max_length=20,
                    ),
                ),
                ("observer", models.CharField(blank=True, help_text="Team or observer name.", max_length=150)),
                (
                    "location_override",
                    grms.gis_fields.PointField(
                        blank=True,
                        help_text="Optional GPS point if different from segment centroid.",
                        null=True,
                        srid=4326,
                    ),
                ),
                ("weather_notes", models.CharField(blank=True, max_length=100)),
                (
                    "qa_status",
                    models.CharField(
                        choices=[
                            ("Draft", "Draft"),
                            ("In Review", "In Review"),
                            ("Approved", "Approved"),
                            ("Rejected", "Rejected"),
                        ],
                        default="Draft",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "road",
                    models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="traffic_surveys", to="grms.road"),
                ),
            ],
            options={
                "verbose_name": "Traffic survey",
                "verbose_name_plural": "Traffic surveys",
                "db_table": "traffic_survey",
                "unique_together": {("road", "survey_year", "cycle_number")},
            },
        ),
        migrations.CreateModel(
            name="NightAdjustmentLookup",
            fields=[
                ("nadj_id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "hours_counted",
                    models.SmallIntegerField(help_text="Hours counted per day (e.g., 12 or 24)."),
                ),
                ("adjustment_factor", models.DecimalField(decimal_places=3, max_digits=6)),
                ("effective_date", models.DateField()),
                ("notes", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Night adjustment lookup",
                "verbose_name_plural": "Night adjustment lookup entries",
                "db_table": "night_adjustment_lookup",
                "indexes": [models.Index(fields=["hours_counted", "effective_date"], name="night_adjus_hours_c_3d5d1a_idx")],
            },
        ),
        migrations.CreateModel(
            name="PcuLookup",
            fields=[
                ("pcu_id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "vehicle_class",
                    models.CharField(
                        choices=[
                            ("Car", "Car"),
                            ("LightGoods", "Light goods"),
                            ("MiniBus", "Mini-bus"),
                            ("MediumGoods", "Medium goods"),
                            ("HeavyGoods", "Heavy goods"),
                            ("Bus", "Bus"),
                            ("Tractor", "Tractor"),
                            ("Motorcycle", "Motorcycle"),
                            ("Bicycle", "Bicycle"),
                            ("Pedestrian", "Pedestrian"),
                        ],
                        max_length=20,
                    ),
                ),
                ("pcu_factor", models.DecimalField(decimal_places=3, max_digits=6)),
                ("effective_date", models.DateField()),
                ("expiry_date", models.DateField(blank=True, null=True)),
                ("region", models.CharField(blank=True, max_length=100, null=True)),
                ("notes", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "PCU lookup",
                "verbose_name_plural": "PCU lookup entries",
                "db_table": "pcu_lookup",
                "indexes": [models.Index(fields=["vehicle_class", "effective_date"], name="pcu_lookup_vehicle_7e685b_idx")],
            },
        ),
        migrations.CreateModel(
            name="TrafficForPrioritization",
            fields=[
                ("prep_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("fiscal_year", models.IntegerField()),
                ("value_type", models.CharField(choices=[("ADT", "ADT"), ("PCU", "PCU")], max_length=10)),
                ("value", models.DecimalField(decimal_places=3, max_digits=14)),
                (
                    "source_survey",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="traffic_prioritization_values",
                        to="traffic.trafficsurvey",
                    ),
                ),
                (
                    "road",
                    models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="traffic_prioritization_values", to="grms.road"),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, help_text="Only one active record per road+fiscal_year+value_type."),
                ),
                ("prepared_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Traffic value for prioritization",
                "verbose_name_plural": "Traffic values for prioritization",
                "db_table": "traffic_for_prioritization",
                "unique_together": {("road", "fiscal_year", "value_type", "is_active")},
            },
        ),
        migrations.CreateModel(
            name="TrafficSurveySummary",
            fields=[
                ("survey_summary_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("vehicle_class", models.CharField(choices=[("Car", "Car"), ("LightGoods", "Light goods"), ("MiniBus", "Mini-bus"), ("MediumGoods", "Medium goods"), ("HeavyGoods", "Heavy goods"), ("Bus", "Bus"), ("Tractor", "Tractor"), ("Motorcycle", "Motorcycle"), ("Bicycle", "Bicycle"), ("Pedestrian", "Pedestrian")], max_length=20)),
                ("avg_daily_count_all_cycles", models.DecimalField(decimal_places=3, max_digits=12)),
                ("adt_class", models.DecimalField(decimal_places=3, max_digits=12)),
                ("pcu_class", models.DecimalField(decimal_places=3, max_digits=12)),
                ("adt_total", models.DecimalField(decimal_places=3, max_digits=12)),
                ("pcu_total", models.DecimalField(decimal_places=3, max_digits=14)),
                ("confidence_score", models.DecimalField(decimal_places=2, max_digits=5)),
                ("computed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "road",
                    models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="traffic_survey_summaries", to="grms.road"),
                ),
                (
                    "traffic_survey",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="survey_summaries", to="traffic.trafficsurvey"),
                ),
            ],
            options={
                "verbose_name": "Traffic survey summary",
                "verbose_name_plural": "Traffic survey summaries",
                "db_table": "traffic_survey_summary",
                "unique_together": {("traffic_survey", "road", "vehicle_class")},
            },
        ),
        migrations.CreateModel(
            name="TrafficQc",
            fields=[
                ("qc_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("issue_type", models.CharField(max_length=100)),
                ("issue_detail", models.TextField()),
                ("resolved", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "road",
                    models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="traffic_qc_issues", to="grms.road"),
                ),
                (
                    "traffic_survey",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="qc_issues", to="traffic.trafficsurvey"),
                ),
            ],
            options={
                "verbose_name": "Traffic QC issue",
                "verbose_name_plural": "Traffic QC issues",
                "db_table": "traffic_qc",
            },
        ),
        migrations.CreateModel(
            name="TrafficCountRecord",
            fields=[
                ("count_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("count_date", models.DateField()),
                ("time_block_from", models.TimeField(blank=True, null=True)),
                ("time_block_to", models.TimeField(blank=True, null=True)),
                (
                    "vehicle_class",
                    models.CharField(
                        choices=[
                            ("Car", "Car"),
                            ("LightGoods", "Light goods"),
                            ("MiniBus", "Mini-bus"),
                            ("MediumGoods", "Medium goods"),
                            ("HeavyGoods", "Heavy goods"),
                            ("Bus", "Bus"),
                            ("Tractor", "Tractor"),
                            ("Motorcycle", "Motorcycle"),
                            ("Bicycle", "Bicycle"),
                            ("Pedestrian", "Pedestrian"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "count_value",
                    models.IntegerField(default=0, help_text="Observed count for this block."),
                ),
                (
                    "is_market_day",
                    models.BooleanField(default=False, help_text="Market day flag."),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "traffic_survey",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="count_records",
                        to="traffic.trafficsurvey",
                    ),
                ),
            ],
            options={
                "verbose_name": "Traffic count record",
                "verbose_name_plural": "Traffic count records",
                "db_table": "traffic_count_record",
                "indexes": [
                    models.Index(fields=["traffic_survey", "count_date"], name="traffic_coun_traffic_fccf74_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="TrafficCycleSummary",
            fields=[
                ("cycle_summary_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("vehicle_class", models.CharField(choices=[("Car", "Car"), ("LightGoods", "Light goods"), ("MiniBus", "Mini-bus"), ("MediumGoods", "Medium goods"), ("HeavyGoods", "Heavy goods"), ("Bus", "Bus"), ("Tractor", "Tractor"), ("Motorcycle", "Motorcycle"), ("Bicycle", "Bicycle"), ("Pedestrian", "Pedestrian")], max_length=20)),
                ("cycle_number", models.PositiveSmallIntegerField()),
                ("cycle_days_counted", models.IntegerField()),
                ("cycle_sum_count", models.BigIntegerField()),
                ("cycle_daily_avg", models.DecimalField(decimal_places=3, max_digits=10)),
                ("cycle_daily_24hr", models.DecimalField(decimal_places=3, max_digits=12)),
                ("cycle_pcu", models.DecimalField(decimal_places=3, max_digits=12)),
                ("qc_flag", models.TextField(blank=True, null=True)),
                (
                    "road",
                    models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="traffic_cycle_summaries", to="grms.road"),
                ),
                (
                    "traffic_survey",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="cycle_summaries", to="traffic.trafficsurvey"),
                ),
            ],
            options={
                "verbose_name": "Traffic cycle summary",
                "verbose_name_plural": "Traffic cycle summaries",
                "db_table": "traffic_cycle_summary",
                "unique_together": {("traffic_survey", "road", "vehicle_class", "cycle_number")},
            },
        ),
    ]
