from __future__ import annotations

from typing import Dict, List, Sequence

from django import forms
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.shortcuts import redirect

from . import models
from .services import map_services
from .utils import make_point, point_to_lat_lng


class GRMSAdminSite(AdminSite):
    site_header = "GRMS Administration"
    site_title = "GRMS Admin"
    index_title = "Gravel Road Management System"
    index_template = "admin/grms_index.html"

    SECTION_DEFINITIONS: Sequence[Dict[str, object]] = (
        {
            "title": "Inventories",
            "models": (
                "Road",
                "Road section",
                "RoadSegment",
                "Road segment",
                "RoadSection",
                "StructureInventory",
                "Structure inventory",
                "FurnitureInventory",
                "Furniture inventory",
                "BridgeDetail",
                "Bridge detail",
                "CulvertDetail",
                "Culvert detail",
                "FordDetail",
                "Ford detail",
                "RetainingWallDetail",
                "Retaining wall detail",
                "GabionWallDetail",
                "Gabion wall detail",
            ),
        },
        {
            "title": "Surveys – Condition",
            "models": (
                "RoadConditionSurvey",
                "Road condition survey",
                "StructureConditionSurvey",
                "Structure condition survey",
                "BridgeConditionSurvey",
                "CulvertConditionSurvey",
                "OtherStructureConditionSurvey",
                "FurnitureConditionSurvey",
            ),
        },
        {
            "title": "Surveys – Severity & extent",
            "models": (
                "RoadConditionDetailedSurvey",
                "StructureConditionDetailedSurvey",
                "FurnitureConditionDetailedSurvey",
            ),
        },
        {
            "title": "Surveys – Traffic",
            "models": (
                "TrafficSurvey",
                "TrafficCountRecord",
                "TrafficCycleSummary",
                "TrafficSurveySummary",
                "TrafficQC",
                "TrafficForPrioritization",
                "PCULookup",
                "NightAdjustmentLookup",
            ),
        },
        {
            "title": "Maintenance & planning",
            "models": (
                "AnnualWorkPlan",
                "StructureIntervention",
                "RoadSectionIntervention",
                "BenefitFactor",
                "PrioritizationResult",
            ),
        },
        {
            "title": "Reference data",
            "models": (
                "QAStatus",
                "ActivityLookup",
                "InterventionLookup",
                "UnitCost",
                "DistressType",
                "DistressCondition",
                "DistressActivity",
                "ConditionRating",
                "ConditionFactor",
                "AdminZone",
                "AdminWoreda",
            ),
        },
    )

    @staticmethod
    def _normalise(name: str) -> str:
        return name.replace("_", " ").strip().lower()

    def _build_model_lookup(
        self, app_list: List[Dict[str, object]]
    ) -> Dict[str, Dict[str, object]]:
        lookup: Dict[str, Dict[str, object]] = {}
        for app in app_list:
            for model in app["models"]:
                for key in (model["object_name"], model["name"]):
                    lookup[self._normalise(key)] = model
        return lookup

    def _all_models(self, app_list: List[Dict[str, object]]):
        for app in app_list:
            for model in app["models"]:
                yield model

    def _build_sections(self, request) -> List[Dict[str, object]]:
        app_list = self.get_app_list(request)
        lookup = self._build_model_lookup(app_list)
        assigned: set[str] = set()
        sections: List[Dict[str, object]] = []
        for definition in self.SECTION_DEFINITIONS:
            models: List[Dict[str, object]] = []
            for target in definition.get("models", ()):  # type: ignore[arg-type]
                model = lookup.get(self._normalise(target))
                if model and model["object_name"] not in assigned:
                    models.append(model)
                    assigned.add(model["object_name"])
            if models:
                sections.append({"title": definition["title"], "models": models})
        leftovers = [
            model
            for model in sorted(self._all_models(app_list), key=lambda item: item["name"])
            if model["object_name"] not in assigned
        ]
        if leftovers:
            sections.append({"title": "Other models", "models": leftovers})
        return sections

    def index(self, request, extra_context=None):  # pragma: no cover - thin wrapper
        extra_context = extra_context or {}
        extra_context["sections"] = self._build_sections(request)
        return super().index(request, extra_context=extra_context)

    def app_index(self, request, app_label, extra_context=None):
        """Keep navigation consistent by redirecting per-app views to the dashboard."""
        return redirect("admin:index")


