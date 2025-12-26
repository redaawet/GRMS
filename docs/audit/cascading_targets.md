# Cascading hierarchy targets (GRMS)

Inventory of ModelAdmins/ModelForms containing FK fields named `road`, `section`, `segment`,
`road_section`, `road_segment`, `structure`, or `furniture`.

| Model | Admin/Form | Fields present | Widget mode |
| --- | --- | --- | --- |
| `RoadSection` | `RoadSectionAdmin` | `road` | `road` (autocomplete_fields) |
| `RoadSegment` | `RoadSegmentAdmin` | `section` | `section` (autocomplete_fields) |
| `StructureInventory` | `StructureInventoryAdmin` / `StructureInventoryAdminForm` | `road`, `section` | `road` + `section` (autocomplete_fields) |
| `BridgeDetail` | `BridgeDetailAdmin` / `StructureDetailFilterForm` | `road`, `section`, `structure` | `road` (static select2), `section` (static select2), `structure` (autocomplete_fields) |
| `CulvertDetail` | `CulvertDetailAdmin` / `StructureDetailFilterForm` | `road`, `section`, `structure` | `road` (static select2), `section` (static select2), `structure` (autocomplete_fields) |
| `FordDetail` | `FordDetailAdmin` / `StructureDetailFilterForm` | `road`, `section`, `structure` | `road` (static select2), `section` (static select2), `structure` (autocomplete_fields) |
| `RetainingWallDetail` | `RetainingWallDetailAdmin` / `StructureDetailFilterForm` | `road`, `section`, `structure` | `road` (static select2), `section` (static select2), `structure` (autocomplete_fields) |
| `GabionWallDetail` | `GabionWallDetailAdmin` / `StructureDetailFilterForm` | `road`, `section`, `structure` | `road` (static select2), `section` (static select2), `structure` (autocomplete_fields) |
| `FurnitureInventory` | `FurnitureInventoryAdmin` / `FurnitureInventoryForm` | `road` (filter), `section` | `road` (static select2), `section` (static select2) |
| `SegmentMCIResult` | `SegmentMCIResultAdmin` | `road_segment` | `road_segment` (static select2) |
| `SegmentInterventionRecommendation` | `SegmentInterventionRecommendationAdmin` | `segment` | `segment` (autocomplete_fields) |
| `StructureInterventionRecommendation` | `StructureInterventionRecommendationAdmin` | `structure` | `structure` (autocomplete_fields) |
| `RoadConditionSurvey` | `RoadConditionSurveyAdmin` / `RoadConditionSurveyForm` | `road`, `section`, `road_segment` | `road` (static select2), `section` (static select2), `road_segment` (autocomplete_fields) |
| `RoadConditionDetailedSurvey` | `RoadConditionDetailedSurveyAdmin` / `RoadConditionDetailedSurveyForm` | `road`, `section`, `road_segment` | `road` (static select2), `section` (static select2), `road_segment` (autocomplete_fields) |
| `StructureConditionSurvey` | `StructureConditionSurveyAdmin` / `StructureConditionSurveyForm` | `road_filter`, `section_filter`, `structure` | `road_filter` (static select2), `section_filter` (static select2), `structure` (autocomplete_fields) |
| `FurnitureConditionSurvey` | `FurnitureConditionSurveyAdmin` / `FurnitureConditionSurveyForm` | `road_filter`, `section_filter`, `furniture` | `road_filter` (static select2), `section_filter` (static select2), `furniture` (autocomplete_fields) |
| `StructureConditionDetailedSurvey` | `StructureConditionDetailedSurveyAdmin` | `structure` | `structure` (autocomplete_fields) |
| `FurnitureConditionDetailedSurvey` | `FurnitureConditionDetailedSurveyAdmin` | `furniture` | `furniture` (autocomplete_fields) |
| `RoadSocioEconomic` | `RoadSocioEconomicAdmin` | `road` | `road` (autocomplete_fields) |
| `AnnualWorkPlan` | `AnnualWorkPlanAdmin` | `road` | `road` (autocomplete_fields) |
| `TrafficSurvey` | `TrafficSurveyAdmin` / `TrafficSurveyAdminForm` | `road` | `road` (autocomplete_fields) |
