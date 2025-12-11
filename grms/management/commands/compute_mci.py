from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from grms.models import RoadConditionSurvey, SegmentMCIResult


class Command(BaseCommand):
    help = "Compute or update Segment MCI Results for all RoadConditionSurvey entries in a given fiscal year."

    def add_arguments(self, parser):
        parser.add_argument(
            "year",
            type=int,
            help="Fiscal year (YYYY) to compute MCI results for.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        year = options["year"]

        surveys = RoadConditionSurvey.objects.filter(
            inspection_date__year=year
        ).select_related(
            "road_segment",
            "drainage_left",
            "drainage_right",
            "shoulder_left",
            "shoulder_right",
            "surface_condition",
        )

        total = surveys.count()
        if total == 0:
            self.stdout.write(f"No surveys found for fiscal year {year}.")
            return

        self.stdout.write(f"Computing MCI results for {total} survey(s) in FY {year}...")

        computed = 0
        for survey in surveys:
            try:
                SegmentMCIResult.create_or_update_from_survey(survey)
                computed += 1
            except Exception as e:
                raise CommandError(f"Error computing MCI for survey {survey.id}: {e}")

        self.stdout.write(self.style.SUCCESS(
            f"Completed. Computed/updated {computed} MCI result(s)."
        ))
