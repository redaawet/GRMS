from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0011_structureconditionsurvey_condition_code"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="structureinventory",
            options={
                "ordering": ["road", "station_km"],
                "verbose_name": "Structure inventory",
                "verbose_name_plural": "Structure inventories",
            },
        ),
        migrations.RenameField(
            model_name="structureinventory",
            old_name="structure_type",
            new_name="structure_name",
        ),
        migrations.RemoveField(
            model_name="structureinventory",
            name="condition_code",
        ),
        migrations.RemoveField(
            model_name="structureinventory",
            name="head_walls_flag",
        ),
        migrations.AlterField(
            model_name="structureinventory",
            name="road",
            field=models.ForeignKey(
                help_text="Parent road carrying or associated with the structure",
                on_delete=models.deletion.CASCADE,
                related_name="structures",
                to="grms.road",
            ),
        ),
        migrations.AlterField(
            model_name="structureinventory",
            name="structure_name",
            field=models.CharField(
                blank=True,
                help_text="Optional structure name / local ID",
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name="structureinventory",
            name="attachments",
            field=models.JSONField(
                blank=True,
                help_text="Photos or documents (file metadata, URLs, etc.)",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="bridgedetail",
            name="bridge_type",
            field=models.CharField(
                choices=[
                    ("Concrete", "Concrete Bridge"),
                    ("Stone", "Stone Bridge"),
                    ("Bailey", "Bailey Bridge"),
                    ("Steel", "Steel Bridge"),
                    ("Timber", "Timber Bridge"),
                ],
                help_text="Type of bridge",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="bridgedetail",
            name="length_m",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Total bridge length (m)",
                max_digits=8,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="bridgedetail",
            name="span_count",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Number of spans",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="bridgedetail",
            name="width_m",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Deck width (m)",
                max_digits=6,
                null=True,
            ),
        ),
    ]
