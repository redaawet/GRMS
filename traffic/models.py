from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils import timezone

from grms.gis_fields import PointField
from grms.models import Road
from .choices import (
    QA_STATUS_CHOICES,
    TRAFFIC_METHOD_CHOICES,
    VALUE_TYPE_CHOICES,
    VEHICLE_CLASS_CHOICES,
)

VEHICLE_FIELD_MAP = {
    "Car": "cars",
    "LightGoods": "light_goods",
    "MiniBus": "minibuses",
    "MediumGoods": "medium_goods",
    "HeavyGoods": "heavy_goods",
    "Bus": "buses",
    "Tractor": "tractors",
    "Motorcycle": "motorcycles",
    "Bicycle": "bicycles",
    "Pedestrian": "pedestrians",
}


class TrafficSurvey(models.Model):
    """
    Survey header metadata for a 7-day traffic count campaign on a road.
    One record per road-year-cycle with a station location.
    """

    road = models.ForeignKey(
        Road,
        on_delete=models.PROTECT,
        related_name="traffic_surveys",
    )

    station_location = PointField(srid=4326, help_text="GPS location of the counting station.")

    survey_year = models.IntegerField(help_text="Year of survey (e.g. 2025).")

    cycle_number = models.PositiveSmallIntegerField(
        help_text="Economic-season cycle (1–3).",
    )

    count_start_date = models.DateField()
    count_end_date = models.DateField()

    count_days_per_cycle = models.PositiveSmallIntegerField(
        default=7,
        help_text="Number of days counted in this cycle (usually 7).",
    )

    count_hours_per_day = models.PositiveSmallIntegerField(
        default=12,
        help_text="Hours counted per day (12 or 24).",
    )

    night_adjustment_factor = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        help_text="Night adjustment factor used for this survey (frozen).",
    )

    override_night_factor = models.BooleanField(
        default=False,
        help_text="Tick only if you manually override the computed night adjustment factor.",
    )

    method = models.CharField(
        max_length=20,
        choices=TRAFFIC_METHOD_CHOICES,
        default="MOC",
    )

    observer = models.CharField(
        max_length=150,
        blank=True,
        help_text="Team or observer name.",
    )

    weather_notes = models.CharField(
        max_length=100,
        blank=True,
    )

    qa_status = models.CharField(
        max_length=20,
        choices=QA_STATUS_CHOICES,
        default="Draft",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "traffic_survey"
        unique_together = ("road", "survey_year", "cycle_number")
        verbose_name = "Traffic survey"
        verbose_name_plural = "Traffic surveys"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.road} – {self.survey_year} – Cycle {self.cycle_number}"

    def approve(self):
        unresolved = self.qc_issues.filter(resolved=False).exists()
        if unresolved:
            raise ValueError("Resolve all QC issues before approval.")
        self.qa_status = "Approved"
        self.approved_at = timezone.now()
        self.save(update_fields=["qa_status", "approved_at"])

    def save(self, *args, **kwargs):
        if not self.override_night_factor and self.count_start_date:
            factor = NightAdjustmentLookup.get_factor(
                hours_counted=self.count_hours_per_day,
                date=self.count_start_date,
            )
            if factor is not None:
                self.night_adjustment_factor = factor
            elif not self.night_adjustment_factor:
                self.night_adjustment_factor = Decimal("1.0")

        super().save(*args, **kwargs)


