# Cascading FK targets in GRMS admin

Inventory of ModelAdmin definitions with hierarchical foreign keys.

| ModelAdmin class | Model name | Fields present | Uses `autocomplete_fields` |
| --- | --- | --- | --- |
| `RoadSegmentAdmin` | `RoadSegment` | `road`, `section` | Yes (`section`) |
| `StructureInventoryAdmin` | `StructureInventory` | `road`, `section` | Yes (`road`, `section`) |
| `BridgeDetailAdmin` | `BridgeDetail` | `road`, `section`, `structure` | Yes (`structure`) |
| `CulvertDetailAdmin` | `CulvertDetail` | `road`, `section`, `structure` | Yes (`structure`) |
| `FordDetailAdmin` | `FordDetail` | `road`, `section`, `structure` | Yes (`structure`) |
| `RetainingWallDetailAdmin` | `RetainingWallDetail` | `road`, `section`, `structure` | Yes (`structure`) |
| `GabionWallDetailAdmin` | `GabionWallDetail` | `road`, `section`, `structure` | Yes (`structure`) |
| `RoadConditionSurveyAdmin` | `RoadConditionSurvey` | `road`, `section`, `road_segment` | Yes (`road_segment`) |
| `RoadConditionDetailedSurveyAdmin` | `RoadConditionDetailedSurvey` | `road`, `section`, `road_segment` | Yes (`road_segment`) |
