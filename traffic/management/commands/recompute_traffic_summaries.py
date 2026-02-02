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
            cycles_present = set(
                TrafficSurvey.objects.filter(
                    road_id=survey.road_id,
                    survey_year=survey.survey_year,
                ).values_list("cycle_number", flat=True)
            )
            missing_cycles = {1, 2, 3} - cycles_present
            if missing_cycles:
                missing_list = ", ".join(str(cycle) for cycle in sorted(missing_cycles))
                self.stdout.write(
                    self.style.WARNING(
                        f"Missing cycles for road {survey.road_id} year {survey.survey_year}: {missing_list}"
                    )
                )
        self.stdout.write(self.style.SUCCESS(f"Processed {approved_surveys.count()} approved surveys."))
