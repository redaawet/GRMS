from django.core.management.base import BaseCommand
from django.db.models import Avg, Sum

from traffic.models import TrafficSurveyOverall, TrafficSurveySummary


class Command(BaseCommand):
    help = "Compute road-level ADT/PCU totals"

    def handle(self, *args, **kwargs):
        summaries = (
            TrafficSurveySummary.objects
            .values('road_id', 'fiscal_year')
            .annotate(
                adt_total=Sum('adt_final'),
                pcu_total=Sum('pcu_final'),
                confidence_score=Avg('confidence_score'),
            )
        )

        for row in summaries:
            TrafficSurveyOverall.objects.update_or_create(
                road_id=row['road_id'],
                fiscal_year=row['fiscal_year'],
                defaults={
                    'adt_total': row['adt_total'],
                    'pcu_total': row['pcu_total'],
                    'confidence_score': row['confidence_score'],
                }
            )

        self.stdout.write(self.style.SUCCESS(f"Processed {len(summaries)} aggregated summaries."))
