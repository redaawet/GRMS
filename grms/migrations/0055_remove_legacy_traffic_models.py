from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("grms", "0054_roadnamealias"),
    ]

    operations = [
        migrations.RemoveModel(
            name="TrafficCountRecord",
        ),
        migrations.RemoveModel(
            name="TrafficCycleSummary",
        ),
        migrations.RemoveModel(
            name="TrafficSurveySummary",
        ),
        migrations.RemoveModel(
            name="TrafficQC",
        ),
        migrations.RemoveModel(
            name="TrafficForPrioritization",
        ),
        migrations.RemoveModel(
            name="TrafficSurvey",
        ),
    ]
