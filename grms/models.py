"""Core data models for the GRMS backend.

This module follows the specification shared with the project stakeholders. It
contains inventory, survey, traffic, prioritisation and planning entities that
mirror the SRAD data model.  GIS fields are backed by PostGIS through
``django.contrib.gis``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Optional

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Max

from .gis_fields import LineStringField, PointField
from .utils import (
    GEOS_AVAILABLE,
    fetch_osrm_route,
    geometry_length_km,
    geos_length_km,
    make_point,
    osrm_linestring_to_geos,
    point_to_lat_lng,
    slice_linestring_by_chainage,
    utm_to_wgs84,
)

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------


class QAStatus(models.Model):
    """Quality assurance status for survey records."""

    status = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "QA status"
        verbose_name_plural = "QA statuses"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.status


class RoadLinkTypeLookup(models.Model):
    """Functional road classification lookup used for prioritisation."""

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    score = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Road link type"
        verbose_name_plural = "Road link types"
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.name} ({self.code})"


class AdminZone(models.Model):
    """Administrative zone lookup for the Tigray region."""

    name = models.CharField(max_length=100, unique=True)
    region = models.CharField(max_length=100, default="Tigray")

    class Meta:
        verbose_name = "Administrative zone"
        verbose_name_plural = "Administrative zones"
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.name} ({self.region})"


class AdminWoreda(models.Model):
    """Administrative woreda lookup linked to a zone."""

    name = models.CharField(max_length=150)
    zone = models.ForeignKey(AdminZone, on_delete=models.CASCADE, related_name="woredas")

    class Meta:
        verbose_name = "Administrative woreda"
        verbose_name_plural = "Administrative woredas"
        unique_together = ("name", "zone")
        ordering = ["zone__name", "name"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.name} ({self.zone.name})"


class InterventionLookup(models.Model):
    """Master list of maintenance interventions with default costs."""

    intervention_code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=150)
    category = models.CharField(
        max_length=10,
        choices=[("Road", "Road"), ("Structure", "Structure"), ("Bottleneck", "Bottleneck")],
    )
    unit_measure = models.CharField(max_length=10, choices=[("km", "km"), ("m", "m"), ("item", "item")])
    default_unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Intervention lookup"
        verbose_name_plural = "Intervention lookups"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.intervention_code} - {self.name}"


class InterventionCategory(models.Model):
    """Category for intervention work items used in planning lookups."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Intervention category"
        verbose_name_plural = "Intervention categories"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.name


class InterventionWorkItem(models.Model):
    """Lookup for intervention work items with optional default cost."""

    category = models.ForeignKey(
        InterventionCategory,
        on_delete=models.PROTECT,
        related_name="work_items",
    )
    work_code = models.CharField(max_length=5, unique=True)
    description = models.CharField(max_length=255)
    unit = models.CharField(max_length=30)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["work_code"]
        verbose_name = "Intervention work item"
        verbose_name_plural = "Intervention work items"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.work_code} - {self.description}"


class ActivityLookup(models.Model):
    """ERA maintenance activity codes used in detailed surveys."""

    UNIT_CHOICES = [
        ("m3", "m³"),
        ("m2", "m²"),
        ("m", "m"),
        ("km", "km"),
        ("item", "item"),
        ("lump_sum", "lump sum"),
    ]

    activity_code = models.CharField(max_length=10, primary_key=True)
    activity_name = models.CharField(max_length=150)
    default_unit = models.CharField(max_length=10, choices=UNIT_CHOICES)
    is_resource_based = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Activity lookup"
        verbose_name_plural = "Activity lookups"
        ordering = ["activity_code"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.activity_code} - {self.activity_name}"


class UnitCost(models.Model):
    """Regional overrides for intervention unit costs."""

    intervention = models.ForeignKey(InterventionLookup, on_delete=models.CASCADE, related_name="unit_costs")
    region = models.CharField(max_length=100)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Unit cost"
        verbose_name_plural = "Unit costs"
        unique_together = ("intervention", "region", "effective_date")

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.intervention_id} @ {self.region}"


class PCULookup(models.Model):
    """Passenger car unit conversion factor per vehicle class."""

    vehicle_class = models.CharField(max_length=20)
    pcu_factor = models.DecimalField(max_digits=6, decimal_places=3)
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "PCU lookup"
        verbose_name_plural = "PCU lookups"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.vehicle_class} ({self.pcu_factor})"


class NightAdjustmentLookup(models.Model):
    """Night adjustment multipliers for traffic surveys."""

    hours_counted = models.PositiveSmallIntegerField()
    adjustment_factor = models.DecimalField(max_digits=6, decimal_places=3)
    effective_date = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Night adjustment lookup"
        verbose_name_plural = "Night adjustment lookups"
        unique_together = ("hours_counted", "effective_date")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.hours_counted}h -> {self.adjustment_factor}"


class DistressType(models.Model):
    """Canonical list of distress codes used by surveyors."""

    ROAD = "road"
    STRUCTURE = "structure"
    FURNITURE = "furniture"
    OTHER = "other"

    CATEGORY_CHOICES = [
        (ROAD, "Road"),
        (STRUCTURE, "Structure"),
        (FURNITURE, "Furniture"),
        (OTHER, "Other"),
    ]

    distress_code = models.CharField(max_length=50, unique=True)
    distress_name = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Distress type"
        verbose_name_plural = "Distress types"
        ordering = ["distress_code"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.distress_code} ({self.category})"


class DistressCondition(models.Model):
    """Represents a severity/extent combination for a distress."""

    SEVERITY_CHOICES = [(1, "Minor"), (2, "Moderate"), (3, "Severe")]
    EXTENT_CHOICES = [(1, "Isolated"), (2, "Frequent"), (3, "Widespread")]

    distress = models.ForeignKey(DistressType, on_delete=models.CASCADE, related_name="conditions")
    severity_code = models.PositiveSmallIntegerField(choices=SEVERITY_CHOICES)
    extent_code = models.PositiveSmallIntegerField(choices=EXTENT_CHOICES, null=True, blank=True)
    condition_notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Distress condition"
        verbose_name_plural = "Distress conditions"
        unique_together = ("distress", "severity_code", "extent_code")
        ordering = ["distress__distress_code", "severity_code", "extent_code"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.distress_id} sev{self.severity_code} ext{self.extent_code or 0}"


class DistressActivity(models.Model):
    """Maps a distress condition to one or more ERA activities."""

    SCALE_BASIS_CHOICES = [
        ("per_segment", "Per segment"),
        ("per_100m", "Per 100 m"),
        ("per_1m", "Per 1 m"),
        ("per_m2", "Per m²"),
        ("per_culvert", "Per culvert"),
        ("per_item", "Per item"),
        ("fixed", "Fixed quantity"),
    ]

    condition = models.ForeignKey(DistressCondition, on_delete=models.CASCADE, related_name="activities")
    activity = models.ForeignKey(ActivityLookup, on_delete=models.CASCADE, related_name="distress_links")
    quantity_value = models.DecimalField(max_digits=12, decimal_places=3)
    scale_basis = models.CharField(max_length=20, choices=SCALE_BASIS_CHOICES)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Distress activity"
        verbose_name_plural = "Distress activities"
        unique_together = ("condition", "activity")

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.condition_id} -> {self.activity_id}"


# ---------------------------------------------------------------------------
# Road network inventory
# ---------------------------------------------------------------------------


