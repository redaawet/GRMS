from __future__ import annotations

from django.contrib import admin

from .admin_forms import HelpTextInjectingModelForm
from .admin_utils import valid_autocomplete_fields


class GRMSBaseAdmin(admin.ModelAdmin):
    def get_form(self, request, obj=None, change=False, **kwargs):
        form_class = super().get_form(request, obj=obj, change=change, **kwargs)
        if issubclass(form_class, HelpTextInjectingModelForm):
            return form_class

        class HelpTextForm(HelpTextInjectingModelForm, form_class):
            pass

        HelpTextForm.__name__ = f"{form_class.__name__}HelpText"
        return HelpTextForm

    def get_autocomplete_fields(self, request):
        fields = super().get_autocomplete_fields(request)
        return valid_autocomplete_fields(self.model, fields)
