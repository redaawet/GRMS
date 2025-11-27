from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0010_alter_road_geometry"),
    ]

    operations = [
        migrations.AddField(
            model_name="structureconditionsurvey",
            name="condition_code",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Overall condition rating code (1=Good, 4=Poor)",
                null=True,
            ),
        ),
    ]
