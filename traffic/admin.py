from django.contrib import admin

from grms.admin import grms_admin_site
from .models import (
    NightAdjustmentLookup,
    PcuLookup,
    TrafficCountRecord,
    TrafficCycleSummary,
    TrafficForPrioritization,
    TrafficQc,
    TrafficSurvey,
    TrafficSurveySummary,
)


class TrafficCountRecordInline(admin.TabularInline):
    model = TrafficCountRecord
    extra = 0
    readonly_fields = ("road_segment",)

    def has_add_permission(self, request, obj=None):  # pragma: no cover - admin hook
        return True


@admin.register(TrafficSurvey, site=grms_admin_site)
class TrafficSurveyAdmin(admin.ModelAdmin):
    inlines = [TrafficCountRecordInline]
    list_display = (
        "road_segment",
        "survey_year",
        "cycle_number",
        "method",
        "qa_status",
    )
    list_filter = ("survey_year", "cycle_number", "method", "qa_status")
    search_fields = ("observer", "road_segment__id")

    def get_readonly_fields(self, request, obj=None):  # pragma: no cover - admin hook
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and not obj.override_night_factor:
            readonly.append("night_adjustment_factor")
        return readonly


@admin.register(TrafficCountRecord, site=grms_admin_site)
class TrafficCountRecordAdmin(admin.ModelAdmin):
    list_display = (
        "traffic_survey",
        "road_segment",
        "vehicle_class",
        "count_value",
        "count_date",
        "time_block_from",
        "time_block_to",
        "is_market_day",
    )
    readonly_fields = ("road_segment",)
    list_filter = ("vehicle_class", "count_date", "is_market_day")
    search_fields = ("traffic_survey__id", "road_segment__id")


class _ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request, obj=None):  # pragma: no cover - admin hook
        return False

    def has_delete_permission(self, request, obj=None):  # pragma: no cover - admin hook
        return False

    def get_readonly_fields(self, request, obj=None):  # pragma: no cover - admin hook
        if self.readonly_fields:
            return self.readonly_fields
        if obj:
            return [field.name for field in obj._meta.fields]
        return []


@admin.register(TrafficCycleSummary, site=grms_admin_site)
class TrafficCycleSummaryAdmin(_ReadOnlyAdmin):
    list_display = (
        "traffic_survey",
        "vehicle_class",
        "cycle_number",
        "cycle_daily_24hr",
        "cycle_pcu",
    )


@admin.register(TrafficSurveySummary, site=grms_admin_site)
class TrafficSurveySummaryAdmin(_ReadOnlyAdmin):
    list_display = (
        "traffic_survey",
        "vehicle_class",
        "adt_class",
        "pcu_class",
        "confidence_score",
    )


@admin.register(TrafficForPrioritization, site=grms_admin_site)
class TrafficForPrioritizationAdmin(_ReadOnlyAdmin):
    readonly_fields = (
        "road",
        "road_segment",
        "fiscal_year",
        "value_type",
        "value",
        "source_survey",
        "prepared_at",
    )
    list_display = ("road", "road_segment", "fiscal_year", "value_type", "value", "is_active")


@admin.register(TrafficQc, site=grms_admin_site)
class TrafficQcAdmin(admin.ModelAdmin):
    list_display = (
        "traffic_survey",
        "road_segment",
        "issue_type",
        "resolved",
        "created_at",
    )
    list_filter = ("resolved",)
    search_fields = ("issue_type", "issue_detail")


@admin.register(PcuLookup, site=grms_admin_site)
class PcuLookupAdmin(admin.ModelAdmin):
    list_display = ("vehicle_class", "pcu_factor", "effective_date", "region")
    list_filter = ("vehicle_class", "region")
    search_fields = ("vehicle_class", "region")


@admin.register(NightAdjustmentLookup, site=grms_admin_site)
class NightAdjustmentLookupAdmin(admin.ModelAdmin):
    list_display = ("hours_counted", "adjustment_factor", "effective_date")
    list_filter = ("hours_counted",)
