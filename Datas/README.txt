GRMS Excel Extraction (generated in ChatGPT sandbox)

FILES
- roads_seed.csv
  One row per road name. Uses road_name_norm as a stable key.
  length_km_preferred = cross-section length if present, else traffic length.

- road_sections_seed.csv
  3 default sections per road (chainage split into 3 equal parts).

- road_segments_seed.csv
  Segments created from the Cross Section Inventory; split automatically across the 3 sections.
  station_from_km / station_to_km are RELATIVE to the section start chainage.

- structures_seed.csv
  Bridge/Culvert/Other/Quarry structures parsed from Structure Inventory.
  station_km_in_section is RELATIVE to the section start chainage.

- traffic_seed.csv
  Road-level traffic (Starting-Ending). Includes ADT and per-vehicle-type 5-day averages where available.

- road_socioeconomic_seed.csv
  Default RoadSocioEconomic rows (placeholders).

NEXT STEP
Use these CSVs as inputs to a Django management command:
- create/get Road by road_name_norm (or road_identifier)
- create 3 RoadSection records per road using road_sections_seed.csv
- create RoadSegment from road_segments_seed.csv (attach to correct section)
- create Structure records from structures_seed.csv
- create TrafficCount/AADT records from traffic_seed.csv
- create RoadSocioEconomic defaults from road_socioeconomic_seed.csv
How to seed the data

Make sure the seed files exist in the folder you’ll point to (default expects: roads_seed.csv, road_sections_seed.csv, road_segments_seed.csv, structures_seed.csv, traffic_seed.csv, road_socioeconomic_seed.csv).

From the project root, run the importer (use a full path if your Datas folder lives elsewhere):
python manage.py seed_from_inventory_csv --path Datas

Optional flags:

--dry-run to validate without saving changes.

--wipe-road-data to clear segments/structures/traffic for roads in the CSVs before importing.
These are supported by the command flags.