from django.conf import settings
from django.contrib import admin
from django import forms

from . import models
from .services import google_maps
from .utils import make_point, point_to_lat_lng


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


@admin.register(models.Road)
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
            None,
            {
                "fields": (
                    ("road_name_from", "road_name_to"),
                    "design_standard",
                    ("admin_zone", "admin_woreda"),
                    "total_length_km",
                    "surface_type",
                    "managing_authority",
                    "population_served",
                    "year_of_update",
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
            "google_maps_api_key": getattr(settings, "GOOGLE_MAPS_API_KEY", "") or "",
            "api": {
                "route": self._reverse_or_empty("road_route", road_id),
                "map_context": self._reverse_or_empty("road_map_context", road_id),
            },
        }
        extra_context["travel_modes"] = sorted(google_maps.TRAVEL_MODES)
        return super().changeform_view(request, object_id, form_url, extra_context)

    @staticmethod
    def _reverse_or_empty(name: str, object_id):
        from django.urls import reverse

        if not object_id:
            return ""
        return reverse(name, args=[object_id])


admin.site.register(models.AdminZone)
admin.site.register(models.AdminWoreda)
admin.site.register(models.RoadSection)
admin.site.register(models.RoadSegment)
admin.site.register(models.StructureInventory)
admin.site.register(models.FurnitureInventory)
admin.site.register(models.QAStatus)
admin.site.register(models.AnnualWorkPlan)
admin.site.register(models.ActivityLookup)
admin.site.register(models.DistressType)
admin.site.register(models.DistressCondition)
admin.site.register(models.DistressActivity)
admin.site.register(models.RoadConditionSurvey)
admin.site.register(models.RoadConditionDetailedSurvey)
admin.site.register(models.StructureConditionDetailedSurvey)
admin.site.register(models.FurnitureConditionDetailedSurvey)
