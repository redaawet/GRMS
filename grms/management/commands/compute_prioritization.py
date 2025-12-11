from django.core.management.base import BaseCommand
from grms.models import RoadConditionSurvey, RoadSegment, SegmentMCIResult

class Command(BaseCommand):
    help = 'Compute simple prioritization score for segments based on survey quantities (placeholder)'

    def handle(self, *args, **options):
        for seg in RoadSegment.objects.all()[:100]:
            surveys = seg.condition_surveys.order_by('-inspection_date')
            last: RoadConditionSurvey | None = surveys.first() if surveys.exists() else None
            result = SegmentMCIResult.create_from_survey(last) if last else None
            mci = result.mci_value if result else 0
            self.stdout.write(f"Segment {seg.pk} last_mci: {mci}")
