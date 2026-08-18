#!/usr/bin/env python3
"""Compare two prepared evidence registers and write a deterministic change ledger."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_evidence import validate_evidence

REQUIRED = {
    "evidence_id",
    "company",
    "category",
    "source_url",
    "collected_at",
    "status",
    "observation",
    "confidence",
}
IDENTITY_FIELDS = ("company", "category", "source_url")
COMPARE_FIELDS = ("status", "observation", "confidence")


def normalized(value: str) -> str:
    return " ".join(value.strip().split())


def load_register(path: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    validation = validate_evidence(path)
    if not validation["delivery_ready"]:
        errors = ", ".join(
            f'line {error["line"]}: {error["error"]}' for error in validation["errors"][:5]
        )
        raise ValueError(f"{path.name}: register validation failed ({errors})")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing_headers = sorted(REQUIRED - headers)
        if missing_headers:
            raise ValueError(f"{path.name}: missing required columns: {', '.join(missing_headers)}")
        rows = list(reader)

    if not rows:
        raise ValueError(f"{path.name}: evidence register is empty")

    indexed: dict[tuple[str, str, str], dict[str, str]] = {}
    for line, source_row in enumerate(rows, start=2):
        row = {name: normalized(source_row.get(name) or "") for name in REQUIRED}
        row["status"] = row["status"].casefold()
        row["confidence"] = row["confidence"].casefold()
        key = tuple(row[field] for field in IDENTITY_FIELDS)
        if not all(key):
            raise ValueError(f"{path.name}:{line}: company, category, and source_url are required")
        if key in indexed:
            raise ValueError(f"{path.name}:{line}: duplicate comparison identity {key!r}")
        indexed[key] = row
    return indexed


def fingerprint(row: dict[str, str]) -> str:
    payload = {field: row[field] for field in (*IDENTITY_FIELDS, *COMPARE_FIELDS)}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def compact(row: dict[str, str]) -> dict[str, str]:
    return {
        "evidence_id": row["evidence_id"],
        "collected_at": row["collected_at"],
        "status": row["status"],
        "observation": row["observation"],
        "confidence": row["confidence"],
        "fingerprint": fingerprint(row),
    }


def compare_evidence(baseline_path: Path, current_path: Path) -> dict[str, object]:
    baseline = load_register(baseline_path)
    current = load_register(current_path)
    counts: Counter[str] = Counter()
    changes: list[dict[str, object]] = []

    for key in sorted(set(baseline) | set(current)):
        before = baseline.get(key)
        after = current.get(key)
        if before is None:
            change_type = "added_check"
            changed_fields = list(COMPARE_FIELDS)
        elif after is None:
            change_type = "missing_from_current"
            changed_fields = list(COMPARE_FIELDS)
        else:
            changed_fields = [field for field in COMPARE_FIELDS if before[field] != after[field]]
            change_type = "changed" if changed_fields else "unchanged"

        counts[change_type] += 1
        changes.append(
            {
                "company": key[0],
                "category": key[1],
                "source_url": key[2],
                "change_type": change_type,
                "changed_fields": changed_fields,
                "baseline": compact(before) if before else None,
                "current": compact(after) if after else None,
            }
        )

    review_needed = sum(counts[name] for name in ("added_check", "changed", "missing_from_current"))
    return {
        "schema_version": 1,
        "baseline_register": baseline_path.name,
        "current_register": current_path.name,
        "identity_fields": list(IDENTITY_FIELDS),
        "compared_fields": list(COMPARE_FIELDS),
        "timestamp_policy": "collected_at is preserved for lineage but excluded from change classification",
        "counts": dict(sorted(counts.items())),
        "review_needed": review_needed,
        "changes": changes,
        "limitations": [
            "A changed row is a review signal, not proof of business significance.",
            "A missing current row is not proof that the underlying page or fact disappeared.",
            "The comparator does not fetch webpages or verify the truth of observations.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {args.baseline.resolve(), args.current.resolve()}:
        parser.error("output must not overwrite a source register")
    result = compare_evidence(args.baseline, args.current)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