class Road(models.Model):
    road_identifier = models.CharField(
        "Road ID",
        max_length=20,
        unique=True,
        validators=[RegexValidator(r"^RTR-\d+$", "Road ID must match RTR-<number> format.")],
        help_text="Unique identifier such as RTR-1",
    )
    road_name_from = models.CharField(max_length=150)
    road_name_to = models.CharField(max_length=150)
    design_standard = models.CharField(
        max_length=20,
        choices=[
            ("Basic Access", "Basic Access"),
            ("DC1", "DC1"),
            ("DC2", "DC2"),
            ("DC3", "DC3"),
            ("DC4", "DC4"),
            ("DC5", "DC5"),
            ("DC6", "DC6"),
            ("DC7", "DC7"),
            ("DC8", "DC8"),
        ],
        help_text="Design standard category",
    )
    admin_zone = models.ForeignKey(
        AdminZone,
        on_delete=models.PROTECT,
        related_name="roads",
        help_text="Administrative zone",
    )
    admin_woreda = models.ForeignKey(
        AdminWoreda,
        on_delete=models.PROTECT,
        related_name="roads",
        null=True,
        blank=True,
        help_text="Administrative Woreda (optional)",
    )
    total_length_km = models.DecimalField(max_digits=6, decimal_places=2)
    start_easting = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="UTM easting for the start point (Zone 37N)",
    )
    start_northing = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="UTM northing for the start point (Zone 37N)",
    )
    road_start_coordinates = PointField(srid=4326, null=True, blank=True)
    end_easting = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="UTM easting for the end point (Zone 37N)",
    )
    end_northing = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="UTM northing for the end point (Zone 37N)",
    )
    road_end_coordinates = PointField(srid=4326, null=True, blank=True)
    geometry = LineStringField(
        geography=True, null=True, blank=True, help_text="Road geometry (LineString)"
    )
    surface_type = models.CharField(
        max_length=10,
        choices=[("Earth", "Earth"), ("Gravel", "Gravel"), ("Paved", "Paved")],
        help_text="Primary surface type",
    )
    managing_authority = models.CharField(
        max_length=20,
        choices=[
            ("Federal", "Federal"),
            ("Regional", "Regional"),
            ("Wereda", "Wereda"),
            ("Community", "Community"),
        ],
        help_text="Responsible authority",
    )
    year_of_update = models.DateField(null=True, blank=True, help_text="Date of last MCI update")
    last_mci_update = models.DateField(null=True, blank=True, help_text="Most recent MCI update date")
    remarks = models.TextField(blank=True, help_text="Additional notes or remarks")

    class Meta:
        verbose_name = "Road"
        verbose_name_plural = "Roads"

    def __str__(self) -> str:  # pragma: no cover
        identifier = getattr(self, "road_identifier", None) or f"Road {self.id}"
        return f"{identifier}: {self.road_name_from}–{self.road_name_to}"

    def clean(self):  # pragma: no cover - simple validation
        errors = {}
        if self.admin_woreda_id and self.admin_zone_id:
            if self.admin_woreda.zone_id != self.admin_zone_id:
                errors["admin_woreda"] = "Selected woreda does not belong to the selected zone."

        if self.road_start_coordinates and self.road_end_coordinates:
            try:
                fetch_osrm_route(
                    float(self.road_start_coordinates.x),
                    float(self.road_start_coordinates.y),
                    float(self.road_end_coordinates.x),
                    float(self.road_end_coordinates.y),
                )
            except Exception:
                errors["geometry"] = "Could not fetch OSRM route"

        if errors:
            raise ValidationError(errors)

    def _point_from_utm(self, easting: Optional[Decimal], northing: Optional[Decimal]):
        if easting is None or northing is None:
            return None
        lat, lon = utm_to_wgs84(float(easting), float(northing), zone=37)
        return make_point(lat, lon)

    def save(self, *args, **kwargs):
        # Update WGS84 coordinates from UTM inputs when provided. Zone and
        # woreda selections are left untouched.
        if not self.road_identifier:
            next_id = (Road.objects.aggregate(Max("id")).get("id__max") or 0) + 1
            self.road_identifier = f"RTR-{next_id}"

        update_fields = kwargs.get("update_fields")
        update_fields_set = set(update_fields) if update_fields else None
        geometry_updated = False

        allow_autofill = (
            not update_fields_set
            or "start_easting" in update_fields_set
            or "start_northing" in update_fields_set
        )
        if allow_autofill:
            start_point = self._point_from_utm(self.start_easting, self.start_northing)
            if start_point:
                self.road_start_coordinates = start_point
                if update_fields_set is not None:
                    update_fields_set.add("road_start_coordinates")

        allow_autofill_end = (
            not update_fields_set
            or "end_easting" in update_fields_set
            or "end_northing" in update_fields_set
        )
        if allow_autofill_end:
            end_point = self._point_from_utm(self.end_easting, self.end_northing)
            if end_point:
                self.road_end_coordinates = end_point
                if update_fields_set is not None:
                    update_fields_set.add("road_end_coordinates")

        should_update_geometry = (
            self.road_start_coordinates
            and self.road_end_coordinates
            and (
                update_fields_set is None
                or bool(
                    {
                        "road_start_coordinates",
                        "road_end_coordinates",
                        "start_easting",
                        "start_northing",
                        "end_easting",
                        "end_northing",
                        "geometry",
                    }
                    & update_fields_set
                )
                or self.geometry is None
            )
        )

        if should_update_geometry:
            start_coords = point_to_lat_lng(self.road_start_coordinates)
            end_coords = point_to_lat_lng(self.road_end_coordinates)
            if start_coords and end_coords:
                try:
                    route_coords = fetch_osrm_route(
                        float(start_coords["lng"]),
                        float(start_coords["lat"]),
                        float(end_coords["lng"]),
                        float(end_coords["lat"]),
                    )
                except Exception:
                    route_coords = [
                        [float(start_coords["lng"]), float(start_coords["lat"])],
                        [float(end_coords["lng"]), float(end_coords["lat"])],
                    ]

                if GEOS_AVAILABLE:
                    self.geometry = osrm_linestring_to_geos(route_coords)
                else:
                    self.geometry = {
                        "type": "LineString",
                        "coordinates": route_coords,
                        "srid": 4326,
                    }

                geometry_updated = True

                if update_fields_set is not None:
                    update_fields_set.add("geometry")

        if self.geometry and (geometry_updated or self.total_length_km in (None, 0)):
            polyline_length = geometry_length_km(self.geometry)
            length_km = Decimal(str(polyline_length)).quantize(Decimal("0.01"))
            self.total_length_km = length_km
            if update_fields_set is not None:
                update_fields_set.add("total_length_km")

        if update_fields_set is not None:
            kwargs["update_fields"] = list(update_fields_set)

        super().save(*args, **kwargs)


class RoadGlobalCostReport(Road):
    class Meta:
        proxy = True
        verbose_name = "Global Cost of Road Works"
        verbose_name_plural = "Global Cost of Road Works"


class SectionWorkplanReport(Road):
    class Meta:
        proxy = True
        verbose_name = "Section Annual Workplan (Table 25)"
        verbose_name_plural = "Section Annual Workplan (Table 25)"


class AnnualWorkplanReport(Road):
    class Meta:
        proxy = True
        verbose_name = "Annual Workplan (Table 26)"
        verbose_name_plural = "Annual Workplan (Table 26)"


class RoadSection(models.Model):
    SURFACE_TYPES = [
        ("Earth", "Earth"),
        ("Gravel", "Gravel"),
        ("DBST", "DBST"),
        ("Asphalt", "Asphalt"),
        ("Sealed", "Sealed"),
    ]

    road = models.ForeignKey(Road, on_delete=models.CASCADE, related_name="sections")
    section_number = models.PositiveIntegerField(
        help_text="Section identifier within the road", editable=False
    )
    sequence_on_road = models.PositiveIntegerField(
        default=0,
        help_text="Ordered position of this section along the parent road",
        editable=False,
    )
    name = models.CharField(max_length=150, blank=True, help_text="Optional section name or landmark")
    start_chainage_km = models.DecimalField(max_digits=8, decimal_places=3, help_text="Section start chainage (km)")
    end_chainage_km = models.DecimalField(max_digits=8, decimal_places=3, help_text="Section end chainage (km)")
    length_km = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        help_text="Section length (km) computed from chainage",
        editable=False,
    )
    geometry = LineStringField(null=True, blank=True, help_text="Section geometry (LineString)")
    surface_type = models.CharField(max_length=10, choices=SURFACE_TYPES)
    surface_thickness_cm = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Wearing course or gravel thickness (cm) for gravel/paved surfaces",
    )
    admin_zone_override = models.ForeignKey(
        AdminZone,
        on_delete=models.PROTECT,
        related_name="section_overrides",
        null=True,
        blank=True,
        help_text="Override when the section crosses into a different zone",
    )
    admin_woreda_override = models.ForeignKey(
        AdminWoreda,
        on_delete=models.PROTECT,
        related_name="section_overrides",
        null=True,
        blank=True,
        help_text="Override when the section crosses into a different woreda",
    )
    notes = models.TextField(blank=True, help_text="Inventory notes for this section")
    start_easting = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="UTM easting for the section start (Zone 37N)",
    )
    start_northing = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="UTM northing for the section start (Zone 37N)",
    )
    section_start_coordinates = PointField(srid=4326, null=True, blank=True)
    end_easting = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="UTM easting for the section end (Zone 37N)",
    )
    end_northing = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="UTM northing for the section end (Zone 37N)",
    )
    section_end_coordinates = PointField(srid=4326, null=True, blank=True)

    class Meta:
        verbose_name = "Road section"
        verbose_name_plural = "Road sections"
        ordering = ("road", "sequence_on_road", "section_number")
        unique_together = (("road", "section_number"), ("road", "sequence_on_road"))

    def __str__(self) -> str:  # pragma: no cover
        return self.section_label

    @property
    def section_label(self) -> str:
        return f"{self.road.road_identifier}-S{self.sequence_on_road}"

    def clean(self):  # pragma: no cover - simple validation
        errors = {}

        if self.admin_zone_override_id and self.admin_woreda_override_id:
            if self.admin_woreda_override.zone_id != self.admin_zone_override_id:
                errors["admin_woreda_override"] = "Selected woreda does not belong to the selected zone."

        # Require road geometry BEFORE allowing section creation
        road = getattr(self, "road", None)
        if not road or not road.geometry:
            errors["road"] = "Road geometry is missing. Run Route Preview → Save Geometry first."

        geometry_length = geos_length_km(getattr(road, "geometry", None)) if road else 0.0

        if self.start_chainage_km is not None:
            if self.start_chainage_km < 0:
                errors["start_chainage_km"] = "Start chainage cannot be negative."

        if self.start_chainage_km is not None and self.end_chainage_km is not None:
            if self.end_chainage_km <= self.start_chainage_km:
                errors["end_chainage_km"] = "End chainage must be greater than start chainage."

            if self.road_id:
                road_length = Decimal(self.road.total_length_km)
                tolerance = Decimal("0.001")
                effective_length = Decimal(str(geometry_length or float(road_length)))
                if self.end_chainage_km > effective_length + tolerance:
                    errors["end_chainage_km"] = "Section end exceeds the parent road length."
                if self.start_chainage_km > effective_length + tolerance:
                    errors["start_chainage_km"] = "Section start exceeds the parent road length."
                if (self.end_chainage_km - self.start_chainage_km) > (road_length + tolerance):
                    errors["end_chainage_km"] = "Section length cannot be greater than the parent road length."

                overlaps = (
                    RoadSection.objects.filter(road_id=self.road_id)
                    .exclude(pk=self.pk)
                    .filter(
                        start_chainage_km__lt=self.end_chainage_km,
                        end_chainage_km__gt=self.start_chainage_km,
                    )
                )
                if overlaps.exists():
                    overlap_list = ", ".join(
                        f"section {section.section_number} ({section.start_chainage_km}–{section.end_chainage_km} km)"
                        for section in overlaps
                    )
                    errors["start_chainage_km"] = (
                        "Section overlaps with existing sections on this road: " + overlap_list
                    )

                siblings = RoadSection.objects.filter(road_id=self.road_id).exclude(pk=self.pk)
                previous = siblings.filter(end_chainage_km__lte=self.start_chainage_km).order_by("-end_chainage_km").first()
                next_section = siblings.filter(start_chainage_km__gte=self.end_chainage_km).order_by("start_chainage_km").first()

                if previous and (self.start_chainage_km - previous.end_chainage_km).copy_abs() > tolerance:
                    errors["start_chainage_km"] = (
                        f"Gap detected before this section; previous section {previous.section_number} ends at {previous.end_chainage_km} km."
                    )
                if next_section and (next_section.start_chainage_km - self.end_chainage_km).copy_abs() > tolerance:
                    errors["end_chainage_km"] = (
                        f"Gap detected after this section; next section {next_section.section_number} starts at {next_section.start_chainage_km} km."
                    )

                if previous and previous.sequence_on_road >= self.sequence_on_road:
                    errors["sequence_on_road"] = (
                        f"Sequence order must follow chainage; section {previous.section_number} comes before this one."
                    )
                if next_section and next_section.sequence_on_road <= self.sequence_on_road:
                    errors["sequence_on_road"] = (
                        f"Sequence order must follow chainage; section {next_section.section_number} should come after this one."
                    )

        if self.surface_type in {"Gravel", "DBST", "Asphalt", "Sealed"}:
            if self.surface_thickness_cm is None:
                errors["surface_thickness_cm"] = "Thickness is required for gravel or paved surfaces."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.road_id:
            if not self.sequence_on_road:
                max_sequence = (
                    RoadSection.objects.filter(road_id=self.road_id)
                    .exclude(pk=self.pk)
                    .aggregate(models.Max("sequence_on_road"))
                    .get("sequence_on_road__max")
                    or 0
                )
                self.sequence_on_road = max_sequence + 1
            if not self.section_number:
                self.section_number = self.sequence_on_road
        sliced = None
        if self.road and self.road.geometry and self.start_chainage_km is not None and self.end_chainage_km is not None:
            sliced = slice_linestring_by_chainage(
                self.road.geometry,
                float(self.start_chainage_km),
                float(self.end_chainage_km),
            )

        if sliced:
            self.geometry = sliced["geometry"]
            if sliced.get("start_point"):
                self.section_start_coordinates = make_point(*sliced["start_point"])
            if sliced.get("end_point"):
                self.section_end_coordinates = make_point(*sliced["end_point"])
            if sliced.get("length_km") is not None:
                self.length_km = Decimal(str(sliced["length_km"])).quantize(Decimal("0.001"))
        elif self.start_chainage_km is not None and self.end_chainage_km is not None:
            self.length_km = (self.end_chainage_km - self.start_chainage_km).quantize(Decimal("0.001"))

        self.full_clean()
        super().save(*args, **kwargs)


