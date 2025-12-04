from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Marks the traffic overall table migration as applied so Django stops trying "
        "to create an existing table."
    )

    def handle(self, *args, **kwargs):
        try:
            call_command(
                "migrate", "traffic", "0004_create_traffic_survey_overall_clean", fake=True
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "✔ Marked 0004_create_traffic_survey_overall_clean as applied (fake)."
                )
            )
        except Exception as e:  # pragma: no cover - informational logging
            self.stdout.write(self.style.ERROR(f"⚠ Error faking migration: {e}"))
        try:
            call_command("migrate")
            self.stdout.write(self.style.SUCCESS("✔ All migrations now applied successfully."))
        except Exception as e:  # pragma: no cover - informational logging
            self.stdout.write(self.style.ERROR(f"⚠ Error running migrate: {e}"))
