#!/usr/bin/env python3
"""Scan for duplicate grms_admin_site registrations without importing Django."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

DECORATOR_RE = re.compile(r"@admin\.register\((?P<model>[^,\)]+),\s*site=grms_admin_site\)")
REGISTER_RE = re.compile(r"grms_admin_site\.register\((?P<model>[^,\)]+)")


def iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        yield path


def main() -> int:
    occurrences: dict[str, list[str]] = defaultdict(list)
    for path in iter_python_files(ROOT):
        rel_path = path.relative_to(ROOT)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in DECORATOR_RE.finditer(text):
            model = match.group("model").strip()
            occurrences[model].append(f"{rel_path} (decorator)")
        for match in REGISTER_RE.finditer(text):
            model = match.group("model").strip()
            if model == "model":
                continue
            occurrences[model].append(f"{rel_path} (register)")

    duplicates = {model: refs for model, refs in occurrences.items() if len(refs) > 1}
    if not duplicates:
        print("No duplicate grms_admin_site registrations found.")
        return 0

    print("Duplicate grms_admin_site registrations detected:\n")
    for model, refs in sorted(duplicates.items()):
        print(f"- {model}")
        for ref in refs:
            print(f"  - {ref}")
        print("")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
