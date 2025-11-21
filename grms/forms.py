from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from django import forms

from . import models
from .utils import make_point, point_to_lat_lng


class RoadBasicForm(forms.ModelForm):
    """First step of the road wizard – capture basic attributes."""

    class Meta:
        model = models.Road
        fields = (
            "road_name_from",
            "road_name_to",
            "admin_zone",
            "admin_woreda",
            "managing_authority",
            "design_standard",
            "population_served",
            "year_of_update",
            "last_mci_update",
            "surface_type",
            "total_length_km",
            "remarks",
        )
        labels = {"total_length_km": "Total length (km)"}
        widgets = {
            "year_of_update": forms.DateInput(attrs={"type": "date"}),
            "last_mci_update": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_total_length_km(self) -> Optional[Decimal]:
        total_length = self.cleaned_data.get("total_length_km")
        if total_length is not None and total_length <= 0:
            raise forms.ValidationError("Total length must be greater than zero.")
        return total_length


class RoadAlignmentForm(forms.ModelForm):
    """Second step of the road wizard – capture alignment coordinates."""

    start_latitude = forms.FloatField(required=False)
    start_longitude = forms.FloatField(required=False)
    end_latitude = forms.FloatField(required=False)
    end_longitude = forms.FloatField(required=False)

    class Meta:
        model = models.Road
        fields = (
            "start_easting",
            "start_northing",
            "end_easting",
            "end_northing",
        )
        widgets = {
            "start_easting": forms.NumberInput(attrs={"step": "0.01"}),
            "start_northing": forms.NumberInput(attrs={"step": "0.01"}),
            "end_easting": forms.NumberInput(attrs={"step": "0.01"}),
            "end_northing": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        instance = self.instance
        if instance and instance.pk:
            start = point_to_lat_lng(getattr(instance, "road_start_coordinates", None))
            end = point_to_lat_lng(getattr(instance, "road_end_coordinates", None))
            if start:
                self.fields["start_latitude"].initial = start["lat"]
                self.fields["start_longitude"].initial = start["lng"]
            if end:
                self.fields["end_latitude"].initial = end["lat"]
                self.fields["end_longitude"].initial = end["lng"]

    def _validate_coordinate_pair(
        self, lat: Optional[float], lng: Optional[float], easting: Optional[Decimal], northing: Optional[Decimal], prefix: str
    ) -> None:
        latlng_complete = lat is not None and lng is not None
        utm_complete = easting is not None and northing is not None
        if lat is not None and lng is None:
            raise forms.ValidationError({f"{prefix}_longitude": "Longitude is required when latitude is provided."})
        if lng is not None and lat is None:
            raise forms.ValidationError({f"{prefix}_latitude": "Latitude is required when longitude is provided."})
        if easting is not None and northing is None:
            raise forms.ValidationError({f"{prefix}_northing": "Northing is required when easting is provided."})
        if northing is not None and easting is None:
            raise forms.ValidationError({f"{prefix}_easting": "Easting is required when northing is provided."})
        if not (latlng_complete or utm_complete):
            raise forms.ValidationError({f"{prefix}_easting": "Provide UTM or latitude/longitude for the start and end points."})

    def clean(self):
        cleaned_data = super().clean()
        self._validate_coordinate_pair(
            cleaned_data.get("start_latitude"),
            cleaned_data.get("start_longitude"),
            cleaned_data.get("start_easting"),
            cleaned_data.get("start_northing"),
            "start",
        )
        self._validate_coordinate_pair(
            cleaned_data.get("end_latitude"),
            cleaned_data.get("end_longitude"),
            cleaned_data.get("end_easting"),
            cleaned_data.get("end_northing"),
            "end",
        )
        return cleaned_data

    def save(self, commit: bool = True):
        self.instance.start_easting = self.cleaned_data.get("start_easting")
        self.instance.start_northing = self.cleaned_data.get("start_northing")
        self.instance.end_easting = self.cleaned_data.get("end_easting")
        self.instance.end_northing = self.cleaned_data.get("end_northing")

        start_lat = self.cleaned_data.get("start_latitude")
        start_lng = self.cleaned_data.get("start_longitude")
        end_lat = self.cleaned_data.get("end_latitude")
        end_lng = self.cleaned_data.get("end_longitude")

        if start_lat is not None and start_lng is not None:
            self.instance.road_start_coordinates = make_point(start_lat, start_lng)
        if end_lat is not None and end_lng is not None:
            self.instance.road_end_coordinates = make_point(end_lat, end_lng)

        return super().save(commit=commit)


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
