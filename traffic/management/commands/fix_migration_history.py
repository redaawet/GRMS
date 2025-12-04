"""Management command to repair an out-of-order traffic migration."""

from django.core.management import BaseCommand, call_command
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Fix inconsistent migration history for the traffic app by ensuring "
        "0004_road_level_traffic_overall is marked before "
        "0005_alter_trafficsurveyoverall_options."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Nominates a database to synchronize. Defaults to the \"default\" database.",
        )

    def handle(self, *args, **options):
        database = options["database"]
        connection = connections[database]
        recorder = MigrationRecorder(connection)
        migration_qs = recorder.migration_qs.using(database)

        has_0004 = migration_qs.filter(app="traffic", name="0004_road_level_traffic_overall").exists()
        has_0005 = migration_qs.filter(app="traffic", name="0005_alter_trafficsurveyoverall_options").exists()

        if has_0005 and not has_0004:
            migration_model = recorder.migration_qs.model
            migration_model.objects.using(database).create(
                app="traffic",
                name="0004_road_level_traffic_overall",
                applied=timezone.now(),
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "✔ Added missing 0004_road_level_traffic_overall migration to history to satisfy dependency order."
                )
            )
        elif has_0004:
            self.stdout.write(self.style.NOTICE("ℹ 0004_road_level_traffic_overall already marked as applied."))
        else:
            self.stdout.write(
                self.style.NOTICE(
                    "ℹ 0004_road_level_traffic_overall not applied yet. It will be handled by migrate run below."
                )
            )

        try:
            call_command("migrate", database=database)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✔ Migration history fixed and all migrations synchronized successfully on database '{database}'."
                )
            )
        except Exception as exc:
            self.stderr.write(
                self.style.ERROR(
                    f"⚠ Error running migrate on database '{database}': {exc}"
                )
            )
