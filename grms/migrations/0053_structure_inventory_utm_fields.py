from django.db import migrations, models

from grms.utils import point_to_lat_lng, wgs84_to_utm


def backfill_structure_utm(apps, schema_editor):
    StructureInventory = apps.get_model("grms", "StructureInventory")
    for structure in StructureInventory.objects.exclude(location_point__isnull=True):
        if structure.easting_m is not None and structure.northing_m is not None:
            continue
        latlng = point_to_lat_lng(structure.location_point)
        if not latlng:
            continue
        zone = structure.utm_zone or 37
        try:
            easting, northing = wgs84_to_utm(latlng["lat"], latlng["lng"], zone=zone)
        except Exception:
            continue
        StructureInventory.objects.filter(pk=structure.pk).update(
            easting_m=easting,
            northing_m=northing,
            utm_zone=zone,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0052_roadsocioeconomic_help_texts"),
    ]

    operations = [
        migrations.AddField(
            model_name="structureinventory",
            name="easting_m",
            field=models.DecimalField(blank=True, decimal_places=2, help_text="UTM easting (m) for point structures", max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="structureinventory",
            name="northing_m",
            field=models.DecimalField(blank=True, decimal_places=2, help_text="UTM northing (m) for point structures", max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="structureinventory",
            name="utm_zone",
            field=models.PositiveSmallIntegerField(default=37, help_text="UTM zone used for Easting/Northing values"),
        ),
        migrations.RunPython(backfill_structure_utm, migrations.RunPython.noop),
    ]
