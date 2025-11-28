from django.contrib import admin

from grms.admin import grms_admin_site
from .forms import PcuBulkAddForm
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
from .models import VEHICLE_FIELD_MAP


@admin.register(TrafficSurvey, site=grms_admin_site)
class TrafficSurveyAdmin(admin.ModelAdmin):
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
    fieldsets = (
        (
            "Time block",
            {
                "fields": (
                    "traffic_survey",
                    "count_date",
                    "time_block_from",
                    "time_block_to",
                    "is_market_day",
                )
            },
        ),
        (
            "Vehicle counts",
            {
                "fields": (
                    ("cars", "light_goods", "minibuses"),
                    ("medium_goods", "heavy_goods", "buses"),
                    ("tractors", "motorcycles", "bicycles", "pedestrians"),
                )
            },
        ),
    )
    list_display = (
        "traffic_survey",
        "count_date",
        "time_block_from",
        "time_block_to",
        "is_market_day",
    )
    list_filter = ("count_date", "is_market_day")
    search_fields = ("traffic_survey__id",)

    class Media:
        css = {"all": ["traffic/admin.css"]}


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
    add_form = PcuBulkAddForm
    list_display = ("vehicle_class", "pcu_factor", "effective_date", "region")
    list_filter = ("vehicle_class", "region")
    search_fields = ("vehicle_class", "region")

    def get_form(self, request, obj=None, **kwargs):  # pragma: no cover - admin hook
        if obj is None:
            defaults = {"form": self.add_form}
            defaults.update(kwargs)
            return super().get_form(request, obj, **defaults)
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):  # pragma: no cover - admin hook
        if change:
            return super().save_model(request, obj, form, change)

        created_entries = []
        base_fields = {
            "effective_date": form.cleaned_data.get("effective_date"),
            "expiry_date": form.cleaned_data.get("expiry_date"),
            "region": form.cleaned_data.get("region"),
            "notes": form.cleaned_data.get("notes", ""),
        }

        for vehicle_class, field_name in VEHICLE_FIELD_MAP.items():
            factor = form.cleaned_data.get(field_name)
            if factor is not None:
                created_entries.append(
                    PcuLookup.objects.create(
                        vehicle_class=vehicle_class,
                        pcu_factor=factor,
                        **base_fields,
                    )
                )

        if created_entries:
            first = created_entries[0]
            obj.pk = first.pk
            obj.vehicle_class = first.vehicle_class
            obj.pcu_factor = first.pcu_factor

    def response_add(self, request, obj, post_url_continue=None):  # pragma: no cover - admin hook
        self.message_user(
            request,
            "Created PCU lookup entries for provided vehicle classes.",
        )
        return super().response_add(request, obj, post_url_continue)


@admin.register(NightAdjustmentLookup, site=grms_admin_site)
class NightAdjustmentLookupAdmin(admin.ModelAdmin):
    list_display = ("hours_counted", "adjustment_factor", "effective_date")
    list_filter = ("hours_counted",)
