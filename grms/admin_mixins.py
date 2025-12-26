from __future__ import annotations

from django.contrib import admin


class CascadeAutocompleteAdminMixin(admin.ModelAdmin):
    """
    Filters autocomplete querysets using parent IDs passed via query params.
    """

    cascade_autocomplete = {}

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        if request.path.endswith("/admin/autocomplete/"):
            field_name = request.GET.get("field_name")
            handler = self.cascade_autocomplete.get(field_name)
            if handler:
                try:
                    queryset = handler(queryset, request)
                except Exception:
                    queryset = queryset.none()

        return queryset, use_distinct


class RoadSectionCascadeAutocompleteMixin(admin.ModelAdmin):
    """
    Filters section autocomplete results to sections under the selected road.
    Requires the page JS to append ?road=<id> to the section autocomplete requests.
    """

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        if request.path.endswith("/admin/autocomplete/"):
            field_name = request.GET.get("field_name")
            if field_name == "section":
                road_id = request.GET.get("road")
                if road_id and str(road_id).isdigit():
                    queryset = queryset.filter(road_id=int(road_id))
                else:
                    queryset = queryset.none()

        return queryset, use_distinct
