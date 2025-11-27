from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0013_alter_structureinventory_attachments_helptext"),
    ]

    operations = [
        migrations.RenameField(
            model_name="culvertdetail",
            old_name="width_span_m",
            new_name="span_m",
        ),
        migrations.AddField(
            model_name="culvertdetail",
            name="width_m",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Width (slab/box culverts)",
                max_digits=6,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="culvertdetail",
            name="culvert_type",
            field=models.CharField(
                choices=[
                    ("Slab Culvert", "Slab Culvert"),
                    ("Box Culvert", "Box Culvert"),
                    ("Pipe Culvert", "Pipe Culvert"),
                ],
                help_text="Type of culvert",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="culvertdetail",
            name="clear_height_m",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Clear height (slab/box culverts)",
                max_digits=6,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="culvertdetail",
            name="num_pipes",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Number of pipes (pipe culvert)",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="culvertdetail",
            name="pipe_diameter_m",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Pipe diameter (m)",
                max_digits=5,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="culvertdetail",
            name="has_head_walls",
            field=models.BooleanField(default=False, help_text="Head walls present"),
        ),
    ]