# Instantiate a single GRMSAdminSite so every generated link and template helper
# (e.g., {% url 'admin:index' %}) routes through the grouped dashboard instead
# of Django's stock admin. Replace Django's default site object so add/change
# pages also inherit the grouped layout.
grms_admin_site = GRMSAdminSite(name="admin")
admin.site = grms_admin_site
admin.sites.site = grms_admin_site


class RoadAdminForm(forms.ModelForm):
    start_lat = forms.FloatField(label="Start latitude", required=False)
    start_lng = forms.FloatField(label="Start longitude", required=False)
    end_lat = forms.FloatField(label="End latitude", required=False)
    end_lng = forms.FloatField(label="End longitude", required=False)

    class Meta:
        model = models.Road
        exclude = ("road_start_coordinates", "road_end_coordinates")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        start = point_to_lat_lng(getattr(self.instance, "road_start_coordinates", None))
        end = point_to_lat_lng(getattr(self.instance, "road_end_coordinates", None))
        if start:
            self.fields["start_lat"].initial = start["lat"]
            self.fields["start_lng"].initial = start["lng"]
        if end:
            self.fields["end_lat"].initial = end["lat"]
            self.fields["end_lng"].initial = end["lng"]

    def _clean_point(self, prefix: str):
        lat = self.cleaned_data.get(f"{prefix}_lat")
        lng = self.cleaned_data.get(f"{prefix}_lng")
        if lat is None and lng is None:
            return None
        if lat is None or lng is None:
            raise forms.ValidationError(
                {f"{prefix}_lat" if lat is None else f"{prefix}_lng": "Both latitude and longitude are required."}
            )
        return make_point(lat, lng)

    def clean(self):
        cleaned = super().clean()
        start = self._clean_point("start")
        end = self._clean_point("end")
        cleaned["road_start_coordinates"] = start
        cleaned["road_end_coordinates"] = end
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.road_start_coordinates = self.cleaned_data.get("road_start_coordinates")
        instance.road_end_coordinates = self.cleaned_data.get("road_end_coordinates")
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class RoadAdmin(admin.ModelAdmin):
    form = RoadAdminForm
    list_display = (
        "id",
        "road_name_from",
        "road_name_to",
        "admin_zone",
        "admin_woreda",
        "surface_type",
        "total_length_km",
    )
    list_filter = ("admin_zone", "admin_woreda", "surface_type", "managing_authority", "design_standard")
    search_fields = ("road_name_from", "road_name_to", "admin_woreda__name", "admin_zone__name")
    change_form_template = "admin/grms/road/change_form.html"
    fieldsets = (
        (
            "Administrative context",
            {
                "fields": (
                    ("road_name_from", "road_name_to"),
                    ("admin_zone", "admin_woreda"),
                    "managing_authority",
                    "design_standard",
                    "population_served",
                    "year_of_update",
                )
            },
        ),
        (
            "Physical characteristics",
            {
                "fields": (
                    "surface_type",
                    "total_length_km",
                    "remarks",
                )
            },
        ),
        (
            "Alignment coordinates",
            {
                "description": "Capture the start and end of the road in decimal degrees (WGS84).",
                "fields": (("start_lat", "start_lng"), ("end_lat", "end_lng")),
            },
        ),
    )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        road_id = int(object_id) if object_id and object_id.isdigit() else None
        extra_context["road_admin_config"] = {
            "road_id": road_id,
            "api": {
                "route": self._reverse_or_empty("road_route", road_id),
                "map_context": self._reverse_or_empty("road_map_context", road_id),
            },
        }
        extra_context["travel_modes"] = sorted(map_services.TRAVEL_MODES)
        return super().changeform_view(request, object_id, form_url, extra_context)

    @staticmethod
    def _reverse_or_empty(name: str, object_id):
        from django.urls import reverse

        if not object_id:
            return ""
        return reverse(name, args=[object_id])


