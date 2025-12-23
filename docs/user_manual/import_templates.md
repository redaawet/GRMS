# Import templates

Use these notes when preparing Excel templates for bulk imports. Always run a **Dry-run** first; fix errors, then re-import the same file.

## Road inventory template (Road → Section → Segment)
- **Required columns**
  - `road_identifier` (`RTR-###`), `road_name_from`, `road_name_to`, `design_standard` (Basic Access/DC1–DC8), `surface_type` (Earth/Gravel/Paved), `managing_authority` (Federal/Regional/Wereda/Community), `admin_zone`, `total_length_km`.
  - Optional geometry: `start_easting`, `start_northing`, `end_easting`, `end_northing` or `geometry_wkt`.
- **Sections**: `road_identifier`, `start_chainage_km`, `end_chainage_km`, `surface_type` (Earth/Gravel/DBST/Asphalt/Sealed), optional `section_name`, `surface_thickness_cm`.
- **Segments**: `road_identifier`, `section_number`, `station_from_km`, `station_to_km`, `cross_section` (Cutting/Embankment/Cut/Embankment/Flat), `terrain_transverse`, `terrain_longitudinal`, drainage/shoulder flags (`ditch_left_present`, `ditch_right_present`, `shoulder_left_present`, `shoulder_right_present`), `carriageway_width_m`.
- **Allowed values**: match the choice fields in the admin forms; text must be case-sensitive to the choices above.
- **Common errors**: chainage gaps/overlaps, end < start, section length exceeding road length, missing geometry when slicing sections.
- **Re-import**: Fix chainage or choice values in Excel, re-run dry-run, then import.

## Road condition survey template
- **Required columns**: `road_identifier`, `section_number`, `segment_sequence`, `inspection_date`, `inspected_by`.
- **Condition fields**: `drainage_left/right`, `shoulder_left/right`, `surface_condition` (must match lookup values), `gravel_thickness_mm`, `is_there_bottleneck`, `bottleneck_size_m`, `comments`.
- **Allowed values**: Lookups must match existing `ConditionFactorLookup` labels; booleans use `TRUE/FALSE` or `1/0`.
- **Common errors**: referencing a segment without shoulders/drainage, bottleneck size provided while `is_there_bottleneck` is false, invalid lookup labels.
- **Re-import**: Correct lookup names or FK references, dry-run again, then import to create/update surveys.

## Traffic survey template (header)
- **Required columns**: `road_identifier`, `survey_year`, `cycle_number`, `count_start_date`, `count_end_date`, `count_hours_per_day`, `method`, `observer`, `station_lat`, `station_lng`.
- **Allowed values**: `method` free text; `count_hours_per_day` numeric; coordinates must be WGS84 decimal degrees.
- **Common errors**: duplicate cycle for the same year/road, missing coordinates, date range shorter/longer than `count_days_per_cycle`.
- **Re-import**: Update the header row, keep the same `traffic_survey_id` if present to update instead of create.

## Traffic count records template (daily counts)
- **Required columns**: `traffic_survey_id` (or `road_identifier` + `survey_year` + `cycle_number`), `count_date`, `time_block_from`, `time_block_to`, vehicle counts (`cars`, `light_goods`, `minibuses`, `medium_goods`, `heavy_goods`, `buses`, `tractors`, `motorcycles`, `bicycles`, `pedestrians`), `is_market_day`.
- **Allowed values**: counts must be integers ≥ 0; dates must fall within the survey’s `count_start_date`–`count_end_date` window.
- **Common errors**: FK mismatch to `traffic_survey` (causes SQLite/Postgres FK failures), count dates outside the survey window, negative numbers, missing required count columns.
- **Dry-run & error log**: Dry-run surfaces FK or validation errors; download the error log, correct the rows, and re-import the exact file.
- **Re-import workflow**: After fixing errors, re-run dry-run → if clean, run final import. Re-importing the same `traffic_survey_id` updates existing rows instead of duplicating them.