class TrafficCountRecord(models.Model):
    """
    One record captures counts for all vehicle classes in a single date/time block.
    """

    count_id = models.BigAutoField(primary_key=True)

    traffic_survey = models.ForeignKey(
        TrafficSurvey,
        on_delete=models.CASCADE,
        related_name="count_records",
    )

    count_date = models.DateField()
    time_block_from = models.TimeField(null=True, blank=True)
    time_block_to = models.TimeField(null=True, blank=True)

    cars = models.IntegerField(default=0)
    light_goods = models.IntegerField(default=0)
    minibuses = models.IntegerField(default=0)
    medium_goods = models.IntegerField(default=0)
    heavy_goods = models.IntegerField(default=0)
    buses = models.IntegerField(default=0)
    tractors = models.IntegerField(default=0)
    motorcycles = models.IntegerField(default=0)
    bicycles = models.IntegerField(default=0)
    pedestrians = models.IntegerField(default=0)

    is_market_day = models.BooleanField(
        default=False,
        help_text="Market day flag.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "traffic_count_record"
        verbose_name = "Traffic count"
        verbose_name_plural = "Traffic counts"


class PcuLookup(models.Model):
    pcu_id = models.BigAutoField(primary_key=True)

    vehicle_class = models.CharField(
        max_length=20,
        choices=VEHICLE_CLASS_CHOICES,
    )
    pcu_factor = models.DecimalField(max_digits=6, decimal_places=3)
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "pcu_lookup"
        indexes = [
            models.Index(fields=["vehicle_class", "effective_date"]),
        ]
        verbose_name = "PCU lookup"
        verbose_name_plural = "PCU lookup entries"

    @classmethod
    def get_effective_factor(cls, vehicle_class: str, date, region: Optional[str] = None) -> Decimal:
        qs = cls.objects.filter(
            vehicle_class=vehicle_class,
            effective_date__lte=date,
        ).filter(
            models.Q(expiry_date__isnull=True) | models.Q(expiry_date__gte=date)
        )

        if region:
            regional = qs.filter(region=region).order_by("-effective_date").first()
            if regional:
                return regional.pcu_factor

        generic = qs.filter(region__isnull=True).order_by("-effective_date").first()
        return generic.pcu_factor if generic else Decimal("1.0")


class NightAdjustmentLookup(models.Model):
    nadj_id = models.BigAutoField(primary_key=True)

    hours_counted = models.SmallIntegerField(
        help_text="Hours counted per day (e.g., 12 or 24).",
    )
    adjustment_factor = models.DecimalField(max_digits=6, decimal_places=3)
    effective_date = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "night_adjustment_lookup"
        indexes = [
            models.Index(fields=["hours_counted", "effective_date"]),
        ]
        verbose_name = "Night adjustment lookup"
        verbose_name_plural = "Night adjustment lookup entries"

    @classmethod
    def get_factor(cls, hours_counted: int, date) -> Decimal:
        qs = cls.objects.filter(
            hours_counted=hours_counted,
            effective_date__lte=date,
        ).order_by("-effective_date")
        obj = qs.first()
        return obj.adjustment_factor if obj else Decimal("1.0")


class TrafficQc(models.Model):
    QC_SOURCE_CHOICES = (
        ("SYSTEM", "System"),
        ("USER", "User"),
    )

    qc_id = models.BigAutoField(primary_key=True)

    traffic_survey = models.ForeignKey(
        TrafficSurvey,
        on_delete=models.CASCADE,
        related_name="qc_issues",
    )
    road = models.ForeignKey(
        Road,
        on_delete=models.PROTECT,
        related_name="traffic_qc_issues",
    )

    issue_type = models.CharField(max_length=100)
    issue_detail = models.TextField()
    qc_source = models.CharField(max_length=10, choices=QC_SOURCE_CHOICES, default="USER")
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_traffic_qc",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "traffic_qc"
        verbose_name = "Traffic QC issue"
        verbose_name_plural = "Traffic QC issues"


class TrafficCycleSummary(models.Model):
    cycle_summary_id = models.BigAutoField(primary_key=True)

    traffic_survey = models.ForeignKey(
        TrafficSurvey,
        on_delete=models.CASCADE,
        related_name="cycle_summaries",
    )
    road = models.ForeignKey(
        Road,
        on_delete=models.PROTECT,
        related_name="traffic_cycle_summaries",
    )

    vehicle_class = models.CharField(
        max_length=20,
        choices=VEHICLE_CLASS_CHOICES,
    )
    cycle_number = models.PositiveSmallIntegerField()

    cycle_days_counted = models.IntegerField()
    cycle_sum_count = models.BigIntegerField()

    cycle_daily_avg = models.DecimalField(max_digits=10, decimal_places=3)
    cycle_daily_24hr = models.DecimalField(max_digits=12, decimal_places=3)
    cycle_pcu = models.DecimalField(max_digits=12, decimal_places=3)

    qc_flag = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "traffic_cycle_summary"
        unique_together = (
            "traffic_survey",
            "road",
            "vehicle_class",
            "cycle_number",
        )
        verbose_name = "Traffic cycle summary"
        verbose_name_plural = "Traffic cycle summaries"


class TrafficSurveySummary(models.Model):
    survey_summary_id = models.BigAutoField(primary_key=True)

    traffic_survey = models.ForeignKey(
        TrafficSurvey,
        on_delete=models.CASCADE,
        related_name="survey_summaries",
    )
    road = models.ForeignKey(
        Road,
        on_delete=models.PROTECT,
        related_name="traffic_survey_summaries",
    )

    fiscal_year = models.IntegerField()

    vehicle_class = models.CharField(
        max_length=20,
        choices=VEHICLE_CLASS_CHOICES,
    )

    avg_daily_count_all_cycles = models.DecimalField(max_digits=12, decimal_places=3)
    adt_final = models.DecimalField(max_digits=12, decimal_places=3)
    pcu_final = models.DecimalField(max_digits=12, decimal_places=3)

    adt_total = models.DecimalField(max_digits=12, decimal_places=3)
    pcu_total = models.DecimalField(max_digits=14, decimal_places=3)

    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)

    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "traffic_survey_summary"
        unique_together = ("traffic_survey", "road", "vehicle_class")
        verbose_name = "Traffic survey summary"
        verbose_name_plural = "Traffic survey summaries"


