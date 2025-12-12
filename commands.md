# Management command usage

Custom Django management commands available in this project. Run them from the repo root with `python manage.py <command>`.

## GRMS app

- **compute_mci `<year>`**
  - Computes or updates `SegmentMCIResult` records for all `RoadConditionSurvey` entries in the given fiscal year. Fails fast if a survey cannot be processed.
- **compute_mci_interventions**
  - Recomputes MCI-based intervention recommendations for all road segments and reports how many recommendations were created.
- **compute_benefits `<fiscal_year>`**
  - Calculates benefit factors and prioritization results for the provided fiscal year. Emits an error if the calculation raises an exception.
- **compute_prioritization**
  - Placeholder scorer that prints the latest MCI value for each segment (up to the first 100 segments).

## Traffic app

- **compute_traffic_overall**
  - Aggregates traffic survey summaries by road and fiscal year to update `TrafficSurveyOverall` with ADT/PCU totals and average confidence scores.
- **recompute_traffic_summaries**
  - For every traffic survey whose QA status is `Approved`, recomputes its cycle and survey summaries.
- **refresh_road_traffic_summary**
  - Refreshes the `vw_road_traffic_summary` materialized view directly via SQL.
- **fix_migration_history** `[--database <alias>]`
  - Repairs out-of-order traffic migrations by marking `0004_road_level_traffic_overall` as applied when needed, then runs `migrate` for the chosen database (default `default`).
- **fix_traffic_overall_migration**
  - Fakes the `0004_create_traffic_survey_overall_clean` migration for the `traffic` app and then runs `migrate` to synchronize the rest.
