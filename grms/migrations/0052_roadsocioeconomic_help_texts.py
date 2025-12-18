from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0051_rename_code_mcicategorylookup_rating_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="road",
            field=models.OneToOneField(
                help_text="Road this socio-economic record applies to.",
                on_delete=models.deletion.CASCADE,
                related_name="socioeconomic",
                to="grms.road",
            ),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="population_served",
            field=models.PositiveIntegerField(
                default=10000, help_text="Estimated population served by the road."
            ),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="trading_centers",
            field=models.PositiveIntegerField(
                default=1, help_text="Number of trading centers served."
            ),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="villages",
            field=models.PositiveIntegerField(default=1, help_text="Number of villages served."),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="adt_override",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Average daily traffic value to use when survey data is absent.",
                null=True,
                verbose_name="ADT override",
            ),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="farmland_percent",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("20.00"),
                help_text="Share of surrounding area that is farmland (percent).",
                max_digits=5,
            ),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="cooperative_centers",
            field=models.PositiveIntegerField(
                default=1, help_text="Number of cooperative centers served."
            ),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="markets",
            field=models.PositiveIntegerField(default=1, help_text="Number of markets served."),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="health_centers",
            field=models.PositiveIntegerField(
                default=1, help_text="Number of health centers served."
            ),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="education_centers",
            field=models.PositiveIntegerField(
                default=1, help_text="Number of education centers served."
            ),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="development_projects",
            field=models.PositiveIntegerField(
                default=1, help_text="Number of development projects served."
            ),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="notes",
            field=models.TextField(
                blank=True, help_text="Additional notes about the socio-economic context."
            ),
        ),
    ]
