from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("grms", "0012_update_structureinventory_and_bridgedetail"),
    ]

    operations = [
        migrations.AlterField(
            model_name="structureinventory",
            name="attachments",
            field=models.JSONField(
                blank=True,
                help_text="Design documents and photos (store file metadata, URLs, or other attachment descriptors)",
                null=True,
            ),
        ),
    ]
