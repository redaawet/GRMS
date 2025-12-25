from __future__ import annotations

from typing import Iterable

from django import forms
from django.contrib.admin.widgets import AutocompleteSelect
from django.http import JsonResponse
from django.urls import path

from . import models
from .utils_labels import structure_label
from .validators import (
    validate_furniture_belongs_to_road,
    validate_furniture_belongs_to_section,
    validate_section_belongs_to_road,
    validate_segment_belongs_to_road,
    validate_segment_belongs_to_section,
    validate_structure_belongs_to_road,
    validate_structure_belongs_to_section,
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


class CascadeRoadSectionMixin:
    road_field_name = "road"
    section_field_name = "section"

    def _setup_road_section(self):
        road_id = _field_value(self, self.road_field_name)
        section_field = self.fields.get(self.section_field_name)
        if section_field is None or not hasattr(section_field, "queryset"):
            return
        if road_id and str(road_id).isdigit():
            section_field.queryset = models.RoadSection.objects.filter(
                road_id=int(road_id)
            ).order_by("sequence_on_road")
        else:
            section_field.queryset = models.RoadSection.objects.none()
        _configure_cascade(
            section_field,
            parent_id=f"id_{self.road_field_name}",
            url="/admin/grms/options/sections/",
            param="road_id",
            placeholder="Select a section",
        )
        _set_initial_if_empty(self, self.road_field_name, road_id)
        section_id = _field_value(self, self.section_field_name)
        _set_initial_if_empty(self, self.section_field_name, section_id)

    def clean(self):
        cleaned = super().clean()
        road = cleaned.get(self.road_field_name)
        section = cleaned.get(self.section_field_name)
        validate_section_belongs_to_road(road, section)
        return cleaned


class CascadeSectionSegmentMixin(CascadeRoadSectionMixin):
    def _setup_section_segment(self):
        section_id = _field_value(self, self.section_field_name)
        segment_field = _segment_field(self)
        if not segment_field:
            return
        if section_id and str(section_id).isdigit():
            segment_field.queryset = models.RoadSegment.objects.filter(
                section_id=int(section_id)
            ).order_by("sequence_on_section")
        else:
            segment_field.queryset = models.RoadSegment.objects.none()
        _configure_cascade(
            segment_field,
            parent_id=f"id_{self.section_field_name}",
            url="/admin/grms/options/segments/",
            param="section_id",
            placeholder="Select a segment",
        )

    def clean(self):
        cleaned = super().clean()
        section = cleaned.get(self.section_field_name)
        segment_field_name = _segment_field_name(self)
        segment = cleaned.get(segment_field_name) if segment_field_name else None
        if segment_field_name:
            validate_segment_belongs_to_section(section, segment, field=segment_field_name)
            road = cleaned.get(self.road_field_name)
            validate_segment_belongs_to_road(road, segment, field=segment_field_name)
        return cleaned


class CascadeRoadSectionAssetMixin(CascadeRoadSectionMixin):
    asset_field_name = "structure"
    asset_param = "road_id"
    asset_url = ""
    asset_placeholder = None
    asset_model = None

    def _asset_queryset(self, road_id: str | None, section_id: str | None):
        if not self.asset_model:
            return models.StructureInventory.objects.none()
        qs = self.asset_model.objects.all()
        if road_id and str(road_id).isdigit():
            if self.asset_model is models.StructureInventory:
                qs = qs.filter(road_id=int(road_id))
            else:
                qs = qs.filter(section__road_id=int(road_id))
        if section_id and str(section_id).isdigit():
            qs = qs.filter(section_id=int(section_id))
        return qs

    def _setup_asset(self):
        asset_field = self.fields.get(self.asset_field_name)
        if asset_field is None or not hasattr(asset_field, "queryset"):
            return
        road_id = _field_value(self, self.road_field_name)
        section_id = _field_value(self, self.section_field_name)
        if road_id and str(road_id).isdigit():
            asset_field.queryset = self._asset_queryset(road_id, section_id)
        else:
            asset_field.queryset = self.asset_model.objects.none() if self.asset_model else models.StructureInventory.objects.none()
        _configure_cascade(
            asset_field,
            parent_id=f"id_{self.road_field_name}",
            url=self.asset_url,
            param=self.asset_param,
            placeholder=self.asset_placeholder,
            extra=f"id_{self.section_field_name}:section_id",
        )

    def clean(self):
        cleaned = super().clean()
        road = cleaned.get(self.road_field_name)
        section = cleaned.get(self.section_field_name)
        asset = cleaned.get(self.asset_field_name)
        if self.asset_field_name == "structure":
            validate_structure_belongs_to_road(road, asset)
            if section:
                validate_structure_belongs_to_section(section, asset)
        elif self.asset_field_name == "furniture":
            validate_furniture_belongs_to_road(road, asset)
            if section:
                validate_furniture_belongs_to_section(section, asset)
        return cleaned


class RoadSectionFilterForm(CascadeRoadSectionMixin, forms.ModelForm):
    road = forms.ModelChoiceField(
        queryset=models.Road.objects.all(),
        required=False,
        label="Road",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        road_field = self.fields.get("road")
        if road_field is not None:
            from .admin import grms_admin_site

            road_field.widget = AutocompleteSelect(
                models.RoadSection._meta.get_field("road"),
                grms_admin_site,
            )
        self._setup_road_section()


class RoadSectionSegmentFilterForm(CascadeSectionSegmentMixin, RoadSectionFilterForm):
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
        self._setup_section_segment()


def _segment_field_name(form: forms.ModelForm) -> str | None:
    if "road_segment" in form.fields:
        return "road_segment"
    if "segment" in form.fields:
        return "segment"
    return None


def _segment_field(form: forms.ModelForm):
    name = _segment_field_name(form)
    return form.fields.get(name) if name else None


def _set_initial_if_empty(form: forms.ModelForm, name: str, value):
    field = form.fields.get(name)
    if not field:
        return
    if form.is_bound:
        return
    if field.initial:
        return
    if value:
        field.initial = value


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
        structure = getattr(instance, "structure", None)
        if structure:
            return structure.road_id
        furniture = getattr(instance, "furniture", None)
        if furniture:
            return furniture.section.road_id
    if name == "section":
        section_id = getattr(instance, "section_id", None)
        if section_id:
            return section_id
        segment = getattr(instance, "road_segment", None)
        if segment:
            return segment.section_id
        structure = getattr(instance, "structure", None)
        if structure:
            return structure.section_id
        furniture = getattr(instance, "furniture", None)
        if furniture:
            return furniture.section_id
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
