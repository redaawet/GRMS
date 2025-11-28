from django.db import migrations


def drop_legacy_columns(apps, schema_editor):
    table_name = "traffic_count_record"
    connection = schema_editor.connection
    introspection = connection.introspection
    existing_tables = introspection.table_names()

    if table_name not in existing_tables:
        return

    with connection.cursor() as cursor:
        column_names = {col.name for col in introspection.get_table_description(cursor, table_name)}

    legacy_columns = {"count_value", "vehicle_class", "road_segment_id"}
    drop_columns = legacy_columns & column_names

    if not drop_columns:
        return

    with connection.cursor() as cursor:
        for column in sorted(drop_columns):
            try:
                cursor.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column}")
            except Exception:
                # If the backend does not support IF EXISTS or drop fails, ignore so migration can continue.
                pass


def noop(apps, schema_editor):
    # Reverse migration not required; legacy columns are intentionally removed.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("traffic", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(drop_legacy_columns, reverse_code=noop),
    ]
