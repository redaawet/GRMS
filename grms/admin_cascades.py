from __future__ import annotations

from typing import Iterable

from django import forms
from django.http import JsonResponse
from django.urls import path

from . import models
from .utils_labels import structure_label
from .validators import (
    validate_section_belongs_to_road,
    validate_segment_belongs_to_road,
    validate_segment_belongs_to_section,
)


class CascadeSelectMixin:
    road_field_name = "road"
    section_field_name = "section"

    def _get_request_value(self, request, name: str):
        return request.POST.get(name) or request.GET.get(name)

    def _option_payload(self, items: Iterable[dict]) -> JsonResponse:
        return JsonResponse({"results": list(items)})


class RoadSectionCascadeAdminMixin(CascadeSelectMixin):
    def section_queryset(self, road_id: str | None):
        if road_id and road_id.isdigit():
            return models.RoadSection.objects.filter(road_id=int(road_id))
        return models.RoadSection.objects.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == self.section_field_name:
            road_id = self._get_request_value(request, self.road_field_name)
            if road_id:
                kwargs["queryset"] = self.section_queryset(road_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class RoadSectionSegmentCascadeAdminMixin(RoadSectionCascadeAdminMixin):
    segment_field_name = "road_segment"

    def segment_queryset(self, section_id: str | None):
        if section_id and section_id.isdigit():
            return models.RoadSegment.objects.filter(section_id=int(section_id))
        return models.RoadSegment.objects.none()

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        road_id = _field_value(self, "road")
        if road_id and str(road_id).isdigit():
            self.fields["section"].queryset = models.RoadSection.objects.filter(
                road_id=road_id
            ).order_by("sequence_on_road")
        else:
            self.fields["section"].queryset = models.RoadSection.objects.none()
        _configure_cascade(
            self.fields.get("section"),
            parent_id="id_road",
            url="/admin/grms/options/sections/",
            param="road_id",
            placeholder="Select a section",
        )

    def clean(self):
        cleaned = super().clean()
        road = cleaned.get("road")
        section = cleaned.get("section")
        validate_section_belongs_to_road(road, section)
        return cleaned


class RoadSectionSegmentFilterForm(RoadSectionFilterForm):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        section_id = _field_value(self, "section")
        segment_field = _segment_field(self)
        if segment_field:
            if section_id and str(section_id).isdigit():
                segment_field.queryset = models.RoadSegment.objects.filter(
                    section_id=section_id
                ).order_by("sequence_on_section")
            else:
                segment_field.queryset = models.RoadSegment.objects.none()
            _configure_cascade(
                segment_field,
                parent_id="id_section",
                url="/admin/grms/options/segments/",
                param="section_id",
                placeholder="Select a segment",
            )

    def clean(self):
        cleaned = super().clean()
        road = cleaned.get("road")
        section = cleaned.get("section")
        segment_field_name = _segment_field_name(self)
        segment = cleaned.get(segment_field_name) if segment_field_name else None
        if segment_field_name:
            validate_segment_belongs_to_section(section, segment, field=segment_field_name)
            validate_segment_belongs_to_road(road, segment, field=segment_field_name)
        return cleaned


def _segment_field_name(form: forms.ModelForm) -> str | None:
    if "road_segment" in form.fields:
        return "road_segment"
    if "segment" in form.fields:
        return "segment"
    return None


def _segment_field(form: forms.ModelForm):
    name = _segment_field_name(form)
    return form.fields.get(name) if name else None


def _field_value(form: forms.ModelForm, name: str):
    if form.is_bound and name in form.data:
        value = form.data.get(name) or None
        if value:
            return value
    initial_value = form.initial.get(name) if hasattr(form, "initial") else None
    if initial_value:
        return getattr(initial_value, "id", initial_value)
    field = form.fields.get(name)
    if field and field.initial:
        return getattr(field.initial, "id", field.initial)
    instance = getattr(form, "instance", None)
    if not instance:
        return None
    if name == "road":
        road_id = getattr(instance, "road_id", None)
        if road_id:
            return road_id
        section = getattr(instance, "section", None)
        if section:
            return section.road_id
        segment = getattr(instance, "road_segment", None)
        if segment:
            return segment.section.road_id
    if name == "section":
        section_id = getattr(instance, "section_id", None)
        if section_id:
            return section_id
        segment = getattr(instance, "road_segment", None)
        if segment:
            return segment.section_id
    return None


def _configure_cascade(
    field,
    *,
    parent_id: str,
    url: str,
    param: str,
    placeholder: str | None = None,
    extra: str | None = None,
):
    if not field:
        return
    attrs = field.widget.attrs
    attrs.setdefault("data-cascade-parent", parent_id)
    attrs.setdefault("data-cascade-url", url)
    attrs.setdefault("data-cascade-param", param)
    if placeholder:
        attrs.setdefault("data-cascade-placeholder", placeholder)
    if extra:
        attrs.setdefault("data-cascade-extra", extra)
