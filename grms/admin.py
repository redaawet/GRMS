from __future__ import annotations

import json
from typing import Dict, List, Sequence, Tuple

from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.db.models import Count, Sum
from django.template.response import TemplateResponse
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html

from . import models
from .menu import MENU_GROUPS as DEFAULT_MENU_GROUPS
from traffic.models import TrafficSurveyOverall
from .gis_fields import LineStringField, PointField
from .services import map_services, prioritization
from .utils import make_point, point_to_lat_lng, utm_to_wgs84, wgs84_to_utm

try:  # pragma: no cover - depends on spatial libs
    from django.contrib.gis.forms import OSMWidget
except Exception:  # pragma: no cover - fallback when GIS libs missing
    OSMWidget = None


def _serialize_geometry(geom):
    if not geom:
        return None
    if hasattr(geom, "geojson"):
        try:
            return json.loads(geom.geojson)
        except Exception:
            pass
    if isinstance(geom, (dict, list)):
        return geom
    if isinstance(geom, str):
        try:
            return json.loads(geom)
        except Exception:
            return None
    return None


def _to_float(value):
    return float(value) if value is not None else None


def _road_map_context_url(road_id):
    from django.urls import reverse

    if not road_id:
        return ""
    return reverse("road_map_context", args=[road_id])


def _reverse_or_empty(name: str, object_id):
    from django.urls import reverse

    if not object_id:
        return ""
    return reverse(name, args=[object_id])


