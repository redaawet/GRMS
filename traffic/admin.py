from django.contrib import admin
from django.urls import reverse

from grms.admin import grms_admin_site, _road_map_context_url
from grms.admin_base import GRMSBaseAdmin
from grms.admin_utils import valid_autocomplete_fields
from grms.models import Road
from grms.services import map_services
from grms.utils import point_to_lat_lng, wgs84_to_utm
from .forms import PcuBulkAddForm, TrafficSurveyAdminForm
from .models import (
    NightAdjustmentLookup,
    PcuLookup,
    TrafficCountRecord,
    TrafficCycleSummary,
    TrafficSurveyOverall,
    TrafficQC,
    TrafficSurvey,
    TrafficSurveySummary,
    VEHICLE_FIELD_MAP,
)


@admin.register(TrafficSurvey, site=grms_admin_site)
class TrafficSurveyAdmin(GRMSBaseAdmin):
    _AUTO = ("road",)
    autocomplete_fields = valid_autocomplete_fields(TrafficSurvey, _AUTO)
    change_form_template = "admin/traffic/trafficsurvey/change_form.html"
    form = TrafficSurveyAdminForm
    list_display = ("road", "survey_year", "cycle_number", "method", "qa_status")
    list_filter = ("survey_year", "cycle_number", "method", "qa_status")
    search_fields = ("road__road_identifier", "road__road_name_from", "road__road_name_to", "observer")

    fieldsets = (
        (
            "Survey details",
            {
                "fields": (
                    "road",
                    ("survey_year", "cycle_number"),
                    ("count_start_date", "count_end_date"),
                    ("count_days_per_cycle", "count_hours_per_day"),
                )
            },
        ),
        (
            "Station location",
            {
                "fields": (("station_easting", "station_northing"), "station_location"),
                "description": "Enter UTM Zone 37N coordinates or click the map to populate them.",
            },
        ),
        (
            "Method & QA",
            {
                "fields": (
                    "method",
                    "observer",
                    "weather_notes",
                    "override_night_factor",
                    "night_adjustment_factor",
                    "qa_status",
                )
            },
        ),
    )


    def get_readonly_fields(self, request, obj=None):  # pragma: no cover - admin hook
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and not obj.override_night_factor:
            readonly.append("night_adjustment_factor")
        return readonly

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        instance = self.get_object(request, object_id)
        extra_context["station_map_config"] = self._build_station_map_config(request, instance)
        return super().changeform_view(request, object_id, form_url, extra_context)

    def _build_station_map_config(self, request, survey):
        road = getattr(survey, "road", None)
        if not road:
            road_id = request.GET.get("road") or request.GET.get("road__id__exact")
            if road_id and road_id.isdigit():
                road = Road.objects.filter(pk=int(road_id)).first()

        map_context_url = _road_map_context_url(road.id) if road else reverse("road_map_context_default")

        station_point = None
        if survey and survey.station_location:
            station_point = point_to_lat_lng(survey.station_location)
            if station_point:
                try:
                    easting, northing = wgs84_to_utm(station_point["lat"], station_point["lng"], zone=37)
                except ImportError:
                    easting = northing = None
                station_point["easting"] = easting
                station_point["northing"] = northing

        return {
            "api": {"map_context": map_context_url},
            "station": station_point,
            "map_region": map_services.get_default_map_region(),
        }


@admin.register(TrafficCountRecord, site=grms_admin_site)
class TrafficCountRecordAdmin(GRMSBaseAdmin):
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


class _ReadOnlyAdmin(GRMSBaseAdmin):
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
    """
    Simplified admin so all fields are displayed automatically.
    """
    list_display = (
        "road",
        "traffic_survey",
        "vehicle_class",
        "cycle_number",
        "cycle_daily_24hr",
        "cycle_pcu",
    )
    list_filter = ("vehicle_class", "cycle_number")
    search_fields = ("road__road_identifier", "road__road_name_from", "road__road_name_to")


@admin.register(TrafficSurveySummary, site=grms_admin_site)
class TrafficSurveySummaryAdmin(_ReadOnlyAdmin):
    """
    Simplified admin so all fields are displayed automatically.
    """
    list_display = (
        "road",
        "vehicle_class",
        "fiscal_year",
        "adt_final",
        "pcu_final",
        "confidence_score",
    )
    list_filter = ("vehicle_class", "fiscal_year")
    search_fields = ("road__road_identifier", "road__road_name_from", "road__road_name_to")


@admin.register(TrafficSurveyOverall, site=grms_admin_site)
class TrafficSurveyOverallAdmin(_ReadOnlyAdmin):
    """
    Temporary simplified admin class so that all fields are displayed automatically.
    This fixes the 'no rows displayed' issue caused by list_display mismatches.
    """
    list_display = ("road", "fiscal_year", "adt_total", "pcu_total", "confidence_score")
    list_filter = ("fiscal_year",)
    search_fields = ("road__road_identifier", "road__road_name_from", "road__road_name_to")

@admin.register(TrafficQC, site=grms_admin_site)
class TrafficQcAdmin(GRMSBaseAdmin):
    list_display = (
        "traffic_survey",
        "road",
        "issue_type",
        "resolved",
        "created_at",
    )
    list_filter = ("resolved",)
    search_fields = ("issue_type", "issue_detail")


@admin.register(PcuLookup, site=grms_admin_site)
class PcuLookupAdmin(GRMSBaseAdmin):
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
class NightAdjustmentLookupAdmin(GRMSBaseAdmin):
    list_display = ("hours_counted", "adjustment_factor", "effective_date")
    list_filter = ("hours_counted",)
