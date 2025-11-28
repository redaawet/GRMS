from django.db import migrations


class SafeRemoveField(migrations.RemoveField):
    """Remove a field from project state if present, ignoring missing fields.

    This is helpful when older migrations or databases still list legacy
    columns like ``count_value`` even though the current models no longer
    declare them. By swallowing ``KeyError`` during state mutation we keep the
    migration graph buildable across varied historical states.
    """

    def state_forwards(self, app_label, state):
        try:
            super().state_forwards(app_label, state)
        except KeyError:
            # Field already absent from state; nothing to do.
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("traffic", "0002_cleanup_legacy_columns"),
    ]

    operations = [
        # These are state-only cleanups; database columns were handled by
        # 0002_cleanup_legacy_columns via raw SQL.
        SafeRemoveField(
            model_name="trafficcountrecord",
            name="count_value",
        ),
        SafeRemoveField(
            model_name="trafficcountrecord",
            name="vehicle_class",
        ),
        SafeRemoveField(
            model_name="trafficcountrecord",
            name="road_segment",
        ),
    ]
