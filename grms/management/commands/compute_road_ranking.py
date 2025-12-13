from django.core.management.base import BaseCommand, CommandError

from grms import models
from grms.services.planning import compute_road_ranking


class Command(BaseCommand):
    help = "Compute SRAD road ranking results for a given fiscal year."

    def add_arguments(self, parser):
        parser.add_argument("fiscal_year", type=int, help="Fiscal year to compute road rankings for.")

    def handle(self, *args, **options):
        fiscal_year = options["fiscal_year"]

        segment_needs = models.SegmentInterventionRecommendation.objects.count()
        structure_needs = models.StructureInterventionRecommendation.objects.count()
        if segment_needs == 0 and structure_needs == 0:
            self.stdout.write(
                self.style.WARNING(
                    "No intervention needs found. Compute intervention recommendations first "
                    "to ensure road costs are available."
                )
            )

        self.stdout.write(self.style.WARNING(f"Computing road ranking for FY {fiscal_year}..."))

        try:
            summary = compute_road_ranking(fiscal_year)
        except Exception as exc:  # pragma: no cover - execution-time errors
            raise CommandError(f"Error computing road ranking: {exc}")

        for group, data in summary.items():
            processed = data.get("processed", 0)
            self.stdout.write(self.style.SUCCESS(f"{group.title()}: {processed} road(s) ranked"))

            top_rows = data.get("top", []) or []
            if top_rows:
                self.stdout.write("Top 10 road indices:")
                for rank, row in top_rows:
                    self.stdout.write(
                        f"  #{rank}: {row.road} | RoadIndex={row.road_index:.8f} | "
                        f"Population={row.population_served} | Benefit={row.benefit_factor} | "
                        f"Cost={row.cost_of_improvement}"
                    )

        self.stdout.write(self.style.SUCCESS("Road ranking computation complete."))
