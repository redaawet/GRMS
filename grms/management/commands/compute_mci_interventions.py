from django.core.management.base import BaseCommand

from grms.services import mci_intervention


class Command(BaseCommand):
    help = "Recompute MCI-based intervention recommendations for road segments."

    def handle(self, *args, **options):
        processed_segments, created = mci_intervention.recompute_all_segment_interventions()
        self.stdout.write(
            self.style.SUCCESS(
                f"Recomputed interventions for {processed_segments} segment(s); "
                f"created {created} recommendation(s)."
            )
        )
