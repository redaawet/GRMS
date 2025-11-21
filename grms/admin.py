from __future__ import annotations

from typing import Dict, List, Sequence

from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.shortcuts import redirect
from django.utils.html import format_html

from . import models
from .services import map_services
from .utils import make_point, point_to_lat_lng, utm_to_wgs84, wgs84_to_utm


def _to_float(value):
    return float(value) if value is not None else None


def _road_map_context_url(road_id):
    from django.urls import reverse

    if not road_id:
        return ""
    return reverse("road_map_context", args=[road_id])


class GRMSAdminSite(AdminSite):
    site_header = "GRMS Administration"
    site_title = "GRMS Admin"
    index_title = "Gravel Road Management System"
    index_template = "admin/grms_index.html"

    SECTION_DEFINITIONS: Sequence[Dict[str, object]] = (
        {
            "title": "Inventories",
            "models": (
                models.Road._meta.verbose_name_plural,
                models.RoadSection._meta.verbose_name_plural,
                models.RoadSegment._meta.verbose_name_plural,
                models.StructureInventory._meta.verbose_name_plural,
                models.FurnitureInventory._meta.verbose_name_plural,
                models.BridgeDetail._meta.verbose_name_plural,
                models.CulvertDetail._meta.verbose_name_plural,
                models.FordDetail._meta.verbose_name_plural,
                models.RetainingWallDetail._meta.verbose_name_plural,
                models.GabionWallDetail._meta.verbose_name_plural,
            ),
        },
        {
            "title": "Surveys – Condition",
            "models": (
                models.RoadConditionSurvey._meta.verbose_name_plural,
                models.StructureConditionSurvey._meta.verbose_name_plural,
                models.BridgeConditionSurvey._meta.verbose_name_plural,
                models.CulvertConditionSurvey._meta.verbose_name_plural,
                models.OtherStructureConditionSurvey._meta.verbose_name_plural,
                models.FurnitureConditionSurvey._meta.verbose_name_plural,
            ),
        },
        {
            "title": "Surveys – Severity & extent",
            "models": (
                models.RoadConditionDetailedSurvey._meta.verbose_name_plural,
                models.StructureConditionDetailedSurvey._meta.verbose_name_plural,
                models.FurnitureConditionDetailedSurvey._meta.verbose_name_plural,
            ),
        },
        {
            "title": "Surveys – Traffic",
            "models": (
                models.TrafficSurvey._meta.verbose_name_plural,
                models.TrafficCountRecord._meta.verbose_name_plural,
                models.TrafficCycleSummary._meta.verbose_name_plural,
                models.TrafficSurveySummary._meta.verbose_name_plural,
                models.TrafficQC._meta.verbose_name_plural,
                models.TrafficForPrioritization._meta.verbose_name_plural,
                models.PCULookup._meta.verbose_name_plural,
                models.NightAdjustmentLookup._meta.verbose_name_plural,
            ),
        },
        {
            "title": "Maintenance & planning",
            "models": (
                models.AnnualWorkPlan._meta.verbose_name_plural,
                models.StructureIntervention._meta.verbose_name_plural,
                models.RoadSectionIntervention._meta.verbose_name_plural,
                models.BenefitFactor._meta.verbose_name_plural,
                models.PrioritizationResult._meta.verbose_name_plural,
            ),
        },
        {
            "title": "Reference data",
            "models": (
                models.ConditionRating._meta.verbose_name_plural,
                models.ConditionFactor._meta.verbose_name_plural,
                models.QAStatus._meta.verbose_name_plural,
                models.ActivityLookup._meta.verbose_name_plural,
                models.InterventionLookup._meta.verbose_name_plural,
                models.UnitCost._meta.verbose_name_plural,
                models.DistressType._meta.verbose_name_plural,
                models.DistressCondition._meta.verbose_name_plural,
                models.DistressActivity._meta.verbose_name_plural,
                models.AdminZone._meta.verbose_name_plural,
                models.AdminWoreda._meta.verbose_name_plural,
            ),
        },
    )

    @staticmethod
    def _normalise(name: str) -> str:
        return name.replace("_", " ").strip().lower()

    def _build_model_lookup(
        self, app_list: List[Dict[str, object]]
    ) -> Dict[str, List[Dict[str, object]]]:
        lookup: Dict[str, List[Dict[str, object]]] = {}
        for app in app_list:
            app_label = app.get("app_label")
            for model in app["models"]:
                model.setdefault("app_label", app_label)
                for key in (model["object_name"], model["name"]):
                    normalised = self._normalise(key)
                    lookup.setdefault(normalised, []).append(model)
        return lookup

    def _all_models(self, app_list: List[Dict[str, object]]):
        for app in app_list:
            for model in app["models"]:
                yield model

    def _build_sections(self, request) -> List[Dict[str, object]]:
        app_list = self.get_app_list(request)
        lookup = self._build_model_lookup(app_list)
        assigned: set[tuple[str | None, str]] = set()
        sections: List[Dict[str, object]] = []
        for definition in self.SECTION_DEFINITIONS:
            models: List[Dict[str, object]] = []
            for target in definition.get("models", ()):  # type: ignore[arg-type]
                for model in lookup.get(self._normalise(target), []):
                    identifier = (model.get("app_label"), model["object_name"])
                    if identifier not in assigned:
                        models.append(model)
                        assigned.add(identifier)
            if models:
                sections.append({"title": definition["title"], "models": models})
        leftovers = [
            model
            for model in sorted(self._all_models(app_list), key=lambda item: item["name"])
            if (model.get("app_label"), model["object_name"]) not in assigned
        ]
        if leftovers:
            sections.append({"title": "Other models", "models": leftovers})
        return sections

    def each_context(self, request):
        context = super().each_context(request)
        context["sections"] = self._build_sections(request)
        return context

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
    start_easting = forms.DecimalField(label="Start easting", required=False, max_digits=12, decimal_places=2)
    start_northing = forms.DecimalField(label="Start northing", required=False, max_digits=12, decimal_places=2)
    start_lat = forms.FloatField(label="Start latitude", required=False)
    start_lng = forms.FloatField(label="Start longitude", required=False)
    end_easting = forms.DecimalField(label="End easting", required=False, max_digits=12, decimal_places=2)
    end_northing = forms.DecimalField(label="End northing", required=False, max_digits=12, decimal_places=2)
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
        if getattr(self.instance, "start_easting", None) is not None:
            self.fields["start_easting"].initial = self.instance.start_easting
        if getattr(self.instance, "start_northing", None) is not None:
            self.fields["start_northing"].initial = self.instance.start_northing
        if getattr(self.instance, "end_easting", None) is not None:
            self.fields["end_easting"].initial = self.instance.end_easting
        if getattr(self.instance, "end_northing", None) is not None:
            self.fields["end_northing"].initial = self.instance.end_northing

    @staticmethod
    def _quantize_utm(value: float) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _populate_coordinates(self, prefix: str):
        lat = self.cleaned_data.get(f"{prefix}_lat")
        lng = self.cleaned_data.get(f"{prefix}_lng")
        easting = self.cleaned_data.get(f"{prefix}_easting")
        northing = self.cleaned_data.get(f"{prefix}_northing")

        has_lat = lat is not None
        has_lng = lng is not None
        has_easting = easting is not None
        has_northing = northing is not None

        latlng_complete = has_lat and has_lng
        utm_complete = has_easting and has_northing

        if latlng_complete and utm_complete:
            return {"lat": float(lat), "lng": float(lng)}

        if latlng_complete:
            try:
                easting_val, northing_val = wgs84_to_utm(float(lat), float(lng), zone=37)
            except ImportError as exc:
                raise forms.ValidationError(str(exc))
            self.cleaned_data[f"{prefix}_easting"] = self._quantize_utm(easting_val)
            self.cleaned_data[f"{prefix}_northing"] = self._quantize_utm(northing_val)
            return {"lat": float(lat), "lng": float(lng)}

        if utm_complete:
            try:
                lat_val, lon_val = utm_to_wgs84(float(easting), float(northing), zone=37)
            except ImportError as exc:
                raise forms.ValidationError(str(exc))
            self.cleaned_data[f"{prefix}_lat"] = lat_val
            self.cleaned_data[f"{prefix}_lng"] = lon_val
            return {"lat": lat_val, "lng": lon_val}

        if has_easting or has_northing:
            missing = "northing" if has_easting else "easting"
            raise forms.ValidationError({f"{prefix}_{missing}": "Provide both easting and northing or a latitude/longitude pair."})

        if has_lat or has_lng:
            missing = "lng" if has_lat else "lat"
            raise forms.ValidationError({f"{prefix}_{missing}": "Provide both latitude and longitude or a UTM easting/northing pair."})

        return None

    def _clean_point(self, prefix: str):
        lat = self.cleaned_data.get(f"{prefix}_lat")
        lng = self.cleaned_data.get(f"{prefix}_lng")
        if lat is None and lng is None:
            return None
        return make_point(lat, lng)

    def clean(self):
        cleaned = super().clean()
        self._populate_coordinates("start")
        self._populate_coordinates("end")
        start_point = self._clean_point("start")
        end_point = self._clean_point("end")
        cleaned["road_start_coordinates"] = start_point
        cleaned["road_end_coordinates"] = end_point
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
                "description": "Capture the start and end of the road in UTM (Zone 37N) or decimal degrees (WGS84).",
                "fields": (
                    ("start_easting", "start_northing"),
                    ("end_easting", "end_northing"),
                    ("start_lat", "start_lng"),
                    ("end_lat", "end_lng"),
                ),
            },
        ),
    )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        road_id = int(object_id) if object_id and object_id.isdigit() else None
        if road_id:
            map_context_url = self._reverse_or_empty("road_map_context", road_id)
        else:
            from django.urls import reverse

            map_context_url = reverse("road_map_context_default")
        extra_context["road_admin_config"] = {
            "road_id": road_id,
            "api": {
                "route": self._reverse_or_empty("road_route", road_id),
                "map_context": map_context_url,
            },
        }
        extra_context["travel_modes"] = sorted(map_services.TRAVEL_MODES)
        return super().changeform_view(request, object_id, form_url, extra_context)


