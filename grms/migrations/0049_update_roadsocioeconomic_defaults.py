from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0048_srad_numbering_and_admin_updates"),
    ]

    operations = [
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="population_served",
            field=models.PositiveIntegerField(default=10000),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="trading_centers",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="villages",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="road_link_type",
            field=models.ForeignKey(
                blank=True,
                help_text="Functional road class (socio-economic input)",
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="socioeconomic_records",
                to="grms.roadlinktypelookup",
            ),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="farmland_percent",
            field=models.DecimalField(decimal_places=2, default=Decimal("20.00"), max_digits=5),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="cooperative_centers",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="markets",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="health_centers",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="education_centers",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="roadsocioeconomic",
            name="development_projects",
            field=models.PositiveIntegerField(default=1),
        ),
    ]
