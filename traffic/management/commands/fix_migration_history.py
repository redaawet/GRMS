"""Utilities for faking out-of-order traffic migrations."""

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Fix inconsistent migration history for the traffic app by faking 0004 and 0005 as applied."

    def handle(self, *args, **kwargs):
        # 1. Fake-apply migration 0004
        try:
            call_command("migrate", "traffic", "0004_road_level_traffic_overall", fake=True)
            self.stdout.write(self.style.SUCCESS("✔ Marked 0004_road_level_traffic_overall as applied (fake)."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"⚠ Error faking 0004: {e}"))

        # 2. Fake-apply migration 0005
        try:
            call_command("migrate", "traffic", "0005_alter_trafficsurveyoverall_options", fake=True)
            self.stdout.write(self.style.SUCCESS("✔ Marked 0005_alter_trafficsurveyoverall_options as applied (fake)."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"⚠ Error faking 0005: {e}"))

        # 3. Now run migrate normally
        try:
            call_command("migrate")
            self.stdout.write(self.style.SUCCESS("✔ Migration history fixed and all migrations synchronized successfully."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"⚠ Error running migrate: {e}"))
