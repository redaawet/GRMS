from django.core.management.base import BaseCommand

from traffic.models import (
    TrafficSurvey,
    recompute_cycle_summaries_for_survey,
    recompute_survey_summary_for_survey,
)


class Command(BaseCommand):
    help = "Recompute traffic cycle and survey summaries for approved surveys"

    def handle(self, *args, **options):
        approved_surveys = TrafficSurvey.objects.filter(qa_status="Approved")
        for survey in approved_surveys:
            recompute_cycle_summaries_for_survey(survey)
            recompute_survey_summary_for_survey(survey)
        self.stdout.write(self.style.SUCCESS(f"Processed {approved_surveys.count()} approved surveys."))