grms_admin_site.register(models.Road, RoadAdmin)


@admin.register(models.AdminZone, site=grms_admin_site)
class AdminZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "region")
    search_fields = ("name", "region")
    fieldsets = (("Administrative zone", {"fields": ("name", "region")}),)


@admin.register(models.AdminWoreda, site=grms_admin_site)
class AdminWoredaAdmin(admin.ModelAdmin):
    list_display = ("name", "zone")
    list_filter = ("zone",)
    search_fields = ("name", "zone__name")
    fieldsets = (("Woreda", {"fields": ("name", "zone")}),)


@admin.register(models.RoadSection, site=grms_admin_site)
class RoadSectionAdmin(admin.ModelAdmin):
    list_display = ("road", "section_number", "length_km", "surface_type")
    list_filter = ("surface_type", "road__admin_zone")
    search_fields = ("road__road_name_from", "road__road_name_to")
    fieldsets = (
        ("Parent road", {"fields": ("road", "section_number")}),
        (
            "Chainage and length",
            {
                "fields": (
                    ("start_chainage_km", "end_chainage_km"),
                    "length_km",
                    "surface_type",
                    "gravel_thickness_cm",
                )
            },
        ),
        (
            "Geometry",
            {
                "fields": (
                    ("start_coordinates", "end_coordinates"),
                    "geometry",
                )
            },
        ),
        ("Inspection", {"fields": (("inspector_name", "inspection_date"), "attachments")}),
    )


@admin.register(models.RoadSegment, site=grms_admin_site)
class RoadSegmentAdmin(admin.ModelAdmin):
    list_display = ("section", "station_from_km", "station_to_km", "cross_section")
    search_fields = ("section__road__road_name_from", "section__road__road_name_to")
    fieldsets = (
        ("Identification", {"fields": ("section",)}),
        (
            "Location & geometry",
            {"fields": (("station_from_km", "station_to_km"), "carriageway_width_m")},
        ),
        (
            "Classification",
            {
                "fields": (
                    "cross_section",
                    "terrain_transverse",
                    "terrain_longitudinal",
                )
            },
        ),
        (
            "Roadway elements",
            {
                "fields": (
                    ("ditch_left_present", "ditch_right_present"),
                    ("shoulder_left_present", "shoulder_right_present"),
                )
            },
        ),
        ("Notes", {"fields": ("comment",)}),
    )


@admin.register(models.StructureInventory, site=grms_admin_site)
class StructureInventoryAdmin(admin.ModelAdmin):
    list_display = ("road", "structure_category", "station_km")
    list_filter = ("structure_category",)
    search_fields = ("road__road_name_from", "road__road_name_to")
    readonly_fields = ("created_date", "modified_date")
    fieldsets = (
        ("Location", {"fields": ("road", "section", "station_km", "location_point")}),
        (
            "Structure details",
            {
                "fields": (
                    "structure_category",
                    "structure_type",
                    "condition_code",
                    "head_walls_flag",
                )
            },
        ),
        ("Documentation", {"fields": ("comments", "attachments")}),
        ("Timestamps", {"fields": ("created_date", "modified_date")}),
    )


@admin.register(models.FurnitureInventory, site=grms_admin_site)
class FurnitureInventoryAdmin(admin.ModelAdmin):
    list_display = ("furniture_type", "road_segment", "chainage_from_km", "chainage_to_km")
    list_filter = ("furniture_type",)
    readonly_fields = ("created_at", "modified_at")
    fieldsets = (
        ("Road segment", {"fields": ("road_segment", "furniture_type")}),
        (
            "Location", {"fields": (("chainage_from_km", "chainage_to_km"),)}),
        (
            "Presence",
            {"fields": (("left_present", "right_present"),)},
        ),
        ("Notes", {"fields": ("comments",)}),
        ("Timestamps", {"fields": ("created_at", "modified_at")}),
    )


