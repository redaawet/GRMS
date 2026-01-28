# Generating import templates (CSV and XLSX)

Use this short guide when you need new import templates or want to re-export clean files for bulk loading.

## CSV templates (seed/import workflow)

The CSV templates are generated with the inventory export command and are compatible with `seed_from_inventory_csv`.
Run the management command and point it at an output directory:

```bash
python manage.py export_inventory_csv --path Datas
```

This creates the seed CSVs plus an `IMPORT_ORDER.txt` that lists a dependency-aware import order (e.g., Road → RoadSection → RoadSegment before dependent models). The traffic seed file (`traffic_seed.csv`) is generated from the **traffic app** models and contains both `TrafficSurveyOverall` and `TrafficSurveySummary` rows in a single file.

## XLSX templates (Excel-ready downloads)

XLSX files are produced from the admin reports and export actions. These are Excel-native downloads (no CSV parsing required) and are useful for sharing inventory snapshots or reports in a format that opens cleanly in Excel.

## CSV vs XLSX in this project

- **CSV** is the canonical format for bulk import/export with the seed/import commands. It is plain text and is best for automated workflows and scripted data validation.
- **XLSX** is Excel-native and is used for reports or ad-hoc exports. It preserves formatting but is not the primary format for bulk imports.
