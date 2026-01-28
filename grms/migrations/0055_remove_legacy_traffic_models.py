from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("grms", "0054_roadnamealias"),
    ]

    operations = [
        migrations.DeleteModel(
            name="TrafficCountRecord",
        ),
        migrations.DeleteModel(
            name="TrafficCycleSummary",
        ),
        migrations.DeleteModel(
            name="TrafficSurveySummary",
        ),
        migrations.DeleteModel(
            name="TrafficQC",
        ),
        migrations.DeleteModel(
            name="TrafficForPrioritization",
        ),
        migrations.DeleteModel(
            name="TrafficSurvey",
        ),
    ]