@admin.register(models.StructureConditionSurvey, site=grms_admin_site)
class StructureConditionSurveyAdmin(admin.ModelAdmin):
    list_display = ("structure", "survey_year", "condition_rating", "qa_status")
    list_filter = ("survey_year", "condition_rating")
    readonly_fields = ("created_at", "modified_at")
    fieldsets = (
        ("Structure", {"fields": ("structure",)}),
        (
            "Survey details",
            {
                "fields": (
                    "survey_year",
                    "condition_rating",
                    "inspector_name",
                    "inspection_date",
                    "qa_status",
                )
            },
        ),
        ("Comments & attachments", {"fields": ("comments", "attachments")}),
        ("Audit", {"fields": ("created_at", "modified_at")}),
    )


@admin.register(models.BridgeConditionSurvey, site=grms_admin_site)
class BridgeConditionSurveyAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Structure survey", {"fields": ("structure_survey",)}),
        (
            "Component ratings",
            {
                "fields": (
                    "deck_condition",
                    "abutment_condition",
                    "pier_condition",
                    "wearing_surface",
                    "expansion_joint_ok",
                )
            },
        ),
        ("Remarks", {"fields": ("remarks",)}),
    )


@admin.register(models.CulvertConditionSurvey, site=grms_admin_site)
class CulvertConditionSurveyAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Structure survey", {"fields": ("structure_survey",)}),
        (
            "Component ratings",
            {
                "fields": (
                    "inlet_condition",
                    "outlet_condition",
                    "barrel_condition",
                    "headwall_condition",
                )
            },
        ),
        ("Remarks", {"fields": ("remarks",)}),
    )


@admin.register(models.OtherStructureConditionSurvey, site=grms_admin_site)
class OtherStructureConditionSurveyAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Structure survey", {"fields": ("structure_survey",)}),
        (
            "Component ratings",
            {
                "fields": (
                    "wall_condition",
                    "ford_condition",
                )
            },
        ),
        ("Remarks", {"fields": ("remarks",)}),
    )


@admin.register(models.RoadConditionSurvey, site=grms_admin_site)
class RoadConditionSurveyAdmin(admin.ModelAdmin):
    list_display = ("road_segment", "inspection_date", "calculated_mci", "is_there_bottleneck")
    list_filter = ("inspection_date", "is_there_bottleneck")
    readonly_fields = ("calculated_mci",)
    fieldsets = (
        (
            "Survey header",
            {
                "fields": (
                    "road_segment",
                    ("inspection_date", "inspected_by"),
                )
            },
        ),
        (
            "Drainage & surface condition",
            {
                "description": "Capture field observations that drive the MCI calculation.",
                "fields": (
                    ("drainage_condition_left", "drainage_condition_right"),
                    ("shoulder_condition_left", "shoulder_condition_right"),
                    "surface_condition_factor",
                ),
            },
        ),
        (
            "Bottleneck assessment",
            {
                "fields": (
                    "is_there_bottleneck",
                    "bottleneck_size_m",
                )
            },
        ),
        (
            "Insights & recommendations",
            {
                "fields": (
                    "comments",
                    "calculated_mci",
                    "intervention_recommended",
                )
            },
        ),
    )


@admin.register(models.FurnitureConditionSurvey, site=grms_admin_site)
class FurnitureConditionSurveyAdmin(admin.ModelAdmin):
    list_display = ("furniture", "survey_year", "condition_rating")
    list_filter = ("survey_year", "condition_rating")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Furniture", {"fields": ("furniture",)}),
        (
            "Survey",
            {
                "fields": (
                    "survey_year",
                    "condition_rating",
                    "qa_status",
                    "inspected_by",
                    "inspection_date",
                )
            },
        ),
        ("Notes", {"fields": ("comments",)}),
        ("Created", {"fields": ("created_at",)}),
    )


