from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.deletion import ProtectedError

from grms import models as grms_models
from traffic import models as traffic_models


class Command(BaseCommand):
    help = "Delete domain data (roads, surveys, traffic, structures) while keeping lookup/auth tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes-i-know",
            action="store_true",
            help="Confirm deletion of domain data.",
        )

    def handle(self, *args, **options):
        if not options.get("yes_i_know"):
            raise CommandError("This command requires --yes-i-know to proceed.")

        deletion_plan = [
            ("traffic.TrafficCountRecord", traffic_models.TrafficCountRecord),
            ("traffic.TrafficCycleSummary", traffic_models.TrafficCycleSummary),
            ("traffic.TrafficSurveySummary", traffic_models.TrafficSurveySummary),
            ("traffic.TrafficSurveyOverall", traffic_models.TrafficSurveyOverall),
            ("traffic.TrafficForPrioritization", traffic_models.TrafficForPrioritization),
            ("traffic.TrafficQC", traffic_models.TrafficQC),
            ("traffic.TrafficSurvey", traffic_models.TrafficSurvey),
            ("grms.StructureConditionSurvey", grms_models.StructureConditionSurvey),
            ("grms.RoadConditionSurvey", grms_models.RoadConditionSurvey),
            ("grms.BridgeDetail", grms_models.BridgeDetail),
            ("grms.CulvertDetail", grms_models.CulvertDetail),
            ("grms.StructureInventory", grms_models.StructureInventory),
            ("grms.RoadSocioEconomic", grms_models.RoadSocioEconomic),
            ("grms.RoadSegment", grms_models.RoadSegment),
            ("grms.RoadSection", grms_models.RoadSection),
            ("grms.Road", grms_models.Road),
        ]

        with transaction.atomic():
            for label, model in deletion_plan:
                try:
                    deleted, _ = model.objects.all().delete()
                except ProtectedError as exc:
                    self.stderr.write(f"Failed to delete {label}.")
                    self.stderr.write(str(exc))
                    self.stderr.write("Hint: Add the referencing model earlier in delete order.")
                    raise
                self.stdout.write(f"Deleted {deleted} {label} records")
