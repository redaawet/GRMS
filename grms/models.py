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
from django.db import models

from .gis_fields import PointField
from .utils import make_point, utm_to_wgs84

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------


class ConditionRating(models.Model):
    """Overall condition rating (e.g., Good/Fair/Poor/Bad)."""

    name = models.CharField(max_length=50, unique=True)
    rating_value = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Condition rating"
        verbose_name_plural = "Condition ratings"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.name


class ConditionFactor(models.Model):
    """Component condition factor for structure surveys."""

    factor = models.CharField(max_length=50, unique=True)
    factor_value = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Condition factor"
        verbose_name_plural = "Condition factors"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.factor


class QAStatus(models.Model):
    """Quality assurance status for survey records."""

    status = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "QA status"
        verbose_name_plural = "QA statuses"

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return self.status


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
        help_text="Administrative Woreda",
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
    population_served = models.IntegerField(null=True, blank=True, help_text="Population served")
    year_of_update = models.DateField(null=True, blank=True, help_text="Date of last MCI update")
    remarks = models.TextField(blank=True, help_text="Additional notes or remarks")

    class Meta:
        verbose_name = "Road"
        verbose_name_plural = "Roads"

    def __str__(self) -> str:  # pragma: no cover
        return f"Road {self.id}: {self.road_name_from}–{self.road_name_to}"

    def clean(self):  # pragma: no cover - simple validation
        if self.admin_woreda_id and self.admin_zone_id:
            if self.admin_woreda.zone_id != self.admin_zone_id:
                raise ValidationError(
                    {"admin_woreda": "Selected woreda does not belong to the selected zone."}
                )

    def _point_from_utm(self, easting: Optional[Decimal], northing: Optional[Decimal]):
        if easting is None or northing is None:
            return None
        lat, lon = utm_to_wgs84(float(easting), float(northing), zone=37)
        return make_point(lat, lon)

    def save(self, *args, **kwargs):
        # Update WGS84 coordinates from UTM inputs when provided. Zone and
        # woreda selections are left untouched.
        start_point = self._point_from_utm(self.start_easting, self.start_northing)
        if start_point:
            self.road_start_coordinates = start_point

        end_point = self._point_from_utm(self.end_easting, self.end_northing)
        if end_point:
            self.road_end_coordinates = end_point

        super().save(*args, **kwargs)


