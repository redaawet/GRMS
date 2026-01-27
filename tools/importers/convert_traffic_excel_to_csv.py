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
    "fiscal_year",
    "adt_total",
    "bus",
    "car",
    "heavy_goods",
    "light_goods",
    "medium_goods",
    "mini_bus",
    "motorcycle",
    "tractor",
]

NUMERIC_COLUMNS = {
    "fiscal_year",
    "adt_total",
    "bus",
    "car",
    "heavy_goods",
    "light_goods",
    "medium_goods",
    "mini_bus",
    "motorcycle",
    "tractor",
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
        "origin": "road_name_from",
        "roadnameto": "road_name_to",
        "to": "road_name_to",
        "destination": "road_name_to",
        "fiscalyear": "fiscal_year",
        "year": "fiscal_year",
        "adt": "adt_total",
        "adttotal": "adt_total",
        "averagedailytraffic": "adt_total",
    }
    if normalized in mappings:
        return mappings[normalized]

    vehicle_map = {
        "bus": "bus",
        "buses": "bus",
        "car": "car",
        "cars": "car",
        "heavygoods": "heavy_goods",
        "heavygoodsvehicle": "heavy_goods",
        "lightgoods": "light_goods",
        "mediumgoods": "medium_goods",
        "minibus": "mini_bus",
        "minibuses": "mini_bus",
        "motorcycle": "motorcycle",
        "motorcycleavg": "motorcycle",
        "tractor": "tractor",
        "tractors": "tractor",
    }
    for key, value in vehicle_map.items():
        if key in normalized:
            return value
    return None


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

        has_identifier = bool(row_data["road_identifier"])
        has_names = bool(row_data["road_name_from"] and row_data["road_name_to"])
        if not (has_identifier or has_names):
            bad_rows.append({"row_number": row_number, "reason": "Missing road identifier or names."})
            continue

        if not row_data["adt_total"]:
            bad_rows.append({"row_number": row_number, "reason": "Missing ADT total."})
            continue

        output_rows.append(row_data)

    write_csv(output_path, CANONICAL_COLUMNS, output_rows)
    write_bad_rows(bad_rows_path, bad_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert traffic Excel sheet to canonical CSV.")
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