class TrafficForPrioritization(models.Model):
    prep_id = models.BigAutoField(primary_key=True)

    road = models.ForeignKey(
        Road,
        on_delete=models.PROTECT,
        related_name="traffic_prioritization_values",
    )

    fiscal_year = models.IntegerField()

    value_type = models.CharField(
        max_length=10,
        choices=VALUE_TYPE_CHOICES,
    )
    final_value = models.DecimalField(max_digits=14, decimal_places=3)

    source_survey = models.ForeignKey(
        TrafficSurvey,
        on_delete=models.PROTECT,
        related_name="traffic_prioritization_values",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Only one active record per road+fiscal_year+value_type.",
    )

    prepared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "traffic_for_prioritization"
        unique_together = ("road", "fiscal_year", "value_type", "is_active")
        verbose_name = "Traffic value for prioritization"
        verbose_name_plural = "Traffic values for prioritization"


def recompute_cycle_summaries_for_survey(survey: TrafficSurvey):
    """
    Derive TrafficCycleSummary rows from TrafficCountRecord for a given survey.
    """

    from django.db.models import Sum

    records_qs = TrafficCountRecord.objects.filter(traffic_survey=survey)
    if not records_qs.exists():
        return

    night_factor = survey.night_adjustment_factor or Decimal("1.0")
    cycle_days_counted = records_qs.values("count_date").distinct().count() or 1

    road = survey.road
    region_name = getattr(getattr(road, "admin_zone", None), "name", None) if road else None

    for vehicle_class, field_name in VEHICLE_FIELD_MAP.items():
        cycle_sum = records_qs.aggregate(total=Sum(field_name)).get("total") or 0
        cycle_daily_avg = Decimal(cycle_sum) / Decimal(cycle_days_counted)
        cycle_daily_24hr = cycle_daily_avg * night_factor

        pcu_factor = PcuLookup.get_effective_factor(
            vehicle_class=vehicle_class,
            date=survey.count_start_date,
            region=region_name,
        )

        cycle_pcu = cycle_daily_24hr * pcu_factor

        TrafficCycleSummary.objects.update_or_create(
            traffic_survey=survey,
            road=survey.road,
            vehicle_class=vehicle_class,
            cycle_number=survey.cycle_number,
            defaults=dict(
                cycle_days_counted=cycle_days_counted,
                cycle_sum_count=cycle_sum,
                cycle_daily_avg=cycle_daily_avg,
                cycle_daily_24hr=cycle_daily_24hr,
                cycle_pcu=cycle_pcu,
            ),
        )


