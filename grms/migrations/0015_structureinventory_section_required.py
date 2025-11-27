from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0014_update_culvert_detail"),
    ]

    operations = [
        migrations.AlterField(
            model_name="structureinventory",
            name="section",
            field=models.ForeignKey(
                help_text="Road section containing the structure",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="structures",
                to="grms.roadsection",
            ),
        ),
    ]
