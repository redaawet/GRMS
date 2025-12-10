from django.core.management.base import BaseCommand, CommandError
from grms.services import prioritization


class Command(BaseCommand):
    help = "Compute benefit factors and prioritization results for a given fiscal year."

    def add_arguments(self, parser):
        parser.add_argument(
            "fiscal_year",
            type=int,
            help="Fiscal year to compute benefit factors for.",
        )

    def handle(self, *args, **options):
        fiscal_year = options["fiscal_year"]

        self.stdout.write(self.style.WARNING(f"Starting benefit factor computation for FY {fiscal_year}..."))

        try:
            results = prioritization.compute_prioritization_for_year(fiscal_year)
        except Exception as exc:
            raise CommandError(f"Error during computation: {exc}")

        count = len(results)
        self.stdout.write(self.style.SUCCESS(f"Completed. {count} prioritization records created/updated."))
