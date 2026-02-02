from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand

from grms.models import Road


class Command(BaseCommand):
    help = "Normalize road section chainages, lengths, and geometries."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist fixes instead of running in dry-run mode.",
        )

    def handle(self, *args, **options):
        apply_changes: bool = options["apply"]
        tolerance = Decimal("0.02")

        for road in Road.objects.prefetch_related("sections").order_by("id"):
            sections = list(road.sections.order_by("start_chainage_km", "end_chainage_km", "id"))

            road_length = None
            if road.geometry:
                road_length = road.compute_length_km_from_geom()
            elif sections:
                end_values = [section.end_chainage_km for section in sections if section.end_chainage_km is not None]
                if end_values:
                    road_length = max(end_values)
                    self.stdout.write(f"Road {road} length inferred from sections: {road_length} km")

            if road_length is None:
                self.stdout.write(f"Skipping road {road} (no geometry or section chainage)")
                continue
            if road.total_length_km != road_length:
                self.stdout.write(
                    f"Road {road} length updated from {road.total_length_km} km to {road_length} km"
                )
                if apply_changes:
                    road.total_length_km = road_length
                    road.save(update_fields=["total_length_km"])

            if not sections:
                continue

            for idx, section in enumerate(sections):
                original_start = section.start_chainage_km
                original_end = section.end_chainage_km
                messages: list[str] = []

                if section.start_chainage_km is not None and section.start_chainage_km.copy_abs() <= tolerance:
                    section.start_chainage_km = Decimal("0")
                    messages.append("start→0")

                if idx > 0 and section.start_chainage_km is not None:
                    previous = sections[idx - 1]
                    gap = section.start_chainage_km - previous.end_chainage_km
                    if gap.copy_abs() <= tolerance:
                        section.start_chainage_km = previous.end_chainage_km
                        messages.append("aligned start with previous end")
                    elif gap > tolerance:
                        messages.append(f"gap of {gap:.3f} km before section")
                    elif gap < -tolerance:
                        messages.append(f"overlap of {-gap:.3f} km with previous")

                if idx == len(sections) - 1 and section.end_chainage_km is not None:
                    diff_end = road_length - section.end_chainage_km
                    if diff_end.copy_abs() <= tolerance:
                        section.end_chainage_km = road_length
                        messages.append("snapped end to road length")
                    elif diff_end > tolerance:
                        messages.append(f"trailing gap of {diff_end:.3f} km")
                    elif diff_end < -tolerance:
                        messages.append(f"section extends {(-diff_end):.3f} km past road")

                if messages:
                    change_msg = ", ".join(messages)
                    self.stdout.write(
                        f"Section {section.section_number or '?'} on {road}: {change_msg}"
                    )

                if apply_changes and messages:
                    section.save()

                if not apply_changes and messages:
                    section.start_chainage_km = original_start
                    section.end_chainage_km = original_end
