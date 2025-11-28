from __future__ import annotations

from django import forms

from .models import PcuLookup, VEHICLE_FIELD_MAP


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
