from django.core.management.base import BaseCommand

from grms.services import structure_intervention


class Command(BaseCommand):
    help = "Recompute intervention recommendations for all structures."

    def handle(self, *args, **options):
        processed, created = structure_intervention.recompute_all_structure_interventions()
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {processed} structure(s); created {created} recommendation(s)."
            )
        )