class RoadSegment(models.Model):
    section = models.ForeignKey(RoadSection, on_delete=models.CASCADE, related_name="segments")
    sequence_on_section = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text="Ordered position of this segment within the parent section",
    )
    segment_identifier = models.CharField(
        max_length=100,
        blank=True,
        editable=False,
        help_text="Stable SRAD-compliant segment identifier",
    )
    station_from_km = models.DecimalField(max_digits=8, decimal_places=3, help_text="Segment start chainage (km)")
    station_to_km = models.DecimalField(max_digits=8, decimal_places=3, help_text="Segment end chainage (km)")
    cross_section = models.CharField(
        max_length=20,
        choices=[
            ("Cutting", "Cutting"),
            ("Embankment", "Embankment"),
            ("Cut/Embankment", "Cut/Embankment"),
            ("Flat", "Flat"),
        ],
        help_text="Cross-section type (road in cutting, embankment, etc)",
    )
    terrain_transverse = models.CharField(
        max_length=15,
        choices=[
            ("Flat", "Flat"),
            ("Rolling", "Rolling"),
            ("Mountainous", "Mountainous"),
            ("Escarpment", "Escarpment"),
        ],
        help_text="Terrain transverse slope",
    )
    terrain_longitudinal = models.CharField(
        max_length=15,
        choices=[
            ("Flat", "Flat"),
            ("Rolling", "Rolling"),
            ("Mountainous", "Mountainous"),
            ("Escarpment", "Escarpment"),
        ],
        help_text="Terrain longitudinal slope",
    )
    ditch_left_present = models.BooleanField(
    default=False,
    help_text="Indicates if left-side drainage/ditch exists."
    )
    ditch_right_present = models.BooleanField(
        default=False,
        help_text="Indicates if right-side drainage/ditch exists."
    )

    shoulder_left_present = models.BooleanField(default=False)
    shoulder_right_present = models.BooleanField(default=False)
    carriageway_width_m = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comment = models.TextField(blank=True, help_text="Notes or comments for this segment")

    class Meta:
        verbose_name = "Road segment"
        verbose_name_plural = "Road segments"
        unique_together = (("section", "sequence_on_section"),)

    def clean(self):
        errors = {}

        if self.station_from_km is not None:
            if self.station_from_km < 0:
                errors["station_from_km"] = "Start chainage cannot be negative."

        if self.station_from_km is not None and self.station_to_km is not None:
            if self.station_to_km <= self.station_from_km:
                errors["station_to_km"] = "End chainage must be greater than start chainage."

        if self.section_id and self.section.length_km is not None and self.station_to_km is not None:
            section_length = self.section.length_km
            if self.station_to_km > section_length:
                errors["station_to_km"] = "Segment end exceeds the parent section length."
            if self.station_from_km is not None and self.station_from_km > section_length:
                errors["station_from_km"] = "Segment start exceeds the parent section length."

        if errors:
            raise ValidationError(errors)

    @property
    def length_km(self) -> float:
        """Return computed length based on chainage values."""

        start = float(self.station_from_km or 0)
        end = float(self.station_to_km or 0)
        return end - start

    def __str__(self) -> str:  # pragma: no cover
        return self.segment_identifier or f"Segment {self.pk or '?'}"

    @property
    def segment_label(self) -> str:
        if not self.section_id:
            return ""
        return (
            f"{self.section.road.road_identifier}-S{self.section.sequence_on_road}-"
            f"Sg{self.sequence_on_section}"
        )

    def save(self, *args, **kwargs):
        if self.section_id and not self.sequence_on_section:
            max_sequence = (
                RoadSegment.objects.filter(section_id=self.section_id)
                .exclude(pk=self.pk)
                .aggregate(models.Max("sequence_on_section"))
                .get("sequence_on_section__max")
                or 0
            )
            self.sequence_on_section = max_sequence + 1
        if self.section_id:
            self.segment_identifier = self.segment_label
        self.full_clean()
        super().save(*args, **kwargs)

    def has_road_bottleneck(self) -> bool:
        """Return True when the latest survey reports a bottleneck."""

        survey = self.condition_surveys.order_by("-inspection_date", "-id").first()
        return bool(survey and survey.is_there_bottleneck)


class StructureInventory(models.Model):
    """
    Master structure inventory (parent for Bridge/Culvert/Ford/Wall/etc.)
    """

    CATEGORY_CHOICES = [
        ("Bridge", "Bridge"),
        ("Culvert", "Culvert"),
        ("Ford", "Ford"),
        ("Retaining Wall", "Retaining Wall"),
        ("Gabion Wall", "Gabion Wall"),
        ("Other", "Other"),
    ]

    POINT = "Point"
    LINE = "Line"

    road = models.ForeignKey(
        Road,
        on_delete=models.CASCADE,
        related_name="structures",
        help_text="Parent road carrying or associated with the structure",
    )
    section = models.ForeignKey(
        RoadSection,
        on_delete=models.PROTECT,
        related_name="structures",
        null=True,
        blank=True,
        help_text="Road section containing the structure",
    )
    geometry_type = models.CharField(
        max_length=10,
        choices=[(POINT, "Point"), (LINE, "Line")],
        default=POINT,
        help_text="Indicates whether the structure is mapped as a point or line",
    )
    station_km = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Location along road (chainage km)",
    )
    start_chainage_km = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Start chainage (km) for line structures",
    )
    end_chainage_km = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="End chainage (km) for line structures",
    )
    location_point = PointField(
        srid=4326,
        null=True,
        blank=True,
        help_text="GPS coordinates of the structure",
    )
    location_line = LineStringField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Geometry of line structures",
    )
    location_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Optional latitude override for point structures",
    )
    location_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Optional longitude override for point structures",
    )

    # High-level classification only
    structure_category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        help_text="General category of structure",
    )

    # Free text type/name if needed (e.g. 'RC slab bridge')
    structure_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional structure name / local ID",
    )

    comments = models.TextField(blank=True)
    attachments = models.JSONField(
        null=True,
        blank=True,
        help_text="Design documents and photos (store file metadata, URLs, or other attachment descriptors)",
    )
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Structure inventory"
        verbose_name_plural = "Structure inventories"
        ordering = ["road", "structure_category", "station_km", "start_chainage_km"]

    def clean(self):
        errors = {}

        category = self.structure_category
        if category in {"Bridge", "Culvert", "Ford"}:
            self.geometry_type = self.POINT
        elif category in {"Retaining Wall", "Gabion Wall"}:
            self.geometry_type = self.LINE

        geometry_type = self.geometry_type

        if not self.road_id:
            errors["road"] = "Road is required for structures."

        if self.section_id and self.road_id and self.section.road_id != self.road_id:
            errors["section"] = "Selected section must belong to the chosen road."

        if category in {"Bridge", "Culvert", "Ford"} and geometry_type != self.POINT:
            errors["geometry_type"] = "Bridge, Culvert, and Ford structures must use point geometry."
        if category in {"Retaining Wall", "Gabion Wall"} and geometry_type != self.LINE:
            errors["geometry_type"] = "Retaining Wall and Gabion Wall structures must use line geometry."

        road_length = float(self.road.total_length_km) if getattr(self, "road", None) else None

        if geometry_type == self.POINT:
            if self.station_km is None:
                errors["station_km"] = "Station km is required for point structures."
            if self.start_chainage_km is not None:
                errors["start_chainage_km"] = "Start chainage is only applicable to line structures."
            if self.end_chainage_km is not None:
                errors["end_chainage_km"] = "End chainage is only applicable to line structures."
            if self.location_line:
                errors["location_line"] = "Line geometry is only applicable to line structures."
            if self.station_km is not None:
                if self.station_km < 0:
                    errors["station_km"] = "Station chainage cannot be negative."
                if road_length is not None and float(self.station_km) > road_length:
                    errors["station_km"] = "Station chainage must be within the parent road range."

            if self.section_id and self.station_km is not None:
                start = self.section.start_chainage_km
                end = self.section.end_chainage_km
                if self.station_km < start or self.station_km > end:
                    errors["station_km"] = "Station chainage must fall inside the selected section."

            if not self.section_id and self.station_km is not None and self.road_id and "station_km" not in errors:
                matching_section = RoadSection.objects.filter(
                    road=self.road,
                    start_chainage_km__lte=self.station_km,
                    end_chainage_km__gte=self.station_km,
                ).first()
                if matching_section:
                    self.section = matching_section
                else:
                    errors["section"] = "No section covers this station chainage."

        elif geometry_type == self.LINE:
            if self.start_chainage_km is None:
                errors["start_chainage_km"] = "Start chainage km is required for line structures."
            if self.end_chainage_km is None:
                errors["end_chainage_km"] = "End chainage km is required for line structures."
            if self.station_km is not None:
                errors["station_km"] = "Station km is only applicable to point structures."
            if self.location_point:
                errors["location_point"] = "Point geometry is only applicable to point structures."
            if self.location_latitude is not None:
                errors["location_latitude"] = "Latitude is only applicable to point structures."
            if self.location_longitude is not None:
                errors["location_longitude"] = "Longitude is only applicable to point structures."

            if (
                self.start_chainage_km is not None
                and self.end_chainage_km is not None
                and self.end_chainage_km <= self.start_chainage_km
            ):
                errors["end_chainage_km"] = "End chainage must be greater than start chainage."

            if self.start_chainage_km is not None:
                if self.start_chainage_km < 0:
                    errors["start_chainage_km"] = "Start chainage outside parent road range."
                elif road_length is not None and float(self.start_chainage_km) > road_length:
                    errors["start_chainage_km"] = "Start chainage outside parent road range."

            if self.end_chainage_km is not None and "end_chainage_km" not in errors:
                if self.end_chainage_km < 0:
                    errors["end_chainage_km"] = "End chainage outside parent road range."
                elif road_length is not None and float(self.end_chainage_km) > road_length:
                    errors["end_chainage_km"] = "End chainage outside parent road range."

            if (
                self.section_id
                and self.start_chainage_km is not None
                and self.end_chainage_km is not None
                and "start_chainage_km" not in errors
                and "end_chainage_km" not in errors
            ):
                start = self.section.start_chainage_km
                end = self.section.end_chainage_km
                if self.start_chainage_km < start or self.end_chainage_km > end:
                    errors["start_chainage_km"] = "Line structure must fit inside selected section."

            if (
                not self.section_id
                and self.road_id
                and self.start_chainage_km is not None
                and self.end_chainage_km is not None
                and "start_chainage_km" not in errors
                and "end_chainage_km" not in errors
            ):
                matching_section = RoadSection.objects.filter(
                    road=self.road,
                    start_chainage_km__lte=self.start_chainage_km,
                    end_chainage_km__gte=self.end_chainage_km,
                ).first()
                if matching_section:
                    self.section = matching_section
                else:
                    errors["section"] = "No section covers the requested chainage range."

        if errors:
            raise ValidationError(errors)

    def _populate_geometry_fields(self) -> None:
        base_geometry = getattr(self.road, "geometry", None)

        if self.geometry_type == self.POINT:
            self.start_chainage_km = None
            self.end_chainage_km = None
            self.location_point = None
            self.location_line = None
            if base_geometry is not None and self.station_km is not None:
                sliced = slice_linestring_by_chainage(
                    base_geometry,
                    float(self.station_km),
                    float(self.station_km) + 0.0001,
                )
                start_point = sliced.get("start_point") if sliced else None
                self.location_point = make_point(*start_point) if start_point else None
        elif self.geometry_type == self.LINE:
            self.station_km = None
            self.location_point = None
            self.location_latitude = None
            self.location_longitude = None
            self.location_line = None
            if base_geometry is not None and self.start_chainage_km is not None and self.end_chainage_km is not None:
                sliced = slice_linestring_by_chainage(
                    base_geometry,
                    float(self.start_chainage_km),
                    float(self.end_chainage_km),
                )
                self.location_line = sliced.get("geometry") if sliced else None

    def save(self, *args, **kwargs):
        self.full_clean()
        self._populate_geometry_fields()
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        if self.geometry_type == self.LINE:
            return f"{self.structure_category} from {self.start_chainage_km} to {self.end_chainage_km} km on road {self.road_id}"
        return f"{self.structure_category} at {self.station_km} km on road {self.road_id}"


