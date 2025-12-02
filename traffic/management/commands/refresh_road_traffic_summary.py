from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Refreshes the vw_road_traffic_summary materialized view"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW vw_road_traffic_summary;")
        self.stdout.write(self.style.SUCCESS("Refreshed vw_road_traffic_summary."))