class GRMSAdminSite(AdminSite):
    site_header = "GRMS Administration"
    site_title = "GRMS Admin"
    index_title = "Gravel Road Management System"
    index_template = "admin/index.html"
    site_url = "/"

    EXCLUDED_MODEL_NAMES = {
        "traffic values for prioritization",
        "trafficforprioritization",
    }

    MENU_GROUPS: Dict[str, Sequence[str | Tuple[str, str]]] = DEFAULT_MENU_GROUPS

    @staticmethod
    def _normalise(name: str) -> str:
        """
        Normalize labels to guarantee consistent matching between:
        - MENU_GROUPS entries
        - Django model object_name
        - Verbose names

        Removes spaces, underscores, and lowercases everything.
        Example:
            "RoadSection", "Road Section", "road_section" → "roadsection"
        """
        if not name:
            return ""
        return name.replace("_", "").replace(" ", "").strip().lower()

    @staticmethod
    def _parse_menu_target(target: str | Tuple[str, str]) -> Tuple[str, str]:
        """Return (lookup_label, display_label) for mixed menu definitions."""
        if isinstance(target, tuple):
            lookup_label, display_label = target
            return lookup_label, display_label

        return target, target

    def _build_model_lookup(
        self, app_list: List[Dict[str, object]]
    ) -> Dict[str, List[Dict[str, object]]]:
        lookup: Dict[str, List[Dict[str, object]]] = {}
        for app in app_list:
            app_label = app.get("app_label")
            for model in app["models"]:
                if any(
                    self._normalise(model.get(key, "")) in self.EXCLUDED_MODEL_NAMES
                    for key in ("name", "object_name")
                ):
                    continue
                model_copy = dict(model)
                model_copy.setdefault("app_label", app_label)
                raw_name = model_copy.get("object_name") or model_copy.get("name", "")
                normalised = self._normalise(raw_name)
                lookup.setdefault(normalised, []).append(model_copy)
        return lookup

    def _build_sections(self, request) -> List[Dict[str, object]]:
        app_list = self.get_app_list(request)
        lookup = self._build_model_lookup(app_list)
        assigned: set[tuple[str | None, str]] = set()
        sections: List[Dict[str, object]] = []

        for title, models in self.MENU_GROUPS.items():
            grouped_models: List[Dict[str, object]] = []
            for target in models:
                lookup_label, display_name = self._parse_menu_target(target)
                for model in lookup.get(self._normalise(lookup_label), []):
                    identifier = (model.get("app_label"), model["object_name"])
                    if identifier in assigned:
                        continue
                    model_entry = dict(model)
                    model_entry["name"] = display_name
                    grouped_models.append(model_entry)
                    assigned.add(identifier)
            if grouped_models:
                sections.append({"title": title, "models": grouped_models})

        leftovers: List[Dict[str, object]] = []
        other_section = next(
            (section for section in sections if section["title"] == "Other models"),
            None,
        )
        for models in lookup.values():
            for model in models:
                identifier = (model.get("app_label"), model["object_name"])
                if identifier not in assigned:
                    leftovers.append(model)
                    assigned.add(identifier)
        if leftovers:
            if other_section:
                other_section["models"].extend(leftovers)
            else:
                sections.append({"title": "Other models", "models": leftovers})
        return sections

    def each_context(self, request):
        context = super().each_context(request)
        context["sections"] = self._build_sections(request)
        return context

    def index(self, request, extra_context=None):
        app_list = self.get_app_list(request)
        base_ctx = self.each_context(request)
        total_roads = models.Road.objects.count()
        total_sections = models.RoadSection.objects.count()
        total_segments = models.RoadSegment.objects.count()
        planned_interventions = (
            models.RoadSectionIntervention.objects.count()
            + models.StructureIntervention.objects.count()
        )

        traffic_qs = (
            TrafficSurveyOverall.objects.values("fiscal_year")
            .annotate(total_adt=Sum("adt_total"))
            .order_by("-fiscal_year")
        )
        latest_traffic_year = (
            traffic_qs.first()["fiscal_year"] if traffic_qs.exists() else None
        )
        traffic_summary = list(traffic_qs[:5])
        traffic_summary.reverse()
        traffic_years = [entry["fiscal_year"] for entry in traffic_summary]
        traffic_values = [float(entry["total_adt"]) for entry in traffic_summary]

        surface_counts = (
            models.Road.objects.values("surface_type")
            .annotate(total=Count("id"))
            .order_by()
        )
        asphalt_count = gravel_count = dirt_count = 0
        for item in surface_counts:
            surface = item.get("surface_type") or ""
            count = item.get("total", 0)
            if surface in {"Paved", "Asphalt", "DBST", "Sealed"}:
                asphalt_count += count
            elif surface == "Gravel":
                gravel_count += count
            else:
                dirt_count += count

        road_locations = []
        for road in models.Road.objects.exclude(road_start_coordinates__isnull=True):
            coords = point_to_lat_lng(road.road_start_coordinates)
            if coords:
                road_locations.append(
                    {"lat": coords["lat"], "lon": coords["lng"], "name": str(road)}
                )

        grms_data = {
            "surface": {
                "asphalt": asphalt_count,
                "gravel": gravel_count,
                "dirt": dirt_count,
            },
            "traffic_years": traffic_years,
            "traffic_values": traffic_values,
            "road_locations": road_locations,
        }

        context = {
            **base_ctx,
            **(extra_context or {}),
            "title": "Gravel Road Management System",
            "app_list": app_list,
            "sections": base_ctx.get("sections", []),
            "total_roads": total_roads,
            "total_sections": total_sections,
            "total_segments": total_segments,
            "planned_interventions": planned_interventions,
            "latest_traffic_year": latest_traffic_year,
            "asphalt_count": asphalt_count,
            "gravel_count": gravel_count,
            "dirt_count": dirt_count,
            "traffic_years": json.dumps(traffic_years),
            "traffic_values": json.dumps(traffic_values),
            "road_locations": json.dumps(road_locations),
            "grms_data": grms_data,
        }

        return TemplateResponse(request, "admin/index.html", context)

    def _get_model_from_label(self, label):
        """
        Resolve a label in MENU_GROUPS to a registered model class.
        For example 'Roads', 'TrafficSurvey', 'PCU lookups', etc.
        """
        for model, admin_obj in self._registry.items():
            verbose = getattr(model._meta, "verbose_name", "")
            verbose_plural = getattr(model._meta, "verbose_name_plural", "")
            if label in (verbose, verbose_plural, model.__name__):
                return model
        return None

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
        "road_identifier",
        "road_name_from",
        "road_name_to",
        "admin_zone",
        "admin_woreda",
        "link_type",
        "surface_type",
        "total_length_km",
    )
    list_filter = (
        "admin_zone",
        "admin_woreda",
        "surface_type",
        "managing_authority",
        "design_standard",
        "link_type",
    )
    search_fields = (
        "road_identifier",
        "road_name_from",
        "road_name_to",
        "admin_woreda__name",
        "admin_zone__name",
    )
    change_form_template = "admin/grms/road/change_form.html"
    fieldsets = (
        (
            "Administrative context",
            {
                "fields": (
                    "road_identifier",
                    ("road_name_from", "road_name_to"),
                    ("admin_zone", "admin_woreda"),
                    "year_of_update",
                )
            },
        ),
        (
            "Classification",
            {
                "fields": (
                    "managing_authority",
                    "design_standard",
                    "link_type",
                    "surface_type",
                )
            },
        ),
        (
            "Physical characteristics",
            {
                "fields": (
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
            map_context_url = _reverse_or_empty("road_map_context", road_id)
        else:
            from django.urls import reverse

            map_context_url = reverse("road_map_context_default")
        extra_context["road_admin_config"] = {
            "road_id": road_id,
            "api": {
                "route": _reverse_or_empty("road_route", road_id),
                "geometry": _reverse_or_empty("road_geometry", road_id),
                "map_context": map_context_url,
            },
        }
        extra_context["travel_modes"] = sorted(map_services.TRAVEL_MODES)
        return super().changeform_view(request, object_id, form_url, extra_context)


class RoadSectionAdminForm(forms.ModelForm):
    class Meta:
        model = models.RoadSection
        exclude = (
            "section_start_coordinates",
            "section_end_coordinates",
            "start_easting",
            "start_northing",
            "end_easting",
            "end_northing",
        )

grms_admin_site.register(models.Road, RoadAdmin)


@admin.register(models.RoadLinkTypeLookup, site=grms_admin_site)
class RoadLinkTypeLookupAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "score")
    search_fields = ("name", "code")
    fieldsets = (
        ("Road link type", {"fields": ("name", "code", "score")}),
        ("Notes", {"fields": ("notes",)}),
    )


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
    list_filter = ("road", "admin_zone_override", "admin_woreda_override", "surface_type")
    search_fields = ("road__road_name_from", "road__road_name_to", "name")
    readonly_fields = (
        "length_km",
    )
    change_form_template = "admin/roadsection_change_form.html"
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
    )

    def get_fieldsets(self, request, obj=None):
        """Ensure fields are not repeated across fieldsets to satisfy admin checks."""

        cleaned_fieldsets = []
        seen_fields = set()

        for name, options in super().get_fieldsets(request, obj):
            fields = options.get("fields", ())
            normalised = []

            for entry in fields:
                if isinstance(entry, (list, tuple)):
                    row = [field for field in entry if field not in seen_fields]
                    if row:
                        normalised.append(tuple(row))
                        seen_fields.update(row)
                else:
                    if entry not in seen_fields:
                        normalised.append(entry)
                        seen_fields.add(entry)

            options = dict(options)
            options["fields"] = tuple(normalised)
            cleaned_fieldsets.append((name, options))

        return tuple(cleaned_fieldsets)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/get_geometry/",
                self.admin_site.admin_view(self.get_geometry),
                name="roadsection-get-geometry",
            )
        ]
        return custom + urls

    def get_geometry(self, request, pk):
        section = models.RoadSection.objects.get(pk=pk)
        geometry = _serialize_geometry(getattr(section, "geometry", None))
        start_point = point_to_lat_lng(getattr(section, "section_start_coordinates", None))
        end_point = point_to_lat_lng(getattr(section, "section_end_coordinates", None))
        length_km = float(section.length_km) if section.length_km is not None else None
        return JsonResponse(
            {
                "geometry": geometry,
                "start_point": start_point,
                "end_point": end_point,
                "length_km": length_km,
            }
        )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        instance = self.get_object(request, object_id)
        extra_context["map_admin_config"] = self._build_map_config(instance, request=request)
        extra_context["travel_modes"] = sorted(map_services.TRAVEL_MODES)
        return super().changeform_view(request, object_id, form_url, extra_context)

    def _build_map_config(self, section, request=None):
        road = getattr(section, "road", None)
        if not road and request:
            road_id = request.GET.get("road") or request.GET.get("road__id__exact")
            if road_id and road_id.isdigit():
                road = models.Road.objects.filter(pk=int(road_id)).first()

        if not road:
            map_context_url = reverse("road_map_context_default")
        else:
            map_context_url = _road_map_context_url(road.id)

        start_point = self._section_point(section) if section else None
        end_point = self._section_point(section, end=True) if section else None
        road_start = point_to_lat_lng(getattr(road, "road_start_coordinates", None)) if road else None
        road_end = point_to_lat_lng(getattr(road, "road_end_coordinates", None)) if road else None
        road_geometry = _serialize_geometry(getattr(road, "geometry", None)) if road else None
        section_geometry = _serialize_geometry(getattr(section, "geometry", None)) if section else None

        return {
            "scope": "section",
            "api": {
                "map_context": map_context_url,
                "route": reverse("route_preview"),
            },
            "default_travel_mode": "DRIVING",
            "travel_modes": sorted(map_services.TRAVEL_MODES),
            "road": {
                "id": getattr(road, "id", None),
                "length_km": _to_float(getattr(road, "total_length_km", None)),
                "start": road_start,
                "end": road_end,
                "geometry": road_geometry,
            },
            "section": {
                "id": getattr(section, "id", None),
                "name": getattr(section, "name", None),
                "start_chainage_km": _to_float(getattr(section, "start_chainage_km", None)),
                "end_chainage_km": _to_float(getattr(section, "end_chainage_km", None)),
                "length_km": _to_float(getattr(section, "length_km", None)),
                "zone_override_id": getattr(section, "admin_zone_override_id", None),
                "woreda_override_id": getattr(section, "admin_woreda_override_id", None),
                "geometry": section_geometry,
                "geometry_url": (
                    reverse("admin:roadsection-get-geometry", args=[section.id]) if section else ""
                ),
                "has_parent_geometry": bool(road_geometry),
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
                "zone_id": (
                    getattr(section, "admin_zone_override_id", None)
                    or getattr(road, "admin_zone_id", None)
                ),
                "woreda_id": (
                    getattr(section, "admin_woreda_override_id", None)
                    or getattr(road, "admin_woreda_id", None)
                ),
            },
        }

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
    list_filter = ("section", "terrain_longitudinal", "terrain_transverse")
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
                "geometry": _serialize_geometry(getattr(road, "geometry", None)),
            },
            "section": {
                "name": section.name,
                "start_chainage_km": _to_float(section.start_chainage_km),
                "end_chainage_km": _to_float(section.end_chainage_km),
                "length_km": _to_float(section.length_km),
                "zone_override_id": section.admin_zone_override_id,
                "woreda_override_id": section.admin_woreda_override_id,
                "geometry": _serialize_geometry(getattr(section, "geometry", None)),
                "has_parent_geometry": bool(getattr(section, "geometry", None)),
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
    geometry_widget = (
        OSMWidget(attrs={"map_width": 800, "map_height": 500})
        if OSMWidget
        else forms.Textarea(attrs={"rows": 3})
    )

    list_display = (
        "road",
        "structure_category",
        "geometry_type",
        "station_km",
        "start_chainage_km",
        "end_chainage_km",
    )
    list_filter = ("structure_category", "geometry_type")
    search_fields = ("road__road_name_from", "road__road_name_to")
    readonly_fields = ("created_date", "modified_date")
    formfield_overrides = {
        PointField: {"widget": geometry_widget},
        LineStringField: {"widget": geometry_widget},
    }

    fieldsets = (
        (
            "Structure",
            {
                "fields": (
                    "road",
                    "section",
                    "structure_category",
                    "structure_name",
                )
            },
        ),
        (
            "Point location",
            {
                "classes": ("structure-point",),
                "fields": (
                    "station_km",
                    "location_point",
                ),
            },
        ),
        (
            "Line location",
            {
                "classes": ("structure-line",),
                "fields": (
                    "start_chainage_km",
                    "end_chainage_km",
                    "location_line",
                ),
            },
        ),
        ("Documentation", {"fields": ("comments", "attachments")}),
        ("Timestamps", {"fields": ("created_date", "modified_date")}),
    )

    class Media:
        js = ("grms/js/structure-inventory-admin.js",)


@admin.register(models.BridgeDetail, site=grms_admin_site)
class BridgeDetailAdmin(admin.ModelAdmin):
    list_display = ("structure", "bridge_type", "span_count", "has_head_walls")
    fieldsets = (
        ("Structure", {"fields": ("structure",)}),
        (
            "Bridge details",
            {
                "fields": (
                    "bridge_type",
                    ("span_count", "width_m", "length_m"),
                    "has_head_walls",
                )
            },
        ),
    )


@admin.register(models.CulvertDetail, site=grms_admin_site)
class CulvertDetailAdmin(admin.ModelAdmin):
    class CulvertDetailForm(forms.ModelForm):
        class Media:
            js = ("grms/js/culvert-detail-admin.js",)

        class Meta:
            model = models.CulvertDetail
            fields = "__all__"

        slab_box_fields = ("width_m", "span_m", "clear_height_m")
        pipe_fields = ("num_pipes", "pipe_diameter_m")

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            culvert_type = (
                self.initial.get("culvert_type")
                or getattr(self.instance, "culvert_type", None)
            )
            self._apply_field_state(culvert_type)

        def _apply_field_state(self, culvert_type: str | None):
            def set_disabled(field_names, disabled: bool):
                for name in field_names:
                    field = self.fields.get(name)
                    if not field:
                        continue
                    field.disabled = disabled
                    if disabled:
                        field.widget.attrs["aria-disabled"] = "true"
                    else:
                        field.widget.attrs.pop("aria-disabled", None)

            if culvert_type in {"Slab Culvert", "Box Culvert"}:
                set_disabled(self.pipe_fields, True)
                set_disabled(self.slab_box_fields, False)
            elif culvert_type == "Pipe Culvert":
                set_disabled(self.slab_box_fields, True)
                set_disabled(self.pipe_fields, False)
            else:
                set_disabled(self.pipe_fields, False)
                set_disabled(self.slab_box_fields, False)

    form = CulvertDetailForm
    list_display = (
        "structure",
        "culvert_type",
        "width_m",
        "span_m",
        "clear_height_m",
        "num_pipes",
        "pipe_diameter_m",
        "has_head_walls",
    )
    fieldsets = (
        ("Structure", {"fields": ("structure",)}),
        ("Culvert type", {"fields": ("culvert_type",)}),
        (
            "Slab/Box dimensions",
            {"fields": (("width_m", "span_m", "clear_height_m"),)},
        ),
        ("Pipe details", {"fields": (("num_pipes", "pipe_diameter_m"),)}),
        ("Head walls", {"fields": ("has_head_walls",)}),
    )


@admin.register(models.FurnitureInventory, site=grms_admin_site)
class FurnitureInventoryAdmin(admin.ModelAdmin):
    class FurnitureInventoryForm(forms.ModelForm):
        class Meta:
            model = models.FurnitureInventory
            fields = "__all__"

        class Media:
            js = ("grms/js/furniture-admin.js",)

    form = FurnitureInventoryForm
    list_display = (
        "furniture_type",
        "section",
        "chainage_km",
        "chainage_from_km",
        "chainage_to_km",
        "left_present",
        "right_present",
    )
    list_filter = ("furniture_type",)
    readonly_fields = ("created_at", "modified_at")
    fieldsets = (
        ("Furniture Info", {"fields": ("furniture_type", "section")}),
        ("Point Furniture", {"fields": ("chainage_km",)}),
        ("Linear Furniture", {"fields": ("chainage_from_km", "chainage_to_km", "left_present", "right_present")}),
        ("Optional GPS", {"fields": ("location_point",)}),
        ("Comments", {"fields": ("comments",)}),
        ("Timestamps", {"fields": ("created_at", "modified_at")}),
    )


@admin.register(models.StructureConditionSurvey, site=grms_admin_site)
class StructureConditionSurveyAdmin(admin.ModelAdmin):
    list_display = ("structure", "survey_year", "condition_code", "condition_rating", "qa_status")
    list_filter = ("survey_year", "condition_rating")
    readonly_fields = ("created_at", "modified_at")
    fieldsets = (
        ("Structure", {"fields": ("structure",)}),
        (
            "Survey details",
            {
                "fields": (
                    "survey_year",
                    "condition_code",
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


@admin.register(models.RoadSocioEconomic, site=grms_admin_site)
class RoadSocioEconomicAdmin(admin.ModelAdmin):
    list_display = (
        "road",
        "population_served",
        "trading_centers",
        "villages",
        "markets",
        "health_centers",
        "education_centers",
    )
    list_filter = ("road__admin_zone", "road__admin_woreda")
    search_fields = ("road__road_identifier", "road__road_name_from", "road__road_name_to")
    fieldsets = (
        ("Context", {"fields": ("road", "population_served", "road_link_type", "notes")}),
        (
            "Transport & Connectivity (BF1)",
            {
                "fields": (
                    "adt_override",
                    "trading_centers",
                    "villages",
                )
            },
        ),
        (
            "Agriculture & Market Access (BF2)",
            {
                "fields": (
                    "farmland_percent",
                    "cooperative_centers",
                    "markets",
                )
            },
        ),
        (
            "Social Services & Development (BF3)",
            {
                "fields": (
                    "health_centers",
                    "education_centers",
                    "development_projects",
                )
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj:
            has_survey = models.TrafficSurveySummary.objects.filter(road=obj.road).exists()
            if has_survey:
                readonly.append("adt_override")
        return readonly


@admin.register(models.BenefitCategory, site=grms_admin_site)
class BenefitCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "weight_display")
    search_fields = ("code", "name")

    @staticmethod
    def weight_display(obj):
        return obj.weight

    weight_display.short_description = "Weight"


@admin.register(models.BenefitCriterion, site=grms_admin_site)
class BenefitCriterionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "weight", "scoring_method")
    list_filter = ("category", "scoring_method")
    search_fields = ("code", "name")


@admin.register(models.BenefitCriterionScale, site=grms_admin_site)
class BenefitCriterionScaleAdmin(admin.ModelAdmin):
    list_display = (
        "criterion",
        "min_value",
        "max_value",
        "score",
        "description",
    )
    list_filter = ("criterion",)
    search_fields = ("criterion__name",)


@admin.register(models.BenefitFactor, site=grms_admin_site)
class BenefitFactorAdmin(admin.ModelAdmin):
    list_display = (
        "road",
        "fiscal_year",
        "bf1_transport_score",
        "bf2_agriculture_score",
        "bf3_social_score",
        "total_benefit_score",
    )
    list_filter = ("fiscal_year", "road__admin_zone", "road__admin_woreda")
    readonly_fields = (
        "road",
        "fiscal_year",
        "bf1_transport_score",
        "bf2_agriculture_score",
        "bf3_social_score",
        "total_benefit_score",
        "calculated_at",
        "notes",
    )
    fieldsets = (
        ("Context", {"fields": ("road", "fiscal_year", "calculated_at", "notes")}),
        (
            "Benefit factors",
            {
                "fields": (
                    "bf1_transport_score",
                    "bf2_agriculture_score",
                    "bf3_social_score",
                    "total_benefit_score",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False if obj else super().has_change_permission(request, obj)


@admin.register(models.PrioritizationResult, site=grms_admin_site)
class PrioritizationResultAdmin(admin.ModelAdmin):
    list_display = (
        "road",
        "fiscal_year",
        "priority_rank",
        "ranking_index",
        "benefit_score",
        "improvement_cost",
    )
    list_filter = ("fiscal_year", "road__admin_zone", "road__admin_woreda")
    search_fields = ("road__road_identifier", "road__road_name_from", "road__road_name_to")
    readonly_fields = (
        "road",
        "section",
        "fiscal_year",
        "population_served",
        "benefit_score",
        "improvement_cost",
        "ranking_index",
        "priority_rank",
        "recommended_budget",
        "approved_budget",
        "calculation_date",
        "notes",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False if obj else super().has_change_permission(request, obj)


@admin.register(models.AnnualWorkPlan, site=grms_admin_site)
class AnnualWorkPlanAdmin(admin.ModelAdmin):
    list_display = ("road", "fiscal_year", "priority_rank", "status", "total_budget")
    list_filter = ("fiscal_year", "road__admin_zone")
    search_fields = ("road__road_identifier", "road__road_name_from", "road__road_name_to")


@admin.register(models.StructureIntervention, site=grms_admin_site)
class StructureInterventionAdmin(admin.ModelAdmin):
    list_display = (
        "structure",
        "intervention",
        "intervention_year",
        "status",
        "estimated_cost",
    )
    list_filter = ("intervention_year", "structure__road__admin_zone")
    search_fields = (
        "structure__road__road_identifier",
        "structure__road__road_name_from",
        "structure__road__road_name_to",
    )


@admin.register(models.RoadSectionIntervention, site=grms_admin_site)
class RoadSectionInterventionAdmin(admin.ModelAdmin):
    list_display = (
        "section",
        "intervention",
        "intervention_year",
        "status",
        "estimated_cost",
    )
    list_filter = ("intervention_year", "section__road__admin_zone")
    search_fields = (
        "section__road__road_identifier",
        "section__road__road_name_from",
        "section__road__road_name_to",
    )

# Register supporting models without custom admins
for model in [
    models.QAStatus,
    models.ActivityLookup,
    models.DistressType,
    models.DistressCondition,
    models.DistressActivity,
    models.ConditionRating,
    models.InterventionLookup,
    models.UnitCost,
    models.FordDetail,
    models.RetainingWallDetail,
    models.GabionWallDetail,
]:
    grms_admin_site.register(model)
