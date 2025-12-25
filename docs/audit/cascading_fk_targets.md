# Cascading FK targets in GRMS admin

Inventory of ModelAdmin definitions with hierarchical foreign keys.

| ModelAdmin class | Model name | Fields present | Uses `autocomplete_fields` |
| --- | --- | --- | --- |
| `AnnualWorkPlanAdmin` | `AnnualWorkPlan` | `road` | Yes (`road`) |
| `RoadSectionAdmin` | `RoadSection` | `road` | Yes (`road`, `admin_zone_override`, `admin_woreda_override`) |
| `RoadSegmentAdmin` | `RoadSegment` | `road`, `section` | Yes (`section`) |
| `StructureInventoryAdmin` | `StructureInventory` | `road`, `section` | Yes (`road`, `section`) |
| `BridgeDetailAdmin` | `BridgeDetail` | `road`, `section`, `structure` | Yes (`structure`) |
| `CulvertDetailAdmin` | `CulvertDetail` | `road`, `section`, `structure` | Yes (`structure`) |
| `FordDetailAdmin` | `FordDetail` | `road`, `section`, `structure` | Yes (`structure`) |
| `RetainingWallDetailAdmin` | `RetainingWallDetail` | `road`, `section`, `structure` | Yes (`structure`) |
| `GabionWallDetailAdmin` | `GabionWallDetail` | `road`, `section`, `structure` | Yes (`structure`) |
| `FurnitureInventoryAdmin` | `FurnitureInventory` | `section` | No |
| `SegmentMCIResultAdmin` | `SegmentMCIResult` | `road_segment` | No |
| `SegmentInterventionRecommendationAdmin` | `SegmentInterventionRecommendation` | `segment` | Yes (`segment`) |
| `RoadConditionSurveyAdmin` | `RoadConditionSurvey` | `road`, `section`, `road_segment` | Yes (`road_segment`) |
| `RoadConditionDetailedSurveyAdmin` | `RoadConditionDetailedSurvey` | `road`, `section`, `road_segment` | Yes (`road_segment`) |
| `RoadSocioEconomicAdmin` | `RoadSocioEconomic` | `road` | Yes (`road`, `road_link_type`) |
| `BenefitFactorAdmin` | `BenefitFactor` | `road` | No |
| `RoadRankingResultAdmin` | `RoadRankingResult` | `road` | No |
| `TrafficSurveyAdmin` | `TrafficSurvey` | `road` | Yes (`road`) |
