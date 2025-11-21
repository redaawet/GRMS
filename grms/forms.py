from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from django import forms

from . import models


class RoadSectionBasicForm(forms.ModelForm):
    """Initial step for creating a road section linked to a road."""

    section_sequence = forms.IntegerField(
        label="Section sequence", min_value=1, help_text="Ordered position along the road"
    )

    class Meta:
        model = models.RoadSection
        fields = (
            "road",
            "section_number",
            "section_sequence",
            "start_chainage_km",
            "end_chainage_km",
            "surface_type",
            "surface_thickness_cm",
        )
        widgets = {"road": forms.HiddenInput()}
        labels = {"surface_thickness_cm": "Thickness (cm)"}

    def __init__(self, *args: Any, road: Optional[models.Road] = None, **kwargs: Any):
        self.road = road
        super().__init__(*args, **kwargs)
        if self.road:
            self.fields["road"].initial = self.road.id
        # Align the displayed sequence with the underlying model field name.
        if self.instance and self.instance.pk:
            self.fields["section_sequence"].initial = self.instance.sequence_on_road

    def clean_surface_thickness_cm(self) -> Optional[Decimal]:
        value = self.cleaned_data.get("surface_thickness_cm")
        surface_type = self.cleaned_data.get("surface_type")
        requires_thickness = surface_type in {"Gravel", "DBST", "Asphalt", "Sealed"}
        if requires_thickness and value is None:
            raise forms.ValidationError("Thickness is required for gravel or paved surfaces.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_chainage_km")
        end = cleaned_data.get("end_chainage_km")
        if start is not None and end is not None:
            if start >= end:
                raise forms.ValidationError({"end_chainage_km": "End chainage must be greater than start chainage."})
            cleaned_data["length_km"] = (end - start).quantize(Decimal("0.001"))
        return cleaned_data

    def save(self, commit: bool = True):
        if self.road:
            self.instance.road = self.road
        self.instance.sequence_on_road = self.cleaned_data.get("section_sequence") or 1
        # Model.save will compute length_km and enforce uniqueness/overlaps.
        return super().save(commit=commit)