class RoadSectionAdminForm(forms.ModelForm):
    start_easting = forms.DecimalField(label="Start easting", required=False, max_digits=12, decimal_places=2)
    start_northing = forms.DecimalField(label="Start northing", required=False, max_digits=12, decimal_places=2)
    start_lat = forms.FloatField(label="Start latitude", required=False)
    start_lng = forms.FloatField(label="Start longitude", required=False)
    end_easting = forms.DecimalField(label="End easting", required=False, max_digits=12, decimal_places=2)
    end_northing = forms.DecimalField(label="End northing", required=False, max_digits=12, decimal_places=2)
    end_lat = forms.FloatField(label="End latitude", required=False)
    end_lng = forms.FloatField(label="End longitude", required=False)

    class Meta:
        model = models.RoadSection
        exclude = (
            "section_start_coordinates",
            "section_end_coordinates",
        )

    @staticmethod
    def _quantize_utm(value: float) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        start = point_to_lat_lng(getattr(self.instance, "section_start_coordinates", None))
        end = point_to_lat_lng(getattr(self.instance, "section_end_coordinates", None))
        if start:
            self.fields["start_lat"].initial = start["lat"]
            self.fields["start_lng"].initial = start["lng"]
        if end:
            self.fields["end_lat"].initial = end["lat"]
            self.fields["end_lng"].initial = end["lng"]

        for field_name in (
            "start_easting",
            "start_northing",
            "end_easting",
            "end_northing",
        ):
            if getattr(self.instance, field_name, None) is not None:
                self.fields[field_name].initial = getattr(self.instance, field_name)

    def _populate_coordinates(self, prefix: str):
        lat = self.cleaned_data.get(f"{prefix}_lat")
        lng = self.cleaned_data.get(f"{prefix}_lng")
        easting = self.cleaned_data.get(f"{prefix}_easting")
        northing = self.cleaned_data.get(f"{prefix}_northing")

        has_lat = lat is not None
        has_lng = lng is not None
        has_easting = easting is not None
        has_northing = northing is not None

        latlng_complete = has_lat and has_lng
        utm_complete = has_easting and has_northing

        if latlng_complete and utm_complete:
            return {"lat": float(lat), "lng": float(lng)}

        if latlng_complete:
            try:
                easting_val, northing_val = wgs84_to_utm(float(lat), float(lng), zone=37)
            except ImportError as exc:
                raise forms.ValidationError(str(exc))
            self.cleaned_data[f"{prefix}_easting"] = self._quantize_utm(easting_val)
            self.cleaned_data[f"{prefix}_northing"] = self._quantize_utm(northing_val)
            return {"lat": float(lat), "lng": float(lng)}

        if utm_complete:
            try:
                lat_val, lon_val = utm_to_wgs84(float(easting), float(northing), zone=37)
            except ImportError as exc:
                raise forms.ValidationError(str(exc))
            self.cleaned_data[f"{prefix}_lat"] = lat_val
            self.cleaned_data[f"{prefix}_lng"] = lon_val
            return {"lat": lat_val, "lng": lon_val}

        if has_easting or has_northing:
            missing = "northing" if has_easting else "easting"
            raise forms.ValidationError({f"{prefix}_{missing}": "Provide both easting and northing or a latitude/longitude pair."})

        if has_lat or has_lng:
            missing = "lng" if has_lat else "lat"
            raise forms.ValidationError({f"{prefix}_{missing}": "Provide both latitude and longitude or a UTM easting/northing pair."})

        return None

    def _clean_point(self, prefix: str):
        lat = self.cleaned_data.get(f"{prefix}_lat")
        lng = self.cleaned_data.get(f"{prefix}_lng")
        if lat is None and lng is None:
            return None
        return make_point(lat, lng)

    def clean(self):
        cleaned = super().clean()
        self._populate_coordinates("start")
        self._populate_coordinates("end")
        cleaned["section_start_coordinates"] = self._clean_point("start")
        cleaned["section_end_coordinates"] = self._clean_point("end")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.section_start_coordinates = self.cleaned_data.get("section_start_coordinates")
        instance.section_end_coordinates = self.cleaned_data.get("section_end_coordinates")
        if commit:
            instance.save()
            self.save_m2m()
        return instance

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
    form = RoadSectionAdminForm
    list_display = (
        "road",
        "section_number",
        "sequence_on_road",
        "length_km",
        "surface_type",
    )
    list_filter = ("surface_type", "road__admin_zone")
    search_fields = ("road__road_name_from", "road__road_name_to", "name")
    readonly_fields = (
        "length_km",
        "map_preview",
    )
    change_form_template = "admin/grms/roadsection/change_form.html"
    fieldsets = (
        ("Parent road", {"fields": ("road",)}),
        (
            "Section identification",
            {"fields": (("section_number", "sequence_on_road"), "name")},
        ),
        (
            "Chainage and length",
            {"fields": (("start_chainage_km", "end_chainage_km"), "length_km")},
        ),
        (
            "Physical characteristics",
            {"fields": ("surface_type", "surface_thickness_cm")},
        ),
        (
            "Administrative overrides",
            {
                "description": "Use only when the section crosses into a new zone or woreda; otherwise the parent road values apply.",
                "fields": ("admin_zone_override", "admin_woreda_override"),
            },
        ),
        ("Notes", {"fields": ("notes",)}),
        (
            "Alignment coordinates",
            {
                "description": "Provide both start and end coordinates in UTM (Zone 37N) or decimal degrees so the map preview and validations can run.",
                "fields": (
                    ("start_easting", "start_northing"),
                    ("end_easting", "end_northing"),
                    ("start_lat", "start_lng"),
                    ("end_lat", "end_lng"),
                ),
            },
        ),
        (
            "Map preview",
            {
                "fields": ("map_preview",),
                "description": "Preview uses the supplied alignment coordinates; refresh to confirm continuity.",
            },
        ),
    )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        instance = self.get_object(request, object_id)
        extra_context["map_admin_config"] = self._build_map_config(instance) if instance else None
        return super().changeform_view(request, object_id, form_url, extra_context)

    def _build_map_config(self, section):
        if not section:
            return None

        road = section.road
        start_point = self._section_point(section)
        end_point = self._section_point(section, end=True)
        return {
            "scope": "section",
            "api": {"map_context": _road_map_context_url(road.id)},
            "road": {
                "id": road.id,
                "length_km": _to_float(road.total_length_km),
                "start": point_to_lat_lng(getattr(road, "road_start_coordinates", None)),
                "end": point_to_lat_lng(getattr(road, "road_end_coordinates", None)),
            },
            "section": {
                "name": section.name,
                "start_chainage_km": _to_float(section.start_chainage_km),
                "end_chainage_km": _to_float(section.end_chainage_km),
                "length_km": _to_float(section.length_km),
                "zone_override_id": section.admin_zone_override_id,
                "woreda_override_id": section.admin_woreda_override_id,
                "points": {
                    "start": start_point,
                    "end": end_point,
                },
            },
            "admin_fields": {
                "zone_override": "id_admin_zone_override",
                "woreda_override": "id_admin_woreda_override",
            },
            "default_admin_selection": {
                "zone_id": section.admin_zone_override_id or road.admin_zone_id,
                "woreda_id": section.admin_woreda_override_id or road.admin_woreda_id,
            },
        }

    @staticmethod
    def map_preview(obj):
        if not obj:
            return "Map preview will appear after saving the section and providing alignment coordinates."

        start = obj.start_chainage_km or Decimal("0.000")
        end = obj.end_chainage_km or Decimal("0.000")
        return format_html(
            "<p>Map preview uses the provided alignment between <strong>{}</strong> km and <strong>{}</strong> km.</p>"
            "<ul><li>Validates chainage continuity and coordinate spacing</li>"
            "<li>Highlights the section extents</li>"
            "<li>Shows admin boundaries, towns, and optional base layers</li></ul>",
            start,
            end,
        )

    @staticmethod
    def _section_point(section, end: bool = False):
        if not section:
            return None

        source = section.section_end_coordinates if end else section.section_start_coordinates
        if not source:
            chainage = section.end_chainage_km if end else section.start_chainage_km
            return RoadSectionAdmin._interpolated_point(section, chainage)

        point = point_to_lat_lng(source)
        if not point:
            return None

        try:
            easting, northing = wgs84_to_utm(point["lat"], point["lng"], zone=37)
        except ImportError:
            easting = northing = None

        point["easting"] = easting
        point["northing"] = northing
        return point

    @staticmethod
    def _interpolated_point(section, chainage):
        if chainage is None:
            return None

        road = section.road
        road_length = road.total_length_km
        start = point_to_lat_lng(getattr(road, "road_start_coordinates", None))
        end = point_to_lat_lng(getattr(road, "road_end_coordinates", None))

        if not road_length or road_length <= 0 or not start or not end:
            return None

        fraction = float(chainage) / float(road_length)
        fraction = max(0.0, min(1.0, fraction))
        lat = start["lat"] + (end["lat"] - start["lat"]) * fraction
        lng = start["lng"] + (end["lng"] - start["lng"]) * fraction

        try:
            easting, northing = wgs84_to_utm(lat, lng, zone=37)
        except ImportError:
            easting = northing = None

        return {
            "lat": lat,
            "lng": lng,
            "easting": easting,
            "northing": northing,
        }


