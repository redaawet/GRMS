# Management command usage

Custom Django management commands available in this project. Run them from the repo root with:

`python manage.py <command> [args]`

Each command below includes a short usage line and an example.

The list below is prioritized by common workflows.

## 1) Data import + validation (start here)

- **validate_offline_excel `<path>`**
  - Usage: `python manage.py validate_offline_excel <path>`
  - Example: `python manage.py validate_offline_excel Datas/offline_data.xlsx`
- **import_offline_excel `<path>`** `[--strict]` `[--dry-run]`
  - Import a workbook (e.g., `Datas/offline_data.xlsx`) with sheets like `grms.Road`, `traffic.TrafficSurvey`, etc.
  - `--strict` stops at first error; `--dry-run` validates without saving.
  - Usage: `python manage.py import_offline_excel <path> [--strict] [--dry-run]`
  - Example: `python manage.py import_offline_excel Datas/offline_data.xlsx --strict`
- **export_data_collection_templates** `[--format csv|xlsx]` `[--output <dir>]` `[--models <app.Model> ...]`
  - Export blank data collection templates for offline entry.
  - Usage: `python manage.py export_data_collection_templates [--format csv|xlsx] [--output <dir>] [--models <app.Model> ...]`
  - Example: `python manage.py export_data_collection_templates --format xlsx --output Datas/templates`
- **export_inventory_csv**
  - Export inventory data to CSVs compatible with `seed_from_inventory_csv`.
  - Usage: `python manage.py export_inventory_csv`
  - Example: `python manage.py export_inventory_csv`
- **seed_from_inventory_csv**
  - Seed road inventory data from CSV extracts.
  - Usage: `python manage.py seed_from_inventory_csv`
  - Example: `python manage.py seed_from_inventory_csv`
- **import_inventory**
  - Import traffic, cross-section, and structure inventory data from canonical CSVs.
  - Usage: `python manage.py import_inventory`
  - Example: `python manage.py import_inventory`

## 2) Geometry + chainage normalization

- **normalize_sections** `[--apply]`
  - Normalize road section chainages, lengths, and geometries.
  - Dry-run by default; use `--apply` to persist changes.
  - Usage: `python manage.py normalize_sections [--apply]`
  - Example: `python manage.py normalize_sections --apply`
- **sync_geometry_and_mock_surveys** `[--inspection-date YYYY-MM-DD]`
  - Ensure road/section geometries exist and generate mock condition surveys.
  - Usage: `python manage.py sync_geometry_and_mock_surveys [--inspection-date YYYY-MM-DD]`
  - Example: `python manage.py sync_geometry_and_mock_surveys --inspection-date 2026-01-15`

## 3) Road condition + MCI

- **compute_mci `<year>`**
  - Compute or update `SegmentMCIResult` for all `RoadConditionSurvey` entries in the fiscal year.
  - Usage: `python manage.py compute_mci <year>`
  - Example: `python manage.py compute_mci 2026`
- **compute_mci_interventions**
  - Recompute MCI-based intervention recommendations for road segments.
  - Usage: `python manage.py compute_mci_interventions`
  - Example: `python manage.py compute_mci_interventions`

## 4) Traffic processing

- **recompute_traffic_summaries**
  - Recompute traffic cycle + survey summaries for `Approved` surveys.
  - Emits a warning if any road/year is missing cycles 1–3.
  - Usage: `python manage.py recompute_traffic_summaries`
  - Example: `python manage.py recompute_traffic_summaries`
- **compute_traffic_overall**
  - Aggregate summaries by road/year into `TrafficSurveyOverall` (ADT/PCU totals).
  - Usage: `python manage.py compute_traffic_overall`
  - Example: `python manage.py compute_traffic_overall`
- **refresh_road_traffic_summary**
  - Refresh the `vw_road_traffic_summary` materialized view via SQL.
  - Usage: `python manage.py refresh_road_traffic_summary`
  - Example: `python manage.py refresh_road_traffic_summary`

## 5) Prioritization + planning

- **compute_benefits `<fiscal_year>`**
  - Compute benefit factors and prioritization results for the fiscal year.
  - Usage: `python manage.py compute_benefits <fiscal_year>`
  - Example: `python manage.py compute_benefits 2026`
- **compute_road_ranking `<fiscal_year>`**
  - Compute SRAD road ranking results for the fiscal year.
  - Usage: `python manage.py compute_road_ranking <fiscal_year>`
  - Example: `python manage.py compute_road_ranking 2026`
- **compute_prioritization**
  - Placeholder scorer that prints latest MCI values for segments (first 100).
  - Usage: `python manage.py compute_prioritization`
  - Example: `python manage.py compute_prioritization`
- **compute_structure_interventions**
  - Recompute intervention recommendations for all structures.
  - Usage: `python manage.py compute_structure_interventions`
  - Example: `python manage.py compute_structure_interventions`

## 6) Data reset + maintenance

- **reset_domain_data `--yes-i-know`**
  - Delete domain data (roads, surveys, traffic, structures) while keeping lookup/auth tables.
  - Usage: `python manage.py reset_domain_data --yes-i-know`
  - Example: `python manage.py reset_domain_data --yes-i-know`
- **audit_helptext**
  - Validate help text registry entries against model fields.
  - Usage: `python manage.py audit_helptext`
  - Example: `python manage.py audit_helptext`

## 7) Traffic migration utilities

- **fix_migration_history** `[--database <alias>]`
  - Repair out-of-order traffic migrations and re-run `migrate`.
  - Usage: `python manage.py fix_migration_history [--database <alias>]`
  - Example: `python manage.py fix_migration_history --database default`
- **fix_traffic_overall_migration**
  - Fake the traffic overall migration and re-run `migrate`.
  - Usage: `python manage.py fix_traffic_overall_migration`
  - Example: `python manage.py fix_traffic_overall_migration`
