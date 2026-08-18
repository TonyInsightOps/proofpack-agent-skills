#!/usr/bin/env python3
"""Validate a page-linked PDF extraction register and write a proof manifest."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

REQUIRED = {
    "record_id",
    "source_file",
    "page",
    "field",
    "extracted_value",
    "qa_status",
    "exception_note",
}
VALID_STATUSES = {"pass", "review", "unreadable"}


def build_manifest(input_path: Path) -> dict:
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing_headers = sorted(REQUIRED - headers)
        if missing_headers:
            raise ValueError(f"Missing required columns: {', '.join(missing_headers)}")
        rows = list(reader)

    errors: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    seen: set[tuple[str, str, str]] = set()
    pages: set[tuple[str, int]] = set()

    if not rows:
        errors.append({"line": 1, "error": "empty_register"})

    for line, row in enumerate(rows, start=2):
        source_file = row["source_file"].strip()
        status = row["qa_status"].strip().casefold()
        status_counts[status] += 1
        if status not in VALID_STATUSES:
            errors.append({"line": line, "error": "invalid_status", "value": status})
        try:
            page = int(row["page"])
            if page < 1:
                raise ValueError
            if source_file:
                pages.add((source_file, page))
        except ValueError:
            errors.append({"line": line, "error": "page_must_be_positive_integer"})
        if not source_file:
            errors.append({"line": line, "error": "source_file_required"})
        record_id = row["record_id"].strip()
        field = row["field"].strip()
        key = (source_file, record_id, field)
        if not record_id or not field:
            errors.append({"line": line, "error": "blank_record_or_field"})
        elif key in seen:
            errors.append({"line": line, "error": "duplicate_record_field", "value": list(key)})
        seen.add(key)
        if status == "pass" and not row["extracted_value"].strip():
            errors.append({"line": line, "error": "pass_status_has_blank_value"})
        if status in {"review", "unreadable"} and not row["exception_note"].strip():
            errors.append({"line": line, "error": "exception_status_needs_note"})

    return {
        "source_register": input_path.name,
        "rows": len(rows),
        "files": len({row["source_file"].strip() for row in rows if row["source_file"].strip()}),
        "source_pages": len(pages),
        "records": len(
            {
                (row["source_file"].strip(), row["record_id"].strip())
                for row in rows
                if row["source_file"].strip() and row["record_id"].strip()
            }
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "errors": errors,
        "proof_ready": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0 if manifest["proof_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
