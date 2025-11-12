from django.contrib.gis.db import models as gis_models
from django.db import models

SURFACE_CHOICES = [
    ('Earth','Earth'),
    ('Gravel','Gravel'),
    ('Asphalt','Asphalt'),
]

TERRAIN_CHOICES = [
    ('Flat','Flat'),
    ('Rolling','Rolling'),
    ('Mountainous','Mountainous'),
]

class Road(models.Model):
    road_id = models.BigAutoField(primary_key=True)
    road_name_from = models.CharField(max_length=150)
    road_name_to = models.CharField(max_length=150)
    road_code = models.CharField(max_length=50)
    design_standard = models.CharField(max_length=50, null=True, blank=True)
    admin_zone = models.CharField(max_length=100, null=True, blank=True)
    admin_woreda = models.CharField(max_length=100, null=True, blank=True)
    total_length_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    start_coordinates = gis_models.PointField(srid=4326, null=True, blank=True)
    end_coordinates = gis_models.PointField(srid=4326, null=True, blank=True)
    surface_type_main = models.CharField(max_length=20, choices=SURFACE_CHOICES, default='Gravel')
    managing_authority = models.CharField(max_length=100, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.road_code}: {self.road_name_from} - {self.road_name_to}"


class RoadSection(models.Model):
    section_id = models.BigAutoField(primary_key=True)
    road = models.ForeignKey(Road, on_delete=models.CASCADE, related_name='sections')
    section_number = models.IntegerField()
    start_coordinates = gis_models.PointField(srid=4326, null=True, blank=True)
    end_coordinates = gis_models.PointField(srid=4326, null=True, blank=True)
    start_chainage_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    end_chainage_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    length_km = models.DecimalField(max_digits=8, decimal_places=3, editable=False, null=True)
    surface_type = models.CharField(max_length=20, choices=SURFACE_CHOICES, default='Gravel')
    inspector_name = models.CharField(max_length=150, null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    geometry = gis_models.LineStringField(srid=4326, null=True, blank=True)
    attachments = models.JSONField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.start_chainage_km is not None and self.end_chainage_km is not None:
            try:
                self.length_km = self.end_chainage_km - self.start_chainage_km
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Section {self.section_number} ({self.road})"


class RoadSegment(models.Model):
    road_segment_id = models.BigAutoField(primary_key=True)
    section = models.ForeignKey(RoadSection, on_delete=models.CASCADE, related_name='segments')
    station_from_km = models.DecimalField(max_digits=8, decimal_places=3)
    station_to_km = models.DecimalField(max_digits=8, decimal_places=3)
    length_km = models.DecimalField(max_digits=8, decimal_places=3, editable=False, null=True)
    cross_section_type = models.CharField(max_length=100, null=True, blank=True)
    terrain = models.CharField(max_length=20, choices=TERRAIN_CHOICES, null=True, blank=True)
    carriageway_width_m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    shoulder_width_left_m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    shoulder_width_right_m = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    ditch_left_present = models.BooleanField(default=False)
    ditch_right_present = models.BooleanField(default=False)
    comment = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.station_from_km is not None and self.station_to_km is not None:
            try:
                self.length_km = self.station_to_km - self.station_from_km
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Segment {self.road_segment_id} ({self.station_from_km}-{self.station_to_km} km)"


class StructureInventory(models.Model):
    structure_id = models.BigAutoField(primary_key=True)
    road = models.ForeignKey(Road, on_delete=models.CASCADE, related_name='structures')
    section = models.ForeignKey(RoadSection, on_delete=models.SET_NULL, null=True, blank=True, related_name='structures')
    station_km = models.DecimalField(max_digits=8, decimal_places=3)
    location_point = gis_models.PointField(srid=4326, null=True, blank=True)
    category = models.CharField(max_length=50)  # Bridge/Culvert/Other
    structure_type = models.CharField(max_length=100, null=True, blank=True)
    bridge_span_count = models.SmallIntegerField(null=True, blank=True)
    bridge_length_m = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    culvert_diameter_mm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    condition_code = models.SmallIntegerField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    attachments = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Structure {self.structure_id} ({self.category}) on {self.road}"


class FurnitureInventory(models.Model):
    furniture_id = models.BigAutoField(primary_key=True)
    road_segment = models.ForeignKey(RoadSegment, on_delete=models.CASCADE, related_name='furnitures')
    furniture_type = models.CharField(max_length=50)
    chainage_km = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    left_present = models.BooleanField(default=False)
    right_present = models.BooleanField(default=False)
    comments = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Furniture {self.furniture_type} @ segment {self.road_segment_id}"


class QAStatus(models.Model):
    qa_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.status_name


class AnnualWorkPlan(models.Model):
    awp_id = models.BigAutoField(primary_key=True)
    fiscal_year = models.IntegerField()
    created_by = models.CharField(max_length=150, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"AWP {self.fiscal_year}"


class DistressType(models.Model):
    distress_id = models.AutoField(primary_key=True)
    distress_code = models.CharField(max_length=50, unique=True)
    distress_name = models.CharField(max_length=150)
    category = models.CharField(max_length=50)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.distress_code


class ActivityLookup(models.Model):
    activity_code = models.CharField(max_length=10, primary_key=True)
    activity_name = models.CharField(max_length=150)
    default_unit = models.CharField(max_length=20)
    is_resource_based = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.activity_code} - {self.activity_name}"


class DistressCondition(models.Model):
    condition_id = models.AutoField(primary_key=True)
    distress = models.ForeignKey(DistressType, on_delete=models.CASCADE, related_name='conditions')
    severity_code = models.SmallIntegerField(null=True, blank=True)
    extent_code = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('distress','severity_code','extent_code')

    def __str__(self):
        return f"{self.distress.distress_code} S{self.severity_code} E{self.extent_code}"


class DistressActivity(models.Model):
    id = models.AutoField(primary_key=True)
    condition = models.ForeignKey(DistressCondition, on_delete=models.CASCADE, related_name='activities')
    activity = models.ForeignKey(ActivityLookup, on_delete=models.CASCADE)
    quantity_value = models.DecimalField(max_digits=12, decimal_places=3)
    scale_basis = models.CharField(max_length=50)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.condition} -> {self.activity.activity_code}"


class RoadSegmentConditionSurvey(models.Model):
    survey_id = models.BigAutoField(primary_key=True)
    awp = models.ForeignKey(AnnualWorkPlan, on_delete=models.SET_NULL, null=True, blank=True)
    road_segment = models.ForeignKey(RoadSegment, on_delete=models.CASCADE, related_name='conditions')
    distress = models.ForeignKey(DistressType, on_delete=models.SET_NULL, null=True, blank=True)
    severity_code = models.SmallIntegerField(null=True, blank=True)
    extent_code = models.SmallIntegerField(null=True, blank=True)
    extent_percent = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    distress_length_m = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    distress_area_m2 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    distress_volume_m3 = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    observed_gravel_thickness_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    activity = models.ForeignKey(ActivityLookup, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_unit = models.CharField(max_length=20, null=True, blank=True)
    quantity_estimated = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    computed_by_lookup = models.BooleanField(default=True)
    severity_notes = models.TextField(null=True, blank=True)
    inspected_by = models.CharField(max_length=150, null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    qa_status = models.ForeignKey(QAStatus, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        segment_display = self.road_segment or "unknown segment"
        return f"Survey {self.survey_id} for segment {segment_display}"
