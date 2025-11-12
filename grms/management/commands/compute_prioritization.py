from django.core.management.base import BaseCommand
from grms.models import RoadSegment, RoadSegmentConditionSurvey

class Command(BaseCommand):
    help = 'Compute simple prioritization score for segments based on survey quantities (placeholder)'

    def handle(self, *args, **options):
        for seg in RoadSegment.objects.all()[:100]:
            surveys = seg.conditions.order_by('-created_at')
            last = surveys.first() if surveys.exists() else None
            qty = getattr(last, 'quantity_estimated', None) or 0
            self.stdout.write(f"Segment {seg.pk} last_estimated_qty: {qty}")
