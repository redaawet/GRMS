from __future__ import annotations

from django import forms

from .helptexts import HELP_TEXTS


class CascadeFKModelFormMixin:
    def init_queryset_none(self, field_name: str) -> None:
        field = self.fields.get(field_name)
        if field is None or not hasattr(field, "queryset"):
            return
        field.queryset = field.queryset.none()

    def filter_queryset(self, field_name: str, qs) -> None:
        field = self.fields.get(field_name)
        if field is None or not hasattr(field, "queryset"):
            return
        field.queryset = qs

    def read_parent_id(self, field_name: str):
        if self.is_bound:
            value = self.data.get(field_name)
            if value:
                return value
        initial = self.initial.get(field_name) if hasattr(self, "initial") else None
        if initial:
            return getattr(initial, "id", initial)
        instance = getattr(self, "instance", None)
        if instance and hasattr(instance, f"{field_name}_id"):
            return getattr(instance, f"{field_name}_id")
        return None


class HelpTextInjectingModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model = getattr(self._meta, "model", None)
        if not model:
            return
        key = f"{model._meta.app_label}.{model.__name__}"
        hints = HELP_TEXTS.get(key, {})
        if not hints:
            return
        for name, payload in hints.items():
            field = self.fields.get(name)
            if not field:
                continue
            help_text = payload.get("help_text") if isinstance(payload, dict) else payload
            if help_text:
                field.help_text = help_text