def compute_confidence_score_for_survey(survey: TrafficSurvey) -> Decimal:
    """
    Simple placeholder: 100 - 5 points per unresolved QC issue (max 40).
    """

    base = Decimal("100.0")
    unresolved_count = TrafficQc.objects.filter(
        traffic_survey=survey,
        road=survey.road,
        resolved=False,
    ).count()
    penalty = min(unresolved_count * 5, 40)
    score = base - Decimal(penalty)
    return max(score, Decimal("0.0"))


def recompute_survey_summary_for_survey(survey: TrafficSurvey):
    """
    Build TrafficSurveySummary rows from TrafficCycleSummary.
    """

    from django.db.models import Avg

    cycle_qs = (
        TrafficCycleSummary.objects
        .filter(traffic_survey=survey, road=survey.road)
        .values("vehicle_class")
        .annotate(
            avg_daily_avg=Avg("cycle_daily_avg"),
            avg_daily_24hr=Avg("cycle_daily_24hr"),
            avg_cycle_pcu=Avg("cycle_pcu"),
        )
    )

    adt_total = Decimal("0")
    pcu_total = Decimal("0")

    for row in cycle_qs:
        vehicle_class = row["vehicle_class"]
        avg_daily_count_all_cycles = row["avg_daily_avg"] or Decimal("0")
        adt_class = row["avg_daily_24hr"] or Decimal("0")
        pcu_class = row["avg_cycle_pcu"] or Decimal("0")

        TrafficSurveySummary.objects.update_or_create(
            traffic_survey=survey,
            road=survey.road,
            vehicle_class=vehicle_class,
            defaults=dict(
                fiscal_year=survey.survey_year,
                avg_daily_count_all_cycles=avg_daily_count_all_cycles,
                adt_final=adt_class,
                pcu_final=pcu_class,
                adt_total=Decimal("0"),
                pcu_total=Decimal("0"),
                confidence_score=Decimal("0"),
            ),
        )

        adt_total += adt_class
        pcu_total += pcu_class

    confidence = compute_confidence_score_for_survey(survey)

    TrafficSurveySummary.objects.filter(
        traffic_survey=survey,
        road=survey.road,
    ).update(
        adt_total=adt_total,
        pcu_total=pcu_total,
        confidence_score=confidence,
    )


def promote_survey_to_prioritization(survey: TrafficSurvey, fiscal_year: int, use_pcu: bool):
    """
    Snapshot the latest TrafficSurveySummary for a road into TrafficForPrioritization.
    Only if survey is Approved.
    """

    if survey.qa_status != "Approved":
        return None

    summary_qs = TrafficSurveySummary.objects.filter(
        traffic_survey=survey,
        road=survey.road,
    )

    if not summary_qs.exists():
        return None

    totals = summary_qs.first()
    value_type = "PCU" if use_pcu else "ADT"
    numeric_value = totals.pcu_total if use_pcu else totals.adt_total

    TrafficForPrioritization.objects.filter(
        road=survey.road,
        fiscal_year=fiscal_year,
        value_type=value_type,
        is_active=True,
    ).update(is_active=False)

    obj = TrafficForPrioritization.objects.create(
        road=survey.road,
        fiscal_year=fiscal_year,
        value_type=value_type,
        final_value=numeric_value,
        source_survey=survey,
        is_active=True,
    )
    return obj


def run_auto_qc_for_survey(survey: TrafficSurvey):
    """Minimal auto-QC checks per requirements."""

    def _add_issue(issue_type: str, detail: str):
        TrafficQc.objects.get_or_create(
            traffic_survey=survey,
            road=survey.road,
            issue_type=issue_type,
            issue_detail=detail,
            qc_source="SYSTEM",
            resolved=False,
        )

    records = TrafficCountRecord.objects.filter(traffic_survey=survey)
    if not records.exists():
        _add_issue("Missing counts", "No traffic counts recorded for this survey.")
        return

    distinct_days = records.values("count_date").distinct().count()
    if distinct_days < survey.count_days_per_cycle:
        _add_issue("Missing days", "Number of count days is below expected cycle length.")

    if survey.count_hours_per_day not in (12, 24):
        _add_issue("Hour mismatch", "Count hours per day is unexpected for night factor lookup.")
