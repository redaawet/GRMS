from django.db import migrations, models

from django.db import migrations, models

import grms.gis_fields


def populate_section_from_segment(apps, schema_editor):
    FurnitureInventory = apps.get_model("grms", "FurnitureInventory")

    for furniture in FurnitureInventory.objects.all():
        road_segment = getattr(furniture, "road_segment", None)
        if road_segment:
            furniture.section_id = road_segment.section_id
            furniture.save(update_fields=["section"])


class Migration(migrations.Migration):
    dependencies = [
        ("grms", "0014_update_culvert_detail"),
    ]

    operations = [
        migrations.AddField(
            model_name="furnitureinventory",
            name="section",
            field=models.ForeignKey(null=True, on_delete=models.CASCADE, related_name="furniture", to="grms.roadsection"),
        ),
        migrations.AddField(
            model_name="furnitureinventory",
            name="chainage_km",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="furnitureinventory",
            name="location_point",
            field=grms.gis_fields.PointField(
                blank=True,
                null=True,
                help_text="Optional GPS location of the furniture",
            ),
        ),
        migrations.AlterField(
            model_name="furnitureinventory",
            name="furniture_type",
            field=models.CharField(
                choices=[
                    ("Guard Post", "Guard Post"),
                    ("Guard Rail", "Guard Rail"),
                    ("KM Post", "KM Post"),
                    ("Road Sign", "Road Sign"),
                ],
                help_text="Furniture category",
                max_length=20,
            ),
        ),
        migrations.RunPython(populate_section_from_segment, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="furnitureinventory",
            name="section",
            field=models.ForeignKey(on_delete=models.CASCADE, related_name="furniture", to="grms.roadsection"),
        ),
        migrations.RemoveField(
            model_name="furnitureinventory",
            name="road_segment",
        ),
    ]
