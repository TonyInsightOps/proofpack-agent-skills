#!/usr/bin/env python3
"""Create a cleaned CSV, exception log, and reconciliation summary."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def normalized(value: str) -> str:
    return " ".join(value.strip().split())


def audit_csv(
    input_path: Path,
    output_dir: Path,
    keys: list[str],
    dedupe: str = "none",
) -> dict:
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Input CSV must have a header row")
        fieldnames = [normalized(name) for name in reader.fieldnames]
        if any(not name for name in fieldnames):
            raise ValueError("Header names must not be blank")
        if len(set(fieldnames)) != len(fieldnames):
            raise ValueError("Header names are duplicated after whitespace normalization")
        rows = []
        for source_line, source_row in enumerate(reader, start=2):
            if None in source_row:
                raise ValueError(f"Row {source_line} has more fields than the header")
            rows.append({normalized(k): normalized(v or "") for k, v in source_row.items()})

    keys = [normalized(key) for key in keys]
    if any(not key for key in keys):
        raise ValueError("Duplicate-key column names must not be blank")
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate-key columns must not be repeated")
    unknown_keys = [key for key in keys if key not in fieldnames]
    if unknown_keys:
        raise ValueError(f"Unknown key columns: {', '.join(unknown_keys)}")

    missing = Counter()
    exceptions: list[dict[str, str]] = []
    groups: dict[tuple[str, ...], list[int]] = defaultdict(list)

    for index, row in enumerate(rows, start=2):
        for column in fieldnames:
            if row[column] == "":
                missing[column] += 1
                exceptions.append(
                    {
                        "source_row": str(index),
                        "issue_type": "missing_value",
                        "column": column,
                        "value": "",
                        "detail": "Value is blank; no value was inferred.",
                    }
                )
        if keys:
            key = tuple(row[column].casefold() for column in keys)
            if all(key):
                groups[key].append(index)

    duplicate_groups = {key: indexes for key, indexes in groups.items() if len(indexes) > 1}
    duplicate_rows = {index for indexes in duplicate_groups.values() for index in indexes[1:]}
    for key, indexes in duplicate_groups.items():
        for index in indexes:
            exceptions.append(
                {
                    "source_row": str(index),
                    "issue_type": "duplicate_key",
                    "column": ",".join(keys),
                    "value": " | ".join(key),
                    "detail": f"Candidate duplicate group spans source rows {indexes}.",
                }
            )

    if dedupe == "keep-first":
        output_rows = [row for row_index, row in enumerate(rows, start=2) if row_index not in duplicate_rows]
    else:
        output_rows = rows

    cleaned_path = output_dir / "cleaned.csv"
    exceptions_path = output_dir / "exceptions.csv"
    summary_path = output_dir / "audit_summary.json"
    source_path = input_path.resolve()
    if any(path.resolve() == source_path for path in (cleaned_path, exceptions_path, summary_path)):
        raise ValueError("Output directory would overwrite the source file")

    output_dir.mkdir(parents=True, exist_ok=True)
    with cleaned_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    exception_fields = ["source_row", "issue_type", "column", "value", "detail"]
    with exceptions_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=exception_fields)
        writer.writeheader()
        writer.writerows(exceptions)

    summary = {
        "source_file": input_path.name,
        "key_columns": keys,
        "dedupe_rule": dedupe,
        "input_rows": len(rows),
        "output_rows": len(output_rows),
        "removed_rows": len(rows) - len(output_rows),
        "reconciliation_ok": len(rows) == len(output_rows) + (len(rows) - len(output_rows)),
        "duplicate_groups": len(duplicate_groups),
        "missing_values_by_column": dict(sorted(missing.items())),
        "exceptions": len(exceptions),
        "outputs": {"cleaned": cleaned_path.name, "exceptions": exceptions_path.name},
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--key", action="append", default=[], help="Duplicate-key column; repeat for composite keys")
    parser.add_argument("--dedupe", choices=["none", "keep-first"], default="none")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = audit_csv(args.input, args.output_dir, args.key, args.dedupe)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
