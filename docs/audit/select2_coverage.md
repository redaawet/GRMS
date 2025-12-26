# Select2 coverage & large datasets

This audit lists foreign-key dropdowns treated as large tables and the strategy used
(to avoid preloading massive option lists).

| Field / model | Strategy | Notes |
| --- | --- | --- |
| `Road` | Autocomplete widgets | Used in `autocomplete_fields` (model FKs) and autocomplete widgets for filter-only road selectors. |
| `RoadSection` | Cascade select2 + filtered queryset | Section queryset is `none()` until road is selected; options loaded via `/admin/grms/options/sections/`. |
| `RoadSegment` | Cascade select2 + filtered queryset | Segment queryset is `none()` until section is selected; options loaded via `/admin/grms/options/segments/`. |
| `StructureInventory` | `autocomplete_fields` + cascade filters | Options filtered by road/section via `/admin/grms/options/structures/` for static selects and `get_search_results` for AJAX. |
| `FurnitureInventory` | Cascade select2 + autocomplete filters | Furniture selection is filtered by road/section via `/admin/grms/options/furniture/` for static selects and `get_search_results` for AJAX. |
