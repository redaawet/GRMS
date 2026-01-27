from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.importers.excel_utils import (
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
    "station_km",
    "start_chainage_km",
    "end_chainage_km",
    "structure_category",
    "structure_name",
    "easting_m",
    "northing_m",
    "comment",
]

NUMERIC_COLUMNS = {
    "section_number",
    "station_km",
    "start_chainage_km",
    "end_chainage_km",
    "easting_m",
    "northing_m",
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
        "stationkm": "station_km",
        "station": "station_km",
        "startchainagekm": "start_chainage_km",
        "endchainagekm": "end_chainage_km",
        "structurecategory": "structure_category",
        "category": "structure_category",
        "structuretype": "structure_category",
        "structurename": "structure_name",
        "name": "structure_name",
        "easting": "easting_m",
        "northing": "northing_m",
        "comment": "comment",
        "remarks": "comment",
    }
    return mappings.get(normalized)


def normalize_category(value: str) -> str:
    normalized = normalize_string(value).lower()
    if not normalized:
        return ""
    if "bridge" in normalized:
        return "Bridge"
    if "culvert" in normalized:
        return "Culvert"
    if "ford" in normalized:
        return "Ford"
    if "retaining" in normalized:
        return "Retaining Wall"
    if "gabion" in normalized:
        return "Gabion Wall"
    if "wall" in normalized:
        return "Retaining Wall"
    return "Other"


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
            else:
                row_data[canonical] = normalize_string(value)

        if row_data["structure_category"]:
            row_data["structure_category"] = normalize_category(row_data["structure_category"])

        has_identifier = bool(row_data["road_identifier"])
        has_names = bool(row_data["road_name_from"] and row_data["road_name_to"])
        if not (has_identifier or has_names):
            bad_rows.append({"row_number": row_number, "reason": "Missing road identifier or names."})
            continue
        if not row_data["structure_category"]:
            bad_rows.append({"row_number": row_number, "reason": "Missing structure category."})
            continue
        if not row_data["station_km"] and not (
            row_data["start_chainage_km"] and row_data["end_chainage_km"]
        ):
            bad_rows.append({"row_number": row_number, "reason": "Missing station or chainage values."})
            continue

        output_rows.append(row_data)

    write_csv(output_path, CANONICAL_COLUMNS, output_rows)
    write_bad_rows(bad_rows_path, bad_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert structures Excel sheet to canonical CSV.")
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
