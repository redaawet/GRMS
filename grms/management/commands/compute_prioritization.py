from django.core.management.base import BaseCommand
from grms.models import RoadConditionSurvey, RoadSegment

class Command(BaseCommand):
    help = 'Compute simple prioritization score for segments based on survey quantities (placeholder)'

    def handle(self, *args, **options):
        for seg in RoadSegment.objects.all()[:100]:
            surveys = seg.condition_surveys.order_by('-inspection_date')
            last: RoadConditionSurvey | None = surveys.first() if surveys.exists() else None
            mci = getattr(last, 'calculated_mci', None) or 0
            self.stdout.write(f"Segment {seg.pk} last_calculated_mci: {mci}")
