from __future__ import annotations

from django import forms

from grms.utils import make_point, point_to_lat_lng, utm_to_wgs84, wgs84_to_utm

from .models import PcuLookup, TrafficSurvey, VEHICLE_FIELD_MAP


class PcuBulkAddForm(forms.ModelForm):
    cars = forms.DecimalField(max_digits=6, decimal_places=3, required=False)
    light_goods = forms.DecimalField(max_digits=6, decimal_places=3, required=False)
    minibuses = forms.DecimalField(max_digits=6, decimal_places=3, required=False)
    medium_goods = forms.DecimalField(max_digits=6, decimal_places=3, required=False)
    heavy_goods = forms.DecimalField(max_digits=6, decimal_places=3, required=False)
    buses = forms.DecimalField(max_digits=6, decimal_places=3, required=False)
    tractors = forms.DecimalField(max_digits=6, decimal_places=3, required=False)
    motorcycles = forms.DecimalField(max_digits=6, decimal_places=3, required=False)
    bicycles = forms.DecimalField(max_digits=6, decimal_places=3, required=False)
    pedestrians = forms.DecimalField(max_digits=6, decimal_places=3, required=False)

    class Meta:
        model = PcuLookup
        fields = ["effective_date", "expiry_date", "region", "notes"]

    def clean(self):
        cleaned = super().clean()
        if not any(cleaned.get(field) is not None for field in VEHICLE_FIELD_MAP.values()):
            raise forms.ValidationError("Enter at least one PCU factor before saving.")
        return cleaned


class TrafficSurveyAdminForm(forms.ModelForm):
    station_easting = forms.DecimalField(
        label="Station easting",
        required=False,
        max_digits=12,
        decimal_places=2,
        help_text="UTM Zone 37N easting for the counting station.",
    )
    station_northing = forms.DecimalField(
        label="Station northing",
        required=False,
        max_digits=12,
        decimal_places=2,
        help_text="UTM Zone 37N northing for the counting station.",
    )

    class Meta:
        model = TrafficSurvey
        fields = "__all__"
        widgets = {"station_location": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        point = point_to_lat_lng(getattr(self.instance, "station_location", None))
        if point:
            try:
                easting, northing = wgs84_to_utm(point["lat"], point["lng"], zone=37)
            except ImportError:
                easting = northing = None
            self.fields["station_easting"].initial = easting
            self.fields["station_northing"].initial = northing

    def clean(self):
        cleaned = super().clean()
        easting = cleaned.get("station_easting")
        northing = cleaned.get("station_northing")

        if easting is None and northing is None:
            cleaned["station_location"] = None
            return cleaned

        if easting is None or northing is None:
            missing = "northing" if easting is not None else "easting"
            raise forms.ValidationError({
                f"station_{missing}": "Provide both easting and northing to set the station location.",
            })

        try:
            lat, lng = utm_to_wgs84(float(easting), float(northing), zone=37)
        except ImportError as exc:
            raise forms.ValidationError(str(exc))

        cleaned["station_location"] = make_point(lat, lng)
        return cleaned