class BridgeDetail(models.Model):
    """
    Detailed attributes for bridge structures.

    Parent record lives in StructureInventory with structure_category='Bridge'.
    """

    structure = models.OneToOneField(
        StructureInventory,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"structure_category": "Bridge"},
    )

    BRIDGE_TYPE_CHOICES = [
        ("Concrete", "Concrete Bridge"),
        ("Stone", "Stone Bridge"),
        ("Bailey", "Bailey Bridge"),
        ("Steel", "Steel Bridge"),
        ("Timber", "Timber Bridge"),
    ]

    bridge_type = models.CharField(
        max_length=20,
        choices=BRIDGE_TYPE_CHOICES,
        help_text="Type of bridge",
    )

    # “Number of spans” (SRAD: dropdown 1–5… UI handles the choices)
    span_count = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of spans",
    )

    # Width (m)
    width_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Deck width (m)",
    )

    # Length (m)
    length_m = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total bridge length (m)",
    )

    # Head walls (Yes/No)
    has_head_walls = models.BooleanField(
        default=False,
        help_text="Head walls present",
    )

    class Meta:
        verbose_name = "Bridge detail"
        verbose_name_plural = "Bridge details"

    def __str__(self) -> str:  # pragma: no cover
        return f"Bridge detail for structure {self.structure_id}"


class CulvertDetail(models.Model):
    structure = models.OneToOneField(
        StructureInventory,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"structure_category": "Culvert"},
    )
    culvert_type = models.CharField(
        max_length=20,
        choices=[
            ("Slab Culvert", "Slab Culvert"),
            ("Box Culvert", "Box Culvert"),
            ("Pipe Culvert", "Pipe Culvert"),
        ],
        help_text="Type of culvert",
    )
    width_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Width (slab/box culverts)",
    )
    span_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Span (slab/box culverts)",
    )
    clear_height_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Clear height (slab/box culverts)",
    )
    num_pipes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of pipes (pipe culvert)",
    )
    pipe_diameter_m = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Pipe diameter (m)",
    )
    has_head_walls = models.BooleanField(default=False, help_text="Head walls present")

    def clean(self):
        super().clean()

        slab_box_fields = ("width_m", "span_m", "clear_height_m")
        pipe_fields = ("num_pipes", "pipe_diameter_m")
        errors = {}

        if self.culvert_type in {"Slab Culvert", "Box Culvert"}:
            for field in slab_box_fields:
                if getattr(self, field) in (None, ""):
                    errors[field] = "Required for slab/box culverts"
            for field in pipe_fields:
                if getattr(self, field):
                    setattr(self, field, None)

        if self.culvert_type == "Pipe Culvert":
            for field in pipe_fields:
                if getattr(self, field) in (None, ""):
                    errors[field] = "Required for pipe culverts"
            for field in slab_box_fields:
                if getattr(self, field):
                    setattr(self, field, None)

        if errors:
            raise ValidationError(errors)

    class Meta:
        verbose_name = "Culvert detail"
        verbose_name_plural = "Culvert details"

    def __str__(self) -> str:  # pragma: no cover
        return f"Culvert detail for structure {self.structure_id}"


class FordDetail(models.Model):
    structure = models.OneToOneField(
        StructureInventory,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"structure_category": "Ford"},
    )

    class Meta:
        verbose_name = "Ford detail"
        verbose_name_plural = "Ford details"

    def __str__(self) -> str:  # pragma: no cover
        return f"Ford detail for structure {self.structure_id}"


class RetainingWallDetail(models.Model):
    structure = models.OneToOneField(
        StructureInventory,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"structure_category": "Retaining Wall"},
    )

    class Meta:
        verbose_name = "Retaining wall detail"
        verbose_name_plural = "Retaining wall details"

    def __str__(self) -> str:  # pragma: no cover
        return f"Retaining wall detail for structure {self.structure_id}"


class GabionWallDetail(models.Model):
    structure = models.OneToOneField(
        StructureInventory,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"structure_category": "Gabion Wall"},
    )

    class Meta:
        verbose_name = "Gabion wall detail"
        verbose_name_plural = "Gabion wall details"

    def __str__(self) -> str:  # pragma: no cover
        return f"Gabion wall detail for structure {self.structure_id}"


class FurnitureInventory(models.Model):
    KM_POST = "KM Post"
    ROAD_SIGN = "Road Sign"
    GUARD_POST = "Guard Post"
    GUARD_RAIL = "Guard Rail"

    POINT_FURNITURE = {KM_POST, ROAD_SIGN}
    LINEAR_FURNITURE = {GUARD_POST, GUARD_RAIL}

    section = models.ForeignKey(RoadSection, on_delete=models.CASCADE, related_name="furniture")
    furniture_type = models.CharField(
        max_length=20,
        choices=[
            (GUARD_POST, "Guard Post"),
            (GUARD_RAIL, "Guard Rail"),
            (KM_POST, "KM Post"),
            (ROAD_SIGN, "Road Sign"),
        ],
        help_text="Furniture category",
    )
    chainage_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    chainage_from_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    chainage_to_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    left_present = models.BooleanField(default=False)
    right_present = models.BooleanField(default=False)
    location_point = PointField(null=True, blank=True, help_text="Optional GPS location of the furniture")
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Furniture inventory"
        verbose_name_plural = "Furniture inventories"

    def clean(self) -> None:
        super().clean()

        errors = {}
        section = self.section
        start_chainage = getattr(section, "start_chainage_km", None)
        end_chainage = getattr(section, "end_chainage_km", None)

        if self.furniture_type in self.POINT_FURNITURE:
            if self.chainage_km is None:
                errors["chainage_km"] = "chainage_km is required for point furniture."
            if self.chainage_from_km is not None:
                errors["chainage_from_km"] = "chainage_from_km is not allowed for point furniture."
            if self.chainage_to_km is not None:
                errors["chainage_to_km"] = "chainage_to_km is not allowed for point furniture."
            if self.left_present or self.right_present:
                errors["left_present"] = "left/right flags are not allowed for point furniture."

            if section and self.chainage_km is not None:
                if start_chainage is not None and self.chainage_km < start_chainage:
                    errors["chainage_km"] = "chainage_km must be within the section bounds."
                if end_chainage is not None and self.chainage_km > end_chainage:
                    errors["chainage_km"] = "chainage_km must be within the section bounds."

        elif self.furniture_type in self.LINEAR_FURNITURE:
            if self.chainage_km is not None:
                errors["chainage_km"] = "chainage_km is not allowed for linear furniture."
            if self.chainage_from_km is None:
                errors["chainage_from_km"] = "chainage_from_km is required for linear furniture."
            if self.chainage_to_km is None:
                errors["chainage_to_km"] = "chainage_to_km is required for linear furniture."
            if not (self.left_present or self.right_present):
                errors["left_present"] = "At least one side (left/right) must be marked as present."
            if (
                self.chainage_from_km is not None
                and self.chainage_to_km is not None
                and self.chainage_from_km > self.chainage_to_km
            ):
                errors["chainage_from_km"] = "chainage_from_km cannot exceed chainage_to_km."

            if section and self.chainage_from_km is not None and self.chainage_to_km is not None:
                if start_chainage is not None and (
                    self.chainage_from_km < start_chainage or self.chainage_to_km < start_chainage
                ):
                    errors["chainage_from_km"] = "Chainages must be within the section bounds."
                if end_chainage is not None and (
                    self.chainage_from_km > end_chainage or self.chainage_to_km > end_chainage
                ):
                    errors["chainage_to_km"] = "Chainages must be within the section bounds."
        else:
            errors["furniture_type"] = "Invalid furniture type."

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.furniture_type} on section {self.section_id}"


# ---------------------------------------------------------------------------
# Survey models
# ---------------------------------------------------------------------------


