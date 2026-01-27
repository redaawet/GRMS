from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("grms", "0053_structure_inventory_utm_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="RoadNameAlias",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name_from", models.CharField(max_length=150)),
                ("name_to", models.CharField(max_length=150)),
                ("normalized_key", models.CharField(db_index=True, max_length=200, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "road",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="name_aliases", to="grms.road"),
                ),
            ],
            options={
                "verbose_name": "Road name alias",
                "verbose_name_plural": "Road name aliases",
            },
        ),
    ]