class RoadSection(models.Model):
    SURFACE_TYPES = [
        ("Earth", "Earth"),
        ("Gravel", "Gravel"),
        ("DBST", "DBST"),
        ("Asphalt", "Asphalt"),
        ("Sealed", "Sealed"),
    ]

    road = models.ForeignKey(Road, on_delete=models.CASCADE, related_name="sections")
    section_number = models.PositiveIntegerField(help_text="Section identifier within the road")
    sequence_on_road = models.PositiveIntegerField(
        default=1, help_text="Ordered position of this section along the parent road"
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

    class Meta:
        verbose_name = "Road section"
        verbose_name_plural = "Road sections"
        ordering = ("road", "sequence_on_road", "section_number")
        unique_together = (("road", "section_number"), ("road", "sequence_on_road"))

    def __str__(self) -> str:  # pragma: no cover
        return f"Section {self.section_number} of Road {self.road_id}"

    def clean(self):  # pragma: no cover - simple validation
        errors = {}

        if self.admin_zone_override_id and self.admin_woreda_override_id:
            if self.admin_woreda_override.zone_id != self.admin_zone_override_id:
                errors["admin_woreda_override"] = "Selected woreda does not belong to the selected zone."

        if self.start_chainage_km is not None:
            if self.start_chainage_km < 0:
                errors["start_chainage_km"] = "Start chainage cannot be negative."

        if self.start_chainage_km is not None and self.end_chainage_km is not None:
            if self.start_chainage_km >= self.end_chainage_km:
                errors["end_chainage_km"] = "End chainage must be greater than start chainage."

            if self.road_id:
                road_length = self.road.total_length_km
                if self.end_chainage_km > road_length:
                    errors["end_chainage_km"] = "Section end exceeds the parent road length."
                if self.start_chainage_km > road_length:
                    errors["start_chainage_km"] = "Section start exceeds the parent road length."
                if (self.end_chainage_km - self.start_chainage_km) > road_length:
                    errors["length_km"] = "Section length cannot be greater than the parent road length."

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

        if self.surface_type in {"Gravel", "DBST", "Asphalt", "Sealed"}:
            if self.surface_thickness_cm is None:
                errors["surface_thickness_cm"] = "Thickness is required for gravel or paved surfaces."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.start_chainage_km is not None and self.end_chainage_km is not None:
            self.length_km = (self.end_chainage_km - self.start_chainage_km).quantize(Decimal("0.001"))
        self.full_clean()
        super().save(*args, **kwargs)


class RoadSegment(models.Model):
    section = models.ForeignKey(RoadSection, on_delete=models.CASCADE, related_name="segments")
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
    ditch_left_present = models.BooleanField(default=False)
    ditch_right_present = models.BooleanField(default=False)
    shoulder_left_present = models.BooleanField(default=False)
    shoulder_right_present = models.BooleanField(default=False)
    carriageway_width_m = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comment = models.TextField(blank=True, help_text="Notes or comments for this segment")

    class Meta:
        verbose_name = "Road segment"
        verbose_name_plural = "Road segments"

    @property
    def length_km(self) -> float:
        """Return computed length based on chainage values."""

        start = float(self.station_from_km or 0)
        end = float(self.station_to_km or 0)
        return end - start

    def __str__(self) -> str:  # pragma: no cover
        return f"Segment {self.id} ({self.station_from_km}-{self.station_to_km} km)"


class StructureInventory(models.Model):
    road = models.ForeignKey(Road, on_delete=models.CASCADE, related_name="structures")
    section = models.ForeignKey(
        RoadSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="structures",
        help_text="Optional road section reference",
    )
    station_km = models.DecimalField(max_digits=8, decimal_places=3, help_text="Location along road (chainage km)")
    location_point = PointField(srid=4326, null=True, blank=True, help_text="GPS coordinates of the structure")
    structure_category = models.CharField(
        max_length=20,
        choices=[
            ("Bridge", "Bridge"),
            ("Culvert", "Culvert"),
            ("Ford", "Ford"),
            ("Retaining Wall", "Retaining Wall"),
            ("Gabion Wall", "Gabion Wall"),
            ("Other", "Other"),
        ],
        help_text="General category of structure",
    )
    structure_type = models.CharField(max_length=50, blank=True)
    condition_code = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Overall condition rating code (1=Good, 4=Poor)")
    head_walls_flag = models.BooleanField(default=False, help_text="Head walls present?")
    comments = models.TextField(blank=True)
    attachments = models.JSONField(null=True, blank=True, help_text="Photos or inspection docs")
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Structure inventory"
        verbose_name_plural = "Structure inventories"

    def __str__(self) -> str:  # pragma: no cover
        return f"Structure {self.id} ({self.structure_category} at {self.station_km} km)"


class BridgeDetail(models.Model):
    structure = models.OneToOneField(
        StructureInventory,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"structure_category": "Bridge"},
    )
    bridge_type = models.CharField(
        max_length=20,
        choices=[
            ("Concrete", "Concrete"),
            ("Stone", "Stone"),
            ("Bailey", "Bailey"),
            ("Steel", "Steel"),
            ("Timber", "Timber"),
        ],
        help_text="Type of bridge structure",
    )
    span_count = models.PositiveSmallIntegerField(null=True, blank=True)
    width_m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    length_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    has_head_walls = models.BooleanField(default=False, help_text="Head walls present")

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
        max_length=10,
        choices=[("Slab", "Slab"), ("Box", "Box"), ("Steel", "Steel"), ("Pipe", "Pipe")],
        help_text="Type of culvert",
    )
    width_span_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Span width (slab/box culverts)",
    )
    clear_height_m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Clear height (slab/box culverts)")
    num_pipes = models.PositiveSmallIntegerField(null=True, blank=True, help_text="# of pipes (pipe culvert)")
    pipe_diameter_m = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Pipe diameter (m)")
    has_head_walls = models.BooleanField(default=False)

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
    road_segment = models.ForeignKey(RoadSegment, on_delete=models.CASCADE, related_name="furniture")
    furniture_type = models.CharField(
        max_length=20,
        choices=[
            ("Guard Post", "Guard Post"),
            ("Guard Rail", "Guard Rail"),
            ("KM Post", "KM Post"),
            ("Road Sign", "Road Sign"),
        ],
        help_text="Furniture category",
    )
    chainage_from_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    chainage_to_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    left_present = models.BooleanField(default=False)
    right_present = models.BooleanField(default=False)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Furniture inventory"
        verbose_name_plural = "Furniture inventories"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.furniture_type} on segment {self.road_segment_id}"


# ---------------------------------------------------------------------------
# Survey models
# ---------------------------------------------------------------------------