class StructureConditionSurvey(models.Model):
    structure = models.ForeignKey(StructureInventory, on_delete=models.CASCADE, related_name="surveys")
    survey_year = models.PositiveIntegerField(help_text="Year of survey")
    condition_code = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Overall condition rating code (1=Good, 4=Poor)",
    )
    condition_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Overall condition (Good/Fair/Poor/Bad)",
    )
    inspector_name = models.CharField(max_length=150, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    comments = models.TextField(blank=True)
    attachments = models.JSONField(null=True, blank=True)
    qa_status = models.ForeignKey(QAStatus, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Structure condition survey"
        verbose_name_plural = "Structure condition surveys"

    def __str__(self) -> str:  # pragma: no cover
        return f"Structure survey {self.id} ({self.structure_id})"


class StructureConditionLookup(models.Model):
    code = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200)

    class Meta:
        ordering = ["code"]
        verbose_name = "Structure condition lookup"
        verbose_name_plural = "Structure condition lookups"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"{self.code} - {self.name}"


class BridgeConditionSurvey(models.Model):
    structure_survey = models.OneToOneField(
        StructureConditionSurvey,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"structure__structure_category": "Bridge"},
    )
    deck_condition = models.PositiveSmallIntegerField(null=True, blank=True)
    abutment_condition = models.PositiveSmallIntegerField(null=True, blank=True)
    pier_condition = models.PositiveSmallIntegerField(null=True, blank=True)
    wearing_surface = models.PositiveSmallIntegerField(null=True, blank=True)
    expansion_joint_ok = models.BooleanField(default=False, help_text="Expansion joint present/OK")
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Bridge condition survey"
        verbose_name_plural = "Bridge condition surveys"

    def __str__(self) -> str:  # pragma: no cover
        return f"Bridge survey details {self.structure_survey_id}"


class CulvertConditionSurvey(models.Model):
    structure_survey = models.OneToOneField(
        StructureConditionSurvey,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"structure__structure_category": "Culvert"},
    )
    inlet_condition = models.PositiveSmallIntegerField(null=True, blank=True)
    outlet_condition = models.PositiveSmallIntegerField(null=True, blank=True)
    barrel_condition = models.PositiveSmallIntegerField(null=True, blank=True)
    headwall_condition = models.PositiveSmallIntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Culvert condition survey"
        verbose_name_plural = "Culvert condition surveys"

    def __str__(self) -> str:  # pragma: no cover
        return f"Culvert survey details {self.structure_survey_id}"


class OtherStructureConditionSurvey(models.Model):
    structure_survey = models.OneToOneField(StructureConditionSurvey, on_delete=models.CASCADE, primary_key=True)
    wall_condition = models.PositiveSmallIntegerField(null=True, blank=True)
    ford_condition = models.PositiveSmallIntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Other structure condition survey"
        verbose_name_plural = "Other structure condition surveys"

    def __str__(self) -> str:  # pragma: no cover
        return f"Other structure survey details {self.structure_survey_id}"


# ---------------------------------------------------------------------------
# MCI Lookup models
# ---------------------------------------------------------------------------


class ConditionFactorLookup(models.Model):
    class FactorType(models.TextChoices):
        DRAINAGE = "drainage", "Drainage Condition"
        SHOULDER = "shoulder", "Shoulder Condition"
        SURFACE = "surface", "Surface Condition"

    CONDITION_FACTOR_TYPES = [
        (FactorType.DRAINAGE, FactorType.DRAINAGE.label),
        (FactorType.SHOULDER, FactorType.SHOULDER.label),
        (FactorType.SURFACE, FactorType.SURFACE.label),
    ]

    FACTOR_TYPES = CONDITION_FACTOR_TYPES

    factor_type = models.CharField(max_length=20, choices=FACTOR_TYPES)
    rating = models.PositiveSmallIntegerField()
    factor_value = models.DecimalField(max_digits=4, decimal_places=2)
    description = models.CharField(max_length=200)

    class Meta:
        unique_together = ("factor_type", "rating")
        ordering = ["factor_type", "rating"]
        verbose_name = "Condition factor"
        verbose_name_plural = "Condition factors"

    def __str__(self):  # pragma: no cover
        return f"{self.factor_type}: R{self.rating} → {self.factor_value}"


class MCIWeightConfig(models.Model):
    name = models.CharField(max_length=100)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    weight_drainage = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0.40"))
    weight_shoulder = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0.20"))
    weight_surface = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0.40"))

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-effective_from"]

    def __str__(self):  # pragma: no cover
        return f"{self.name} ({self.effective_from} – {self.effective_to or 'Present'})"


class MCICategoryLookup(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10)

    mci_min = models.DecimalField(max_digits=5, decimal_places=2)
    mci_max = models.DecimalField(max_digits=5, decimal_places=2)

    severity_order = models.PositiveSmallIntegerField(default=1)

    default_intervention = models.ForeignKey(
        "InterventionWorkItem",
        to_field="work_code",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mci_default_for",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["severity_order", "mci_min"]
        unique_together = ("code", "mci_min", "mci_max")

    def __str__(self):  # pragma: no cover
        return f"{self.name} ({self.code})"

    @classmethod
    def match_for_mci(cls, value):
        return (
            cls.objects.filter(
                is_active=True,
                mci_min__lte=value,
                mci_max__gte=value,
            )
            .order_by("severity_order")
            .first()
        )


class MCIRoadMaintenanceRule(models.Model):
    mci_min = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    mci_max = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    routine = models.BooleanField(default=False)
    periodic = models.BooleanField(default=False)
    rehabilitation = models.BooleanField(default=False)

    priority = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["priority", "mci_min"]
        verbose_name = "MCI road maintenance rule"
        verbose_name_plural = "MCI road maintenance rules"

    def __str__(self):  # pragma: no cover - simple admin label
        return f"MCI {self.mci_min or '-inf'} – {self.mci_max or 'inf'}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.mci_min is not None and self.mci_max is not None and self.mci_min >= self.mci_max:
            raise ValidationError("mci_min must be less than mci_max")

        if not self.is_active:
            return

        qs = MCIRoadMaintenanceRule.objects.filter(is_active=True)
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        overlaps = []
        for other in qs:
            if self._overlaps(other):
                overlaps.append(other)

        if overlaps:
            raise ValidationError("Active rule ranges cannot overlap.")

    def _overlaps(self, other: "MCIRoadMaintenanceRule") -> bool:
        """Half-open range overlap check allowing touching boundaries."""

        lower_a = self.mci_min
        upper_a = self.mci_max
        lower_b = other.mci_min
        upper_b = other.mci_max

        lower_a = lower_a if lower_a is not None else Decimal("-Infinity")
        upper_a = upper_a if upper_a is not None else Decimal("Infinity")
        lower_b = lower_b if lower_b is not None else Decimal("-Infinity")
        upper_b = upper_b if upper_b is not None else Decimal("Infinity")

        return lower_a < upper_b and lower_b < upper_a

    @classmethod
    def match_for_mci(cls, value: Decimal):
        matches = list(
            cls.objects.filter(
                models.Q(mci_min__lte=value) | models.Q(mci_min__isnull=True),
                models.Q(mci_max__gte=value) | models.Q(mci_max__isnull=True),
                is_active=True,
            ).order_by("priority", "mci_min")
        )

        if len(matches) > 1:
            conflicting = ", ".join(str(rule.pk) for rule in matches)
            raise ValueError(
                f"Multiple active MCI road maintenance rules match value {value}: {conflicting}"
            )

        return matches[0] if matches else None


class RoadConditionSurvey(models.Model):
    road_segment = models.ForeignKey("RoadSegment", on_delete=models.CASCADE, related_name="condition_surveys")

    drainage_left = models.ForeignKey(
        ConditionFactorLookup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="drainage_left_surveys",
        limit_choices_to={"factor_type": ConditionFactorLookup.FactorType.DRAINAGE},
    )
    drainage_right = models.ForeignKey(
        ConditionFactorLookup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="drainage_right_surveys",
        limit_choices_to={"factor_type": ConditionFactorLookup.FactorType.DRAINAGE},
    )

    shoulder_left = models.ForeignKey(
        ConditionFactorLookup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="shoulder_left_surveys",
        limit_choices_to={"factor_type": ConditionFactorLookup.FactorType.SHOULDER},
    )
    shoulder_right = models.ForeignKey(
        ConditionFactorLookup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="shoulder_right_surveys",
        limit_choices_to={"factor_type": ConditionFactorLookup.FactorType.SHOULDER},
    )

    surface_condition = models.ForeignKey(
        ConditionFactorLookup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="surface_surveys",
        limit_choices_to={"factor_type": ConditionFactorLookup.FactorType.SURFACE},
    )

    gravel_thickness_mm = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)

    is_there_bottleneck = models.BooleanField(default=False)
    bottleneck_size_m = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    comments = models.TextField(blank=True)
    inspected_by = models.CharField(max_length=150, blank=True)
    inspection_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-inspection_date", "road_segment"]

    def clean(self):
        seg = self.road_segment
        errors = {}

        if seg:
            if not seg.ditch_left_present and self.drainage_left is not None:
                errors["drainage_left"] = (
                    "Left drainage cannot be recorded because this segment has no left ditch."
                )

            if not seg.ditch_right_present and self.drainage_right is not None:
                errors["drainage_right"] = (
                    "Right drainage cannot be recorded because this segment has no right ditch."
                )

            if not seg.shoulder_left_present and self.shoulder_left is not None:
                errors["shoulder_left"] = (
                    "Left shoulder condition cannot be recorded because this segment has no left shoulder."
                )

            if not seg.shoulder_right_present and self.shoulder_right is not None:
                errors["shoulder_right"] = (
                    "Right shoulder condition cannot be recorded because this segment has no right shoulder."
                )

        if not self.is_there_bottleneck and self.bottleneck_size_m is not None:
            errors["bottleneck_size_m"] = "Bottleneck size should be empty when no bottleneck is reported."

        if errors:
            raise ValidationError(errors)


