from __future__ import annotations

from typing import Iterable

from django import forms
from django.http import JsonResponse
from django.urls import path

from . import models
from .utils_labels import section_id, segment_label, structure_label


class CascadeSelectMixin:
    road_field_name = "road"
    section_field_name = "section"

    def _get_request_value(self, request, name: str):
        return request.POST.get(name) or request.GET.get(name)

    def _option_payload(self, items: Iterable[dict]) -> JsonResponse:
        return JsonResponse({"results": list(items)})


class RoadSectionCascadeAdminMixin(CascadeSelectMixin):
    section_options_url_name = "section-options"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "section-options/",
                self.admin_site.admin_view(self.section_options_view),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_section_options",
            )
        ]
        return custom + urls

    def section_queryset(self, road_id: str | None):
        if road_id and road_id.isdigit():
            return models.RoadSection.objects.filter(road_id=int(road_id))
        return models.RoadSection.objects.none()

    def section_options_view(self, request):
        road_id = request.GET.get("road_id")
        sections = self.section_queryset(road_id)
        items = (
            {
                "id": section.id,
                "label": section_id(section),
            }
            for section in sections
        )
        return self._option_payload(items)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == self.section_field_name:
            road_id = self._get_request_value(request, self.road_field_name)
            if road_id:
                kwargs["queryset"] = self.section_queryset(road_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class RoadSectionSegmentCascadeAdminMixin(RoadSectionCascadeAdminMixin):
    segment_field_name = "road_segment"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "segment-options/",
                self.admin_site.admin_view(self.segment_options_view),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_segment_options",
            )
        ]
        return custom + urls

    def segment_queryset(self, section_id: str | None):
        if section_id and section_id.isdigit():
            return models.RoadSegment.objects.filter(section_id=int(section_id))
        return models.RoadSegment.objects.none()

    def segment_options_view(self, request):
        section_id = request.GET.get("section_id")
        segments = self.segment_queryset(section_id)
        items = (
            {
                "id": segment.id,
                "label": segment_label(segment),
            }
            for segment in segments
        )
        return self._option_payload(items)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == self.segment_field_name:
            section_id = self._get_request_value(request, self.section_field_name)
            if section_id:
                kwargs["queryset"] = self.segment_queryset(section_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class RoadSectionStructureCascadeAdminMixin(RoadSectionCascadeAdminMixin):
    structure_field_name = "structure"
    structure_category_codes: Iterable[str] | None = None

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "structure-options/",
                self.admin_site.admin_view(self.structure_options_view),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_structure_options",
            )
        ]
        return custom + urls

    def structure_queryset(self, road_id: str | None, section_id: str | None):
        qs = models.StructureInventory.objects.all()
        if road_id and road_id.isdigit():
            qs = qs.filter(road_id=int(road_id))
        if section_id and section_id.isdigit():
            qs = qs.filter(section_id=int(section_id))
        if self.structure_category_codes:
            qs = qs.filter(structure_category__in=list(self.structure_category_codes))
        return qs

    def structure_options_view(self, request):
        road_id = request.GET.get("road_id")
        section_id = request.GET.get("section_id")
        structures = self.structure_queryset(road_id, section_id)
        items = (
            {
                "id": structure.id,
                "label": structure_label(structure),
            }
            for structure in structures
        )
        return self._option_payload(items)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == self.structure_field_name:
            road_id = self._get_request_value(request, self.road_field_name)
            section_id = self._get_request_value(request, self.section_field_name)
            kwargs["queryset"] = self.structure_queryset(road_id, section_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class RoadSectionFilterForm(forms.ModelForm):
    road = forms.ModelChoiceField(
        queryset=models.Road.objects.all(),
        required=False,
        label="Road",
    )


class RoadSectionSegmentFilterForm(forms.ModelForm):
    road = forms.ModelChoiceField(
        queryset=models.Road.objects.all(),
        required=False,
        label="Road",
    )
    section = forms.ModelChoiceField(
        queryset=models.RoadSection.objects.all(),
        required=False,
        label="Section",
    )