class StructureConditionSurvey(models.Model):
    structure = models.ForeignKey(StructureInventory, on_delete=models.CASCADE, related_name="surveys")
    survey_year = models.PositiveIntegerField(help_text="Year of survey")
    condition_rating = models.ForeignKey(
        ConditionRating,
        on_delete=models.PROTECT,
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


class BridgeConditionSurvey(models.Model):
    structure_survey = models.OneToOneField(
        StructureConditionSurvey,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"structure__structure_category": "Bridge"},
    )
    deck_condition = models.ForeignKey(ConditionFactor, on_delete=models.SET_NULL, null=True, related_name="+")
    abutment_condition = models.ForeignKey(ConditionFactor, on_delete=models.SET_NULL, null=True, related_name="+")
    pier_condition = models.ForeignKey(ConditionFactor, on_delete=models.SET_NULL, null=True, related_name="+")
    wearing_surface = models.ForeignKey(ConditionFactor, on_delete=models.SET_NULL, null=True, related_name="+")
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
    inlet_condition = models.ForeignKey(ConditionFactor, on_delete=models.SET_NULL, null=True, related_name="+")
    outlet_condition = models.ForeignKey(ConditionFactor, on_delete=models.SET_NULL, null=True, related_name="+")
    barrel_condition = models.ForeignKey(ConditionFactor, on_delete=models.SET_NULL, null=True, related_name="+")
    headwall_condition = models.ForeignKey(ConditionFactor, on_delete=models.SET_NULL, null=True, related_name="+")
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Culvert condition survey"
        verbose_name_plural = "Culvert condition surveys"

    def __str__(self) -> str:  # pragma: no cover
        return f"Culvert survey details {self.structure_survey_id}"


class OtherStructureConditionSurvey(models.Model):
    structure_survey = models.OneToOneField(StructureConditionSurvey, on_delete=models.CASCADE, primary_key=True)
    wall_condition = models.ForeignKey(ConditionFactor, on_delete=models.SET_NULL, null=True, related_name="+")
    ford_condition = models.ForeignKey(ConditionFactor, on_delete=models.SET_NULL, null=True, related_name="+")
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Other structure condition survey"
        verbose_name_plural = "Other structure condition surveys"

    def __str__(self) -> str:  # pragma: no cover
        return f"Other structure survey details {self.structure_survey_id}"


class RoadConditionSurvey(models.Model):
    road_segment = models.ForeignKey(RoadSegment, on_delete=models.CASCADE, related_name="condition_surveys")
    drainage_condition_left = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Left drainage condition (0–5 scale)",
    )
    drainage_condition_right = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    shoulder_condition_left = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    shoulder_condition_right = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    surface_condition_factor = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Surface condition factor (e.g., 0–5 scale)",
    )
    is_there_bottleneck = models.BooleanField(default=False, help_text="Is there any bottleneck on this segment?")
    bottleneck_size_m = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comments = models.TextField(blank=True)
    inspected_by = models.CharField(max_length=150, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    calculated_mci = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Maintenance Condition Index for this segment",
    )
    intervention_recommended = models.TextField(blank=True, help_text="Suggested intervention based on condition")

    class Meta:
        verbose_name = "Road condition survey"
        verbose_name_plural = "Road condition surveys"

    def save(self, *args, **kwargs) -> None:
        factors: Iterable[Optional[Decimal]] = (
            self.surface_condition_factor,
            self.drainage_condition_left,
            self.drainage_condition_right,
            self.shoulder_condition_left,
            self.shoulder_condition_right,
        )
        values = [float(v) for v in factors if v is not None]
        if values:
            avg_cond = sum(values) / len(values)
            self.calculated_mci = round(avg_cond * 20.0, 1)
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"Road survey {self.id} for segment {self.road_segment_id}"


class FurnitureConditionSurvey(models.Model):
    furniture = models.ForeignKey(FurnitureInventory, on_delete=models.CASCADE, related_name="surveys")
    survey_year = models.PositiveIntegerField()
    condition_rating = models.ForeignKey(ConditionRating, on_delete=models.PROTECT)
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
    road_segment = models.ForeignKey(RoadSegment, on_delete=models.CASCADE, related_name="traffic_surveys")
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
    fiscal_year = models.PositiveIntegerField()
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
    calculated_mci = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
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
    traffic_vehicles_per_day = models.IntegerField(null=True, blank=True)
    trading_centers_count = models.IntegerField(null=True, blank=True)
    villages_connected_count = models.IntegerField(null=True, blank=True)
    farmland_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    health_centers_count = models.IntegerField(null=True, blank=True)
    educational_institutions_count = models.IntegerField(null=True, blank=True)
    total_benefit_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    last_calculated = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Benefit factor"
        verbose_name_plural = "Benefit factors"

    def __str__(self) -> str:  # pragma: no cover
        return f"Benefit factors for road {self.road_id}"


class PrioritizationResult(models.Model):
    road = models.ForeignKey(Road, on_delete=models.CASCADE)
    section = models.ForeignKey(RoadSection, on_delete=models.CASCADE, null=True, blank=True)
    fiscal_year = models.PositiveIntegerField()
    population_served = models.IntegerField(null=True, blank=True)
    benefit_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    improvement_cost = models.DecimalField(max_digits=15, decimal_places=2)
    ranking_index = models.DecimalField(max_digits=10, decimal_places=4)
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

