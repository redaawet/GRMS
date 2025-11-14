from django.db import migrations, models
import django.db.models.deletion


def _get_or_create_zone(AdminZone, name):
    normalized = (name or "Unknown").strip() or "Unknown"
    zone, _ = AdminZone.objects.get_or_create(name=normalized)
    return zone


def _get_or_create_woreda(AdminWoreda, zone, name):
    normalized = (name or "Unknown").strip() or "Unknown"
    woreda, _ = AdminWoreda.objects.get_or_create(name=normalized, zone=zone)
    return woreda


def forwards_func(apps, schema_editor):
    Road = apps.get_model("grms", "Road")
    AdminZone = apps.get_model("grms", "AdminZone")
    AdminWoreda = apps.get_model("grms", "AdminWoreda")

    for road in Road.objects.all():
        zone = _get_or_create_zone(AdminZone, getattr(road, "admin_zone_name", None))
        woreda = _get_or_create_woreda(AdminWoreda, zone, getattr(road, "admin_woreda_name", None))
        road.admin_zone = zone
        road.admin_woreda = woreda
        road.save(update_fields=["admin_zone", "admin_woreda"])


def backwards_func(apps, schema_editor):
    Road = apps.get_model("grms", "Road")

    for road in Road.objects.select_related("admin_zone", "admin_woreda"):
        road.admin_zone_name = road.admin_zone.name if road.admin_zone_id else ""
        road.admin_woreda_name = road.admin_woreda.name if road.admin_woreda_id else ""
        road.save(update_fields=["admin_zone_name", "admin_woreda_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminZone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("region", models.CharField(default="Tigray", max_length=100)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AdminWoreda",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                (
                    "zone",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="woredas",
                        to="grms.adminzone",
                    ),
                ),
            ],
            options={"ordering": ["zone__name", "name"]},
        ),
        migrations.AlterUniqueTogether(name="adminworeda", unique_together={("name", "zone")}),
        migrations.RenameField(
            model_name="road",
            old_name="admin_zone",
            new_name="admin_zone_name",
        ),
        migrations.RenameField(
            model_name="road",
            old_name="admin_woreda",
            new_name="admin_woreda_name",
        ),
        migrations.AddField(
            model_name="road",
            name="admin_zone",
            field=models.ForeignKey(
                help_text="Administrative zone",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="roads",
                to="grms.adminzone",
            ),
        ),
        migrations.AddField(
            model_name="road",
            name="admin_woreda",
            field=models.ForeignKey(
                help_text="Administrative Woreda",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="roads",
                to="grms.adminworeda",
            ),
        ),
        migrations.RunPython(forwards_func, backwards_func),
        migrations.RemoveField(
            model_name="road",
            name="admin_zone_name",
        ),
        migrations.RemoveField(
            model_name="road",
            name="admin_woreda_name",
        ),
        migrations.AlterField(
            model_name="road",
            name="admin_zone",
            field=models.ForeignKey(
                help_text="Administrative zone",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="roads",
                to="grms.adminzone",
            ),
        ),
        migrations.AlterField(
            model_name="road",
            name="admin_woreda",
            field=models.ForeignKey(
                help_text="Administrative Woreda",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="roads",
                to="grms.adminworeda",
            ),
        ),
    ]