@admin.register(models.RoadSegment, site=grms_admin_site)
class RoadSegmentAdmin(admin.ModelAdmin):
    list_display = ("section", "station_from_km", "station_to_km", "cross_section")
    search_fields = ("section__road__road_name_from", "section__road__road_name_to")
    change_form_template = "admin/grms/roadsegment/change_form.html"
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

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        instance = self.get_object(request, object_id)
        extra_context["map_admin_config"] = self._build_map_config(instance) if instance else None
        return super().changeform_view(request, object_id, form_url, extra_context)

    def _build_map_config(self, segment):
        if not segment:
            return None

        section = segment.section
        road = section.road
        return {
            "scope": "segment",
            "api": {"map_context": _road_map_context_url(road.id)},
            "road": {
                "id": road.id,
                "length_km": _to_float(road.total_length_km),
                "start": point_to_lat_lng(getattr(road, "road_start_coordinates", None)),
                "end": point_to_lat_lng(getattr(road, "road_end_coordinates", None)),
            },
            "section": {
                "name": section.name,
                "start_chainage_km": _to_float(section.start_chainage_km),
                "end_chainage_km": _to_float(section.end_chainage_km),
                "length_km": _to_float(section.length_km),
                "zone_override_id": section.admin_zone_override_id,
                "woreda_override_id": section.admin_woreda_override_id,
            },
            "segment": {
                "station_from_km": _to_float(segment.station_from_km),
                "station_to_km": _to_float(segment.station_to_km),
            },
            "default_admin_selection": {
                "zone_id": section.admin_zone_override_id or road.admin_zone_id,
                "woreda_id": section.admin_woreda_override_id or road.admin_woreda_id,
            },
        }


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