class SegmentMCIResult(models.Model):
    road_segment = models.ForeignKey("RoadSegment", on_delete=models.CASCADE, related_name="mci_results")
    survey = models.OneToOneField(RoadConditionSurvey, on_delete=models.CASCADE, related_name="mci_result")
    weight_config = models.ForeignKey(MCIWeightConfig, on_delete=models.PROTECT)

    survey_date = models.DateField()

    drainage_factor = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    shoulder_factor = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    surface_factor = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    mci_value = models.DecimalField(max_digits=6, decimal_places=2)

    mci_category = models.ForeignKey(
        MCICategoryLookup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="results",
    )

    recommended_intervention = models.ForeignKey(
        "InterventionWorkItem",
        to_field="work_code",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mci_results",
    )

    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-survey_date", "road_segment"]

    @classmethod
    def _get_active_config(cls, on_date=None):
        from datetime import date

        on_date = on_date or date.today()

        return (
            MCIWeightConfig.objects.filter(is_active=True, effective_from__lte=on_date)
            .filter(models.Q(effective_to__gte=on_date) | models.Q(effective_to__isnull=True))
            .order_by("-effective_from")
            .first()
        )

    @classmethod
    def create_from_survey(cls, survey, config=None):
        if survey is None:
            raise ValueError("Survey cannot be None")

        if config is None:
            config = cls._get_active_config(survey.inspection_date)
            if config is None:
                raise ValueError("No active MCIWeightConfig found for this survey date")

        segment = survey.road_segment

        drainage_values = []
        if segment.ditch_left_present and survey.drainage_left:
            drainage_values.append(Decimal(survey.drainage_left.factor_value))
        if segment.ditch_right_present and survey.drainage_right:
            drainage_values.append(Decimal(survey.drainage_right.factor_value))
        drainage_factor = sum(drainage_values) / len(drainage_values) if drainage_values else None

        shoulder_values = []
        if segment.shoulder_left_present and survey.shoulder_left:
            shoulder_values.append(Decimal(survey.shoulder_left.factor_value))
        if segment.shoulder_right_present and survey.shoulder_right:
            shoulder_values.append(Decimal(survey.shoulder_right.factor_value))
        shoulder_factor = sum(shoulder_values) / len(shoulder_values) if shoulder_values else None

        surface_factor = (
            Decimal(survey.surface_condition.factor_value) if survey.surface_condition else None
        )

        mci_value = (
            (drainage_factor or Decimal("0")) * config.weight_drainage
            + (shoulder_factor or Decimal("0")) * config.weight_shoulder
            + (surface_factor or Decimal("0")) * config.weight_surface
        )

        category = MCICategoryLookup.match_for_mci(mci_value) if mci_value is not None else None
        recommended = category.default_intervention if category else None

        obj, _ = cls.objects.update_or_create(
            survey=survey,
            defaults={
                "road_segment": survey.road_segment,
                "weight_config": config,
                "survey_date": survey.inspection_date,
                "drainage_factor": drainage_factor,
                "shoulder_factor": shoulder_factor,
                "surface_factor": surface_factor,
                "mci_value": mci_value,
                "mci_category": category,
                "recommended_intervention": recommended,
            },
        )

        return obj
    
    @classmethod
    def create_or_update_from_survey(cls, survey, config=None):
        """
        Wrapper required by compute_mci command.
        Calls create_from_survey() which already does update_or_create().
        """
        return cls.create_from_survey(survey, config=config)


class SegmentInterventionRecommendation(models.Model):
    segment = models.ForeignKey(
        "RoadSegment",
        on_delete=models.CASCADE,
        related_name="intervention_recommendations",
    )
    mci_value = models.DecimalField(max_digits=6, decimal_places=2)
    recommended_item = models.ForeignKey(
        "InterventionWorkItem",
        on_delete=models.PROTECT,
        related_name="segment_recommendations",
    )
    calculated_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["segment_id", "recommended_item__work_code"]
        unique_together = ("segment", "recommended_item")
        verbose_name = "Segment intervention recommendation"
        verbose_name_plural = "Segment intervention recommendations"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        code = getattr(self.recommended_item, "work_code", self.recommended_item_id)
        return f"{self.segment_id} → {code}"


