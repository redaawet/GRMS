# Inventory Import Pipeline (Excel → CSV → Django)

## 1) Excel → Canonical CSV

Three converters live in `tools/importers/` and output canonical CSVs plus a validation report (`bad_rows.csv`).

```bash
python tools/importers/convert_traffic_excel_to_csv.py <traffic.xlsx> <traffic.csv> --bad-rows <traffic_bad_rows.csv>
python tools/importers/convert_cross_section_excel_to_csv.py <cross_section.xlsx> <cross_section.csv> --bad-rows <cross_section_bad_rows.csv>
python tools/importers/convert_structures_excel_to_csv.py <structures.xlsx> <structures.csv> --bad-rows <structures_bad_rows.csv>
```

Each converter:
- Handles merged/multi-row headers.
- Normalizes strings and booleans (e.g., `√` → `True`).
- Emits a stable schema with canonical column names.

### Canonical schemas

**Traffic (`traffic.csv`)**
- `road_identifier` (optional if names provided)
- `road_name_from`
- `road_name_to`
- `fiscal_year` (optional; defaults to current year)
- `adt_total`
- `bus`
- `car`
- `heavy_goods`
- `light_goods`
- `medium_goods`
- `mini_bus`
- `motorcycle`
- `tractor`

**Cross-section (`cross_section.csv`)**
- `road_identifier` (optional if names provided)
- `road_name_from`
- `road_name_to`
- `section_number`
- `station_from_km`
- `station_to_km`
- `cross_section`
- `terrain_transverse`
- `terrain_longitudinal`
- `ditch_left_present`
- `ditch_right_present`
- `shoulder_left_present`
- `shoulder_right_present`
- `carriageway_width_m`
- `comment`

**Structures (`structures.csv`)**
- `road_identifier` (optional if names provided)
- `road_name_from`
- `road_name_to`
- `section_number` (optional)
- `station_km`
- `start_chainage_km`
- `end_chainage_km`
- `structure_category`
- `structure_name`
- `easting_m`
- `northing_m`
- `comment`

## 2) Import into Django

Run the management command with one or more CSVs. Each file is processed transactionally and uses bulk inserts/updates.

```bash
python manage.py import_inventory \
  --traffic <traffic.csv> \
  --cross_section <cross_section.csv> \
  --structures <structures.csv>
```

Road lookups prefer `road_identifier`. If missing, the importer resolves roads by a normalized `(road_name_from, road_name_to)` pair and persists that mapping in the road alias table to make future imports deterministic.