@admin.register(models.RoadConditionDetailedSurvey, site=grms_admin_site)
class RoadConditionDetailedSurveyAdmin(admin.ModelAdmin):
    list_display = ("road_segment", "distress", "survey_level", "inspection_date")
    list_filter = ("survey_level", "inspection_date", "qa_status")
    fieldsets = (
        (
            "Survey context",
            {
                "fields": (
                    "survey_level",
                    "awp",
                    "road_segment",
                    "inspected_by",
                    "inspection_date",
                    "qa_status",
                )
            },
        ),
        (
            "Distress classification",
            {
                "fields": (
                    "distress",
                    "distress_condition",
                    "severity_code",
                    "extent_code",
                    "extent_percent",
                )
            },
        ),
        (
            "Measurements",
            {
                "fields": (
                    "distress_length_m",
                    "distress_area_m2",
                    "distress_volume_m3",
                    "observed_gravel_thickness_mm",
                    "carriageway_width_m",
                    "shoulder_width_left_m",
                    "shoulder_width_right_m",
                    ("ditch_left_present", "ditch_right_present"),
                )
            },
        ),
        (
            "Activity & quantities",
            {
                "fields": (
                    "activity",
                    "quantity_unit",
                    "quantity_estimated",
                    "quantity_source",
                )
            },
        ),
        ("Notes", {"fields": ("severity_notes", "comments")}),
    )


@admin.register(models.StructureConditionDetailedSurvey, site=grms_admin_site)
class StructureConditionDetailedSurveyAdmin(admin.ModelAdmin):
    list_display = ("structure", "distress", "survey_level", "inspection_date")
    list_filter = ("survey_level", "inspection_date")
    fieldsets = (
        (
            "Survey context",
            {
                "fields": (
                    "survey_level",
                    "awp",
                    "structure",
                    "inspected_by",
                    "inspection_date",
                    "qa_status",
                )
            },
        ),
        (
            "Distress classification",
            {
                "fields": (
                    "distress",
                    "distress_condition",
                    "severity_code",
                    "extent_code",
                )
            },
        ),
        (
            "Measurements",
            {
                "fields": (
                    "distress_length_m",
                    "distress_area_m2",
                    "distress_volume_m3",
                    "check_dam_count",
                )
            },
        ),
        (
            "Activity & quantities",
            {
                "fields": (
                    "activity",
                    "quantity_unit",
                    "quantity_estimated",
                    "computed_by_lookup",
                )
            },
        ),
        ("Notes", {"fields": ("severity_notes", "comments")}),
    )


@admin.register(models.FurnitureConditionDetailedSurvey, site=grms_admin_site)
class FurnitureConditionDetailedSurveyAdmin(admin.ModelAdmin):
    list_display = ("furniture", "distress", "survey_level", "inspection_date")
    list_filter = ("survey_level", "inspection_date")
    fieldsets = (
        (
            "Survey context",
            {
                "fields": (
                    "survey_level",
                    "awp",
                    "furniture",
                    "inspected_by",
                    "inspection_date",
                    "qa_status",
                )
            },
        ),
        (
            "Distress classification",
            {
                "fields": (
                    "distress",
                    "distress_condition",
                    "severity_code",
                    "extent_code",
                )
            },
        ),
        (
            "Activity & quantities",
            {
                "fields": (
                    "activity",
                    "quantity_unit",
                    "quantity_estimated",
                    "computed_by_lookup",
                )
            },
        ),
        ("Notes", {"fields": ("severity_notes", "comments")}),
    )


# Register supporting models without custom admins
for model in [
    models.QAStatus,
    models.AnnualWorkPlan,
    models.ActivityLookup,
    models.DistressType,
    models.DistressCondition,
    models.DistressActivity,
    models.ConditionRating,
    models.ConditionFactor,
    models.InterventionLookup,
    models.UnitCost,
    models.PCULookup,
    models.NightAdjustmentLookup,
    models.BridgeDetail,
    models.CulvertDetail,
    models.FordDetail,
    models.RetainingWallDetail,
    models.GabionWallDetail,
    models.TrafficSurvey,
    models.TrafficCountRecord,
    models.TrafficCycleSummary,
    models.TrafficSurveySummary,
    models.TrafficQC,
    models.TrafficForPrioritization,
    models.StructureIntervention,
    models.RoadSectionIntervention,
    models.BenefitFactor,
    models.PrioritizationResult,
]:
    grms_admin_site.register(model)