class StructureConditionInterventionRule(models.Model):
    class StructureType(models.TextChoices):
        BRIDGE = "bridge", "Bridge"
        CULVERT = "culvert", "Culvert"
        DRIFT = "drift", "Drift"
        VENTED_DRIFT = "vented_drift", "Vented drift"
        OTHER = "other", "Other"

    structure_type = models.CharField(max_length=20, choices=StructureType.choices)
    condition = models.ForeignKey(
        "StructureConditionLookup",
        on_delete=models.PROTECT,
        related_name="intervention_rules",
    )
    intervention_item = models.ForeignKey(
        "InterventionWorkItem",
        to_field="work_code",
        on_delete=models.PROTECT,
        related_name="structure_rules",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("structure_type", "condition")
        verbose_name = "Structure condition intervention rule"
        verbose_name_plural = "Structure condition intervention rules"
        ordering = ["structure_type", "condition__code"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        cond = getattr(self.condition, "code", "?")
        return f"{self.structure_type} → {cond}"


class StructureInterventionRecommendation(models.Model):
    structure = models.ForeignKey(
        StructureInventory,
        on_delete=models.CASCADE,
        related_name="structure_recommendations",
    )
    structure_type = models.CharField(max_length=20, choices=StructureConditionInterventionRule.StructureType.choices)
    condition_code = models.PositiveSmallIntegerField()
    recommended_item = models.ForeignKey(
        "InterventionWorkItem",
        to_field="work_code",
        on_delete=models.PROTECT,
        related_name="structure_recommendations",
    )
    calculated_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["structure_type", "recommended_item__work_code"]
        unique_together = ("structure", "recommended_item")
        verbose_name = "Structure intervention recommendation"
        verbose_name_plural = "Structure intervention recommendations"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        code = getattr(self.recommended_item, "work_code", self.recommended_item_id)
        return f"{self.structure_id} → {code}"


class SegmentInterventionNeed(models.Model):
    segment = models.ForeignKey(RoadSegment, on_delete=models.CASCADE, related_name="intervention_needs")
    fiscal_year = models.PositiveIntegerField(help_text="Fiscal year for which the need is recorded")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Segment intervention need"
        verbose_name_plural = "Segment intervention needs"
        unique_together = ("segment", "fiscal_year")

    def __str__(self) -> str:  # pragma: no cover
        return f"Need for segment {self.segment_id} ({self.fiscal_year})"


class SegmentInterventionNeedItem(models.Model):
    need = models.ForeignKey(
        SegmentInterventionNeed, on_delete=models.CASCADE, related_name="items"
    )
    intervention_item = models.ForeignKey(
        InterventionWorkItem, on_delete=models.PROTECT, related_name="segment_need_items"
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Segment intervention need item"
        verbose_name_plural = "Segment intervention need items"

    def __str__(self) -> str:  # pragma: no cover
        return f"Segment need item {self.intervention_item_id}"


class StructureInterventionNeed(models.Model):
    structure = models.ForeignKey(
        StructureInventory, on_delete=models.CASCADE, related_name="intervention_needs"
    )
    fiscal_year = models.PositiveIntegerField(help_text="Fiscal year for which the need is recorded")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Structure intervention need"
        verbose_name_plural = "Structure intervention needs"
        unique_together = ("structure", "fiscal_year")

    def __str__(self) -> str:  # pragma: no cover
        return f"Need for structure {self.structure_id} ({self.fiscal_year})"


class StructureInterventionNeedItem(models.Model):
    need = models.ForeignKey(
        StructureInterventionNeed, on_delete=models.CASCADE, related_name="items"
    )
    intervention_item = models.ForeignKey(
        InterventionWorkItem, on_delete=models.PROTECT, related_name="structure_need_items"
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Structure intervention need item"
        verbose_name_plural = "Structure intervention need items"

    def __str__(self) -> str:  # pragma: no cover
        return f"Structure need item {self.intervention_item_id}"


class FurnitureConditionSurvey(models.Model):
    furniture = models.ForeignKey(FurnitureInventory, on_delete=models.CASCADE, related_name="surveys")
    survey_year = models.PositiveIntegerField()
    condition_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    comments = models.TextField(blank=True)
    inspected_by = models.CharField(max_length=150, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    qa_status = models.ForeignKey(QAStatus, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Furniture condition survey"
        verbose_name_plural = "Furniture condition surveys"

    def __str__(self) -> str:  # pragma: no cover
        return f"Furniture survey {self.id} ({self.furniture_id})"


class RoadConditionDetailedSurvey(models.Model):
    """Detailed severity/extent survey for a road segment."""

    SURVEY_LEVEL_CHOICES = [("network", "Network"), ("detailed", "Detailed")]
    QUANTITY_UNIT_CHOICES = [("m3", "m³"), ("m2", "m²"), ("m", "m"), ("km", "km")]
    QUANTITY_SOURCE_CHOICES = [("lookup", "Lookup"), ("manual_override", "Manual override")]

    survey_level = models.CharField(max_length=10, choices=SURVEY_LEVEL_CHOICES)
    awp = models.ForeignKey(
        "AnnualWorkPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="road_detailed_surveys",
    )
    road_segment = models.ForeignKey(RoadSegment, on_delete=models.CASCADE, related_name="detailed_surveys")
    distress = models.ForeignKey(DistressType, on_delete=models.PROTECT, related_name="road_surveys")
    distress_condition = models.ForeignKey(
        DistressCondition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="road_surveys",
    )
    severity_code = models.PositiveSmallIntegerField(choices=DistressCondition.SEVERITY_CHOICES, null=True, blank=True)
    extent_code = models.PositiveSmallIntegerField(choices=DistressCondition.EXTENT_CHOICES, null=True, blank=True)
    extent_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    distress_length_m = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    distress_area_m2 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    distress_volume_m3 = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    observed_gravel_thickness_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    carriageway_width_m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    shoulder_width_left_m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    shoulder_width_right_m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ditch_left_present = models.BooleanField(default=False, null=True, blank=True)
    ditch_right_present = models.BooleanField(default=False, null=True, blank=True)
    activity = models.ForeignKey(ActivityLookup, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_unit = models.CharField(max_length=4, choices=QUANTITY_UNIT_CHOICES, null=True, blank=True)
    quantity_estimated = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    quantity_source = models.CharField(max_length=20, choices=QUANTITY_SOURCE_CHOICES, default="lookup")
    severity_notes = models.TextField(blank=True)
    inspected_by = models.CharField(max_length=150, null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    comments = models.TextField(blank=True)
    qa_status = models.ForeignKey(QAStatus, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Road condition detailed survey"
        verbose_name_plural = "Road condition detailed surveys"
        ordering = ["-inspection_date", "road_segment_id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Road detailed survey {self.id} ({self.road_segment_id})"


class StructureConditionDetailedSurvey(models.Model):
    """Detailed severity survey for a structure asset."""

    SURVEY_LEVEL_CHOICES = [("network", "Network"), ("detailed", "Detailed")]
    QUANTITY_UNIT_CHOICES = [("m3", "m³"), ("m2", "m²"), ("item", "item")]

    survey_level = models.CharField(max_length=10, choices=SURVEY_LEVEL_CHOICES)
    awp = models.ForeignKey(
        "AnnualWorkPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="structure_detailed_surveys",
    )
    structure = models.ForeignKey(
        StructureInventory,
        on_delete=models.CASCADE,
        related_name="detailed_surveys",
    )
    distress = models.ForeignKey(DistressType, on_delete=models.PROTECT, related_name="structure_surveys")
    distress_condition = models.ForeignKey(
        DistressCondition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="structure_surveys",
    )
    severity_code = models.PositiveSmallIntegerField(choices=DistressCondition.SEVERITY_CHOICES)
    extent_code = models.PositiveSmallIntegerField(choices=DistressCondition.EXTENT_CHOICES, null=True, blank=True)
    distress_length_m = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    distress_area_m2 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    distress_volume_m3 = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    check_dam_count = models.IntegerField(null=True, blank=True)
    activity = models.ForeignKey(ActivityLookup, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_unit = models.CharField(max_length=4, choices=QUANTITY_UNIT_CHOICES, null=True, blank=True)
    quantity_estimated = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    computed_by_lookup = models.BooleanField(default=True)
    severity_notes = models.TextField(blank=True)
    inspected_by = models.CharField(max_length=150, null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    comments = models.TextField(blank=True)
    qa_status = models.ForeignKey(QAStatus, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Structure condition detailed survey"
        verbose_name_plural = "Structure condition detailed surveys"
        ordering = ["-inspection_date", "structure_id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Structure detailed survey {self.id} ({self.structure_id})"


class FurnitureConditionDetailedSurvey(models.Model):
    """Detailed defect records for road furniture."""

    SURVEY_LEVEL_CHOICES = [("network", "Network"), ("detailed", "Detailed")]
    QUANTITY_UNIT_CHOICES = [("item", "item"), ("m", "m")]

    survey_level = models.CharField(max_length=10, choices=SURVEY_LEVEL_CHOICES)
    awp = models.ForeignKey(
        "AnnualWorkPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="furniture_detailed_surveys",
    )
    furniture = models.ForeignKey(
        FurnitureInventory,
        on_delete=models.CASCADE,
        related_name="detailed_surveys",
    )
    distress = models.ForeignKey(DistressType, on_delete=models.PROTECT, related_name="furniture_surveys")
    distress_condition = models.ForeignKey(
        DistressCondition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="furniture_surveys",
    )
    severity_code = models.PositiveSmallIntegerField(choices=DistressCondition.SEVERITY_CHOICES)
    extent_code = models.PositiveSmallIntegerField(choices=DistressCondition.EXTENT_CHOICES, null=True, blank=True)
    quantity_unit = models.CharField(max_length=4, choices=QUANTITY_UNIT_CHOICES, null=True, blank=True)
    quantity_estimated = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    activity = models.ForeignKey(ActivityLookup, on_delete=models.SET_NULL, null=True, blank=True)
    computed_by_lookup = models.BooleanField(default=True)
    severity_notes = models.TextField(blank=True)
    inspected_by = models.CharField(max_length=150, null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    comments = models.TextField(blank=True)
    qa_status = models.ForeignKey(QAStatus, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Furniture condition detailed survey"
        verbose_name_plural = "Furniture condition detailed surveys"
        ordering = ["-inspection_date", "furniture_id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Furniture detailed survey {self.id} ({self.furniture_id})"


# ---------------------------------------------------------------------------
# Traffic monitoring models
# ---------------------------------------------------------------------------


class TrafficSurvey(models.Model):
    road_segment = models.ForeignKey(
        RoadSegment, on_delete=models.CASCADE, related_name="legacy_traffic_surveys"
    )
    survey_year = models.PositiveIntegerField()
    cycle_number = models.PositiveSmallIntegerField(help_text="Economic season cycle (1,2,3)")
    count_start_date = models.DateField(null=True, blank=True)
    count_end_date = models.DateField(null=True, blank=True)
    count_days_per_cycle = models.PositiveSmallIntegerField(default=7, help_text="# of days counted per cycle")
    count_hours_per_day = models.PositiveSmallIntegerField(default=12, help_text="Hours counted per day")
    night_adjustment_factor = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal("1.330"))
    method = models.CharField(
        max_length=20,
        choices=[
            ("MOC", "Manual (Classified)"),
            ("MTS", "Manual (Tally Sheet)"),
            ("Automated", "Automated Counter"),
            ("Other", "Other"),
        ],
        help_text="Traffic counting method",
    )
    observer = models.CharField(max_length=150, blank=True, help_text="Observer/team name")
    location_override = PointField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Optional GPS point if not exactly at segment center",
    )
    weather_notes = models.CharField(max_length=100, blank=True)
    qa_status = models.CharField(
        max_length=10,
        choices=[("Draft", "Draft"), ("In Review", "In Review"), ("Approved", "Approved"), ("Rejected", "Rejected")],
        default="Draft",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Traffic survey"
        verbose_name_plural = "Traffic surveys"

    def __str__(self) -> str:  # pragma: no cover
        return f"TrafficSurvey {self.id} (Yr {self.survey_year}, Segment {self.road_segment_id})"


class TrafficCountRecord(models.Model):
    traffic_survey = models.ForeignKey(TrafficSurvey, on_delete=models.CASCADE, related_name="count_records")
    road_segment = models.ForeignKey(RoadSegment, on_delete=models.CASCADE)
    count_date = models.DateField()
    time_block_from = models.TimeField(null=True, blank=True)
    time_block_to = models.TimeField(null=True, blank=True)
    vehicle_class = models.CharField(
        max_length=20,
        choices=[
            ("Car", "Car"),
            ("LightGoods", "LightGoods"),
            ("MiniBus", "MiniBus"),
            ("MediumGoods", "MediumGoods"),
            ("HeavyGoods", "HeavyGoods"),
            ("Bus", "Bus"),
            ("Tractor", "Tractor"),
            ("Motorcycle", "Motorcycle"),
            ("Bicycle", "Bicycle"),
            ("Pedestrian", "Pedestrian"),
        ],
        help_text="Vehicle classification counted",
    )
    count_value = models.PositiveIntegerField(default=0, help_text="Observed count for this class/time")
    is_market_day = models.BooleanField(default=False, help_text="Market day indicator for this count")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Traffic count record"
        verbose_name_plural = "Traffic count records"

    def __str__(self) -> str:  # pragma: no cover
        return f"TrafficCountRecord {self.id} ({self.vehicle_class})"


class TrafficCycleSummary(models.Model):
    traffic_survey = models.ForeignKey(TrafficSurvey, on_delete=models.CASCADE, related_name="cycle_summaries")
    road_segment = models.ForeignKey(RoadSegment, on_delete=models.CASCADE)
    vehicle_class = models.CharField(max_length=20, choices=TrafficCountRecord._meta.get_field("vehicle_class").choices)
    cycle_number = models.PositiveSmallIntegerField()
    cycle_days_counted = models.PositiveIntegerField(help_text="Days counted in this cycle")
    cycle_sum_count = models.BigIntegerField(help_text="Total vehicle count in cycle")
    cycle_daily_avg = models.DecimalField(max_digits=10, decimal_places=3, help_text="Average count/day in cycle")
    cycle_daily_24hr = models.DecimalField(max_digits=12, decimal_places=3, help_text="Daily count adjusted to 24h")
    cycle_pcu = models.DecimalField(max_digits=12, decimal_places=3, help_text="Daily PCU for this class")
    qc_flag = models.TextField(blank=True, help_text="Quality control notes/flags")

    class Meta:
        verbose_name = "Traffic cycle summary"
        verbose_name_plural = "Traffic cycle summaries"
        unique_together = ("traffic_survey", "vehicle_class", "cycle_number")

    def __str__(self) -> str:  # pragma: no cover
        return f"Cycle summary {self.traffic_survey_id} ({self.vehicle_class})"


class TrafficSurveySummary(models.Model):
    traffic_survey = models.ForeignKey(TrafficSurvey, on_delete=models.CASCADE, related_name="survey_summary")
    road_segment = models.ForeignKey(RoadSegment, on_delete=models.CASCADE)
    vehicle_class = models.CharField(max_length=20, choices=TrafficCountRecord._meta.get_field("vehicle_class").choices)
    avg_daily_count_all_cycles = models.DecimalField(max_digits=12, decimal_places=3)
    adt_class = models.DecimalField(max_digits=12, decimal_places=3, help_text="Annual daily traffic for this class")
    pcu_class = models.DecimalField(max_digits=12, decimal_places=3, help_text="ADT * PCU factor (this class)")
    adt_total = models.DecimalField(max_digits=12, decimal_places=3, help_text="Sum of ADT across classes")
    pcu_total = models.DecimalField(max_digits=14, decimal_places=3, help_text="Sum of PCU across classes")
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, help_text="Data confidence (0–100)")
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Traffic survey summary"
        verbose_name_plural = "Traffic survey summaries"

    def __str__(self) -> str:  # pragma: no cover
        return f"Survey summary {self.traffic_survey_id} ({self.vehicle_class})"


class TrafficQC(models.Model):
    traffic_survey = models.ForeignKey(TrafficSurvey, on_delete=models.CASCADE, related_name="qc_issues")
    road_segment = models.ForeignKey(RoadSegment, on_delete=models.CASCADE)
    issue_type = models.CharField(max_length=100, help_text="Type of issue (e.g. 'Missing Day', 'Spike')")
    issue_detail = models.TextField(help_text="Detailed description of the issue")
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Traffic quality check"
        verbose_name_plural = "Traffic quality checks"

    def __str__(self) -> str:  # pragma: no cover
        return f"Traffic QC {self.id}: {self.issue_type}"


class TrafficForPrioritization(models.Model):
    road = models.ForeignKey(Road, on_delete=models.CASCADE)
    road_segment = models.ForeignKey(RoadSegment, on_delete=models.CASCADE, null=True, blank=True)
    fiscal_year = models.PositiveIntegerField(null=True, blank=True)
    value_type = models.CharField(max_length=3, choices=[("ADT", "ADT"), ("PCU", "PCU")])
    value = models.DecimalField(max_digits=14, decimal_places=3, help_text="Numeric ADT or PCU used")
    source_survey = models.ForeignKey(TrafficSurvey, on_delete=models.SET_NULL, null=True, blank=True)
    prepared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Traffic for prioritization record"
        verbose_name_plural = "Traffic for prioritization records"
        unique_together = ("road", "fiscal_year", "value_type", "road_segment")

    def __str__(self) -> str:  # pragma: no cover
        return f"Traffic {self.road_id} {self.fiscal_year} {self.value_type}"


class BenefitCategory(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100, unique=True)
    weight = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        verbose_name = "Benefit category"
        verbose_name_plural = "Benefit categories"
        ordering = ["code"]

    def clean(self):
        if not (Decimal("0") < self.weight <= Decimal("1")):
            raise ValidationError({"weight": "Category weight must be between 0 and 1."})

    @property
    def max_score(self):
        return int(self.weight * 100)

    def __str__(self):
        return f"{self.code} ({self.max_score} pts)"

class BenefitCriterion(models.Model):
    class ScoringMethod(models.TextChoices):
        RANGE = "RANGE", "Range"
        LOOKUP = "LOOKUP", "Lookup"

    category = models.ForeignKey(BenefitCategory, on_delete=models.CASCADE, related_name="criteria")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=150)
    weight = models.DecimalField(max_digits=4, decimal_places=2)
    scoring_method = models.CharField(max_length=10, choices=ScoringMethod.choices)

    class Meta:
        unique_together = ("category", "code")

    def clean(self):
        if not (Decimal("0") < self.weight <= Decimal("1")):
            raise ValidationError({"weight": "Criterion weight must be between 0 and 1."})

    @property
    def max_score(self):
        """Criterion contributes weight*100 to the overall 100-point system."""
        return int(self.weight * 100)

    def __str__(self):
        return f"{self.code}: {self.name} ({self.max_score} pts)"


class BenefitCriterionScale(models.Model):
    criterion = models.ForeignKey(BenefitCriterion, on_delete=models.CASCADE, related_name="scales")
    min_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    score = models.PositiveIntegerField()
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["criterion", "min_value", "max_value"]),
        ]

    def clean(self):
        errors = {}

        if self.score > self.criterion.max_score:
            errors["score"] = (
                f"Score {self.score} exceeds criterion max score {self.criterion.max_score}."
            )

        # (Existing validation kept)
        if self.min_value is None and self.max_value is None:
            errors["min_value"] = "At least one boundary is required."

        if self.min_value and self.max_value and self.min_value > self.max_value:
            errors["max_value"] = "min_value cannot exceed max_value."

        # Overlap validation
        if self.criterion_id:
            overlapping = BenefitCriterionScale.objects.filter(criterion=self.criterion).exclude(pk=self.pk)
            for scale in overlapping:
                min_a = self.min_value or Decimal("-Infinity")
                max_a = self.max_value or Decimal("Infinity")
                min_b = scale.min_value or Decimal("-Infinity")
                max_b = scale.max_value or Decimal("Infinity")
                if min_a <= max_b and min_b <= max_a:
                    errors["min_value"] = "Ranges for the same criterion cannot overlap."
                    break

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.criterion.code}: {self.description} → {self.score}"
class RoadSocioEconomic(models.Model):
    """Manual socio-economic inputs captured once per road."""

    road = models.OneToOneField(Road, on_delete=models.CASCADE, related_name="socioeconomic")

    population_served = models.PositiveIntegerField(default=0)

    trading_centers = models.PositiveIntegerField(default=0)
    villages = models.PositiveIntegerField(default=0)
    road_link_type = models.ForeignKey(
        RoadLinkTypeLookup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="socioeconomic_records",
    )
    adt_override = models.PositiveIntegerField(null=True, blank=True)

    farmland_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cooperative_centers = models.PositiveIntegerField(default=0)
    markets = models.PositiveIntegerField(default=0)

    health_centers = models.PositiveIntegerField(default=0)
    education_centers = models.PositiveIntegerField(default=0)
    development_projects = models.PositiveIntegerField(default=0)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Road socio-economic input"
        verbose_name_plural = "Road socio-economic"
        ordering = ["road__road_identifier"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"Socio-economic inputs for {self.road_id}"

    def clean(self):
        errors: dict[str, str] = {}

        if self.population_served is None:
            errors["population_served"] = "Population served is required."
        if self.population_served is not None and self.population_served < 0:
            errors["population_served"] = "Population served must be zero or greater."

        numeric_fields = {
            "trading_centers": self.trading_centers,
            "villages": self.villages,
            "cooperative_centers": self.cooperative_centers,
            "markets": self.markets,
            "health_centers": self.health_centers,
            "education_centers": self.education_centers,
            "development_projects": self.development_projects,
        }
        for field, value in numeric_fields.items():
            if value is not None and value < 0:
                errors[field] = "Value must be zero or greater."

        if self.farmland_percent is not None:
            if not (Decimal("0") <= self.farmland_percent <= Decimal("100")):
                errors["farmland_percent"] = "Farmland percent must be between 0 and 100."

        if self.road_link_type_id is None:
            errors["road_link_type"] = "Road link type is required."

        from traffic.models import TrafficSurveySummary  # avoid circular import

        latest_summary = TrafficSurveySummary.latest_for(self.road) if self.road_id else None
        if latest_summary and self.adt_override is not None:
            errors["adt_override"] = "ADT override not allowed when survey data exists."

        if errors:
            raise ValidationError(errors)


# ---------------------------------------------------------------------------
# Intervention planning & prioritisation
# ---------------------------------------------------------------------------


class StructureIntervention(models.Model):
    structure = models.ForeignKey(StructureInventory, on_delete=models.CASCADE, related_name="planned_interventions")
    intervention = models.ForeignKey(InterventionLookup, on_delete=models.PROTECT)
    required_length_m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    priority_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    intervention_year = models.PositiveIntegerField(help_text="Planned year of intervention")
    status = models.CharField(
        max_length=10,
        choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Completed", "Completed"), ("Deferred", "Deferred")],
        default="Pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Structure intervention"
        verbose_name_plural = "Structure interventions"

    def __str__(self) -> str:  # pragma: no cover
        return f"Structure intervention {self.id} ({self.structure_id})"


class RoadSectionIntervention(models.Model):
    section = models.ForeignKey(RoadSection, on_delete=models.CASCADE, related_name="planned_interventions")
    intervention = models.ForeignKey(InterventionLookup, on_delete=models.PROTECT)
    scope = models.CharField(
        max_length=20,
        choices=[("Full Section", "Full Section"), ("Partial Section", "Partial Section")],
    )
    start_chainage_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    end_chainage_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    length_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, help_text="Length of work")
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    priority_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    intervention_year = models.PositiveIntegerField()
    status = models.CharField(
        max_length=10,
        choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Completed", "Completed"), ("Deferred", "Deferred")],
        default="Pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Road section intervention"
        verbose_name_plural = "Road section interventions"

    def __str__(self) -> str:  # pragma: no cover
        return f"Section intervention {self.id} ({self.section_id})"


class BenefitFactor(models.Model):
    road = models.ForeignKey(Road, on_delete=models.CASCADE, related_name="benefit_factors")
    fiscal_year = models.PositiveIntegerField(null=True, blank=True)
    bf1_transport_score = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    bf2_agriculture_score = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    bf3_social_score = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    total_benefit_score = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    calculated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Benefit factor"
        verbose_name_plural = "Benefit factors"
        unique_together = ("road", "fiscal_year")
        ordering = ["-fiscal_year", "road__road_identifier"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Benefit factors for road {self.road_id} ({self.fiscal_year})"


class RoadRankingResult(models.Model):
    road = models.ForeignKey(Road, on_delete=models.CASCADE, related_name="ranking_results")
    fiscal_year = models.PositiveIntegerField()
    road_class_or_surface_group = models.CharField(max_length=20)
    population_served = models.DecimalField(max_digits=15, decimal_places=2)
    benefit_factor = models.DecimalField(max_digits=12, decimal_places=4)
    cost_of_improvement = models.DecimalField(max_digits=15, decimal_places=2)
    road_index = models.DecimalField(max_digits=20, decimal_places=8)
    rank = models.PositiveIntegerField(help_text="Rank order (1 = highest priority)")

    class Meta:
        verbose_name = "Road ranking result"
        verbose_name_plural = "Road ranking results"
        unique_together = ("road", "fiscal_year", "road_class_or_surface_group")
        ordering = ["road_class_or_surface_group", "rank"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.road} - FY {self.fiscal_year} ({self.road_class_or_surface_group})"


class PrioritizationResult(models.Model):
    road = models.ForeignKey(Road, on_delete=models.CASCADE)
    section = models.ForeignKey(RoadSection, on_delete=models.CASCADE, null=True, blank=True)
    fiscal_year = models.PositiveIntegerField()
    population_served = models.IntegerField(null=True, blank=True)
    benefit_score = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    improvement_cost = models.DecimalField(max_digits=15, decimal_places=2)
    ranking_index = models.DecimalField(max_digits=15, decimal_places=6)
    priority_rank = models.PositiveIntegerField(help_text="Rank order (1 = highest priority)")
    recommended_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    approved_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    calculation_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Prioritization result"
        verbose_name_plural = "Prioritization results"
        ordering = ["fiscal_year", "priority_rank"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Priority {self.priority_rank} for road {self.road_id} ({self.fiscal_year})"


class AnnualWorkPlan(models.Model):
    fiscal_year = models.PositiveIntegerField()
    region = models.CharField(max_length=100)
    woreda = models.CharField(max_length=100)
    road = models.ForeignKey(Road, on_delete=models.CASCADE)
    priority_rank = models.PositiveIntegerField(help_text="Final priority rank in plan")
    total_budget = models.DecimalField(max_digits=15, decimal_places=2)
    rm_budget = models.DecimalField(max_digits=15, decimal_places=2, help_text="Routine Maintenance budget")
    pm_budget = models.DecimalField(max_digits=15, decimal_places=2, help_text="Periodic Maintenance budget")
    rehab_budget = models.DecimalField(max_digits=15, decimal_places=2, help_text="Rehabilitation budget")
    bottleneck_budget = models.DecimalField(max_digits=15, decimal_places=2, help_text="Bottleneck fixes budget")
    struct_budget = models.DecimalField(max_digits=15, decimal_places=2, help_text="Structure interventions budget")
    status = models.CharField(
        max_length=10,
        choices=[
            ("Draft", "Draft"),
            ("Submitted", "Submitted"),
            ("Approved", "Approved"),
            ("Executing", "Executing"),
            ("Completed", "Completed"),
        ],
        default="Draft",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        verbose_name = "Annual work plan"
        verbose_name_plural = "Annual work plans"
        unique_together = ("fiscal_year", "road")

    def __str__(self) -> str:  # pragma: no cover
        return f"Annual work plan {self.fiscal_year} - {self.road_id}"

