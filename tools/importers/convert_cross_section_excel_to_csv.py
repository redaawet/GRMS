from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.importers.excel_utils import (
    normalize_bool,
    normalize_header,
    normalize_string,
    parse_decimal,
    parse_excel,
    write_bad_rows,
    write_csv,
)


CANONICAL_COLUMNS = [
    "road_identifier",
    "road_name_from",
    "road_name_to",
    "section_number",
    "station_from_km",
    "station_to_km",
    "cross_section",
    "terrain_transverse",
    "terrain_longitudinal",
    "ditch_left_present",
    "ditch_right_present",
    "shoulder_left_present",
    "shoulder_right_present",
    "carriageway_width_m",
    "comment",
]

NUMERIC_COLUMNS = {"section_number", "station_from_km", "station_to_km", "carriageway_width_m"}
BOOL_COLUMNS = {
    "ditch_left_present",
    "ditch_right_present",
    "shoulder_left_present",
    "shoulder_right_present",
}


def resolve_column(normalized: str) -> str | None:
    if not normalized:
        return None

    mappings = {
        "roadidentifier": "road_identifier",
        "roadid": "road_identifier",
        "roadno": "road_identifier",
        "roadnamefrom": "road_name_from",
        "from": "road_name_from",
        "roadnameto": "road_name_to",
        "to": "road_name_to",
        "sectionnumber": "section_number",
        "sectionno": "section_number",
        "section": "section_number",
        "stationfromkm": "station_from_km",
        "stationtokm": "station_to_km",
        "chainagefrom": "station_from_km",
        "chainageto": "station_to_km",
        "crosssection": "cross_section",
        "crosssectiontype": "cross_section",
        "terraintransverse": "terrain_transverse",
        "terrainlongitudinal": "terrain_longitudinal",
        "leftditch": "ditch_left_present",
        "rightditch": "ditch_right_present",
        "leftshoulder": "shoulder_left_present",
        "rightshoulder": "shoulder_right_present",
        "carriagewaywidthm": "carriageway_width_m",
        "comment": "comment",
        "remarks": "comment",
    }
    return mappings.get(normalized)


def convert(excel_path: Path, output_path: Path, bad_rows_path: Path) -> None:
    parsed = parse_excel(excel_path, max_header_rows=3, resolver=resolve_column)

    header_map: dict[int, str | None] = {}
    for idx, header in enumerate(parsed.headers):
        header_map[idx] = resolve_column(normalize_header(header))

    output_rows: list[dict[str, str]] = []
    bad_rows: list[dict[str, str]] = []

    for row_number, values in parsed.rows:
        row_data = {column: "" for column in CANONICAL_COLUMNS}
        for idx, value in enumerate(values):
            canonical = header_map.get(idx)
            if not canonical:
                continue
            if canonical in NUMERIC_COLUMNS:
                row_data[canonical] = parse_decimal(value)
            elif canonical in BOOL_COLUMNS:
                row_data[canonical] = "True" if normalize_bool(value) else "False"
            else:
                row_data[canonical] = normalize_string(value)

        has_identifier = bool(row_data["road_identifier"])
        has_names = bool(row_data["road_name_from"] and row_data["road_name_to"])
        if not (has_identifier or has_names):
            bad_rows.append({"row_number": row_number, "reason": "Missing road identifier or names."})
            continue
        if not row_data["section_number"]:
            bad_rows.append({"row_number": row_number, "reason": "Missing section number."})
            continue
        if not row_data["station_from_km"] or not row_data["station_to_km"]:
            bad_rows.append({"row_number": row_number, "reason": "Missing station chainage values."})
            continue
        if not row_data["cross_section"]:
            bad_rows.append({"row_number": row_number, "reason": "Missing cross-section."})
            continue
        if not row_data["terrain_transverse"] or not row_data["terrain_longitudinal"]:
            bad_rows.append({"row_number": row_number, "reason": "Missing terrain values."})
            continue

        output_rows.append(row_data)

    write_csv(output_path, CANONICAL_COLUMNS, output_rows)
    write_bad_rows(bad_rows_path, bad_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert cross-section Excel sheet to canonical CSV.")
    parser.add_argument("excel", type=Path, help="Path to source Excel file")
    parser.add_argument("output", type=Path, help="Path to output CSV file")
    parser.add_argument(
        "--bad-rows",
        dest="bad_rows",
        type=Path,
        default=Path("bad_rows.csv"),
        help="Path for validation report CSV",
    )
    args = parser.parse_args()

    convert(args.excel, args.output, args.bad_rows)


if __name__ == "__main__":
    main()
