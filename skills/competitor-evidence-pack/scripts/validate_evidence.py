#!/usr/bin/env python3
"""Validate an evidence register and summarize company/category coverage."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

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
VALID_STATUSES = {"success", "access_failed", "not_found"}
VALID_CONFIDENCE = {"high", "medium", "low", "n/a"}


def validate_evidence(input_path: Path) -> dict:
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing_headers = sorted(REQUIRED - headers)
        if missing_headers:
            raise ValueError(f"Missing required columns: {', '.join(missing_headers)}")
        rows = list(reader)

    errors: list[dict[str, object]] = []
    ids: set[str] = set()
    coverage: dict[str, Counter[str]] = defaultdict(Counter)
    status_counts: Counter[str] = Counter()

    if not rows:
        errors.append({"line": 1, "error": "empty_register"})

    for line, row in enumerate(rows, start=2):
        evidence_id = row["evidence_id"].strip()
        company = row["company"].strip()
        category = row["category"].strip()
        status = row["status"].strip().casefold()
        confidence = row["confidence"].strip().casefold()
        source_url = row["source_url"].strip()
        parsed = urlparse(source_url)
        collected_at = row["collected_at"].strip()

        if not evidence_id or evidence_id in ids:
            errors.append({"line": line, "error": "blank_or_duplicate_evidence_id", "value": evidence_id})
        ids.add(evidence_id)
        if not company or not category:
            errors.append({"line": line, "error": "company_and_category_required"})
        if status not in VALID_STATUSES:
            errors.append({"line": line, "error": "invalid_status", "value": status})
        if confidence not in VALID_CONFIDENCE:
            errors.append({"line": line, "error": "invalid_confidence", "value": confidence})
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append({"line": line, "error": "public_http_url_required"})
        try:
            parsed_time = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
            if parsed_time.tzinfo is None:
                raise ValueError
        except ValueError:
            errors.append({"line": line, "error": "collected_at_needs_timezone_iso8601"})
        if not row["observation"].strip():
            errors.append({"line": line, "error": "observation_required"})
        if status == "success" and confidence == "n/a":
            errors.append({"line": line, "error": "success_needs_confidence"})

        status_counts[status] += 1
        if company and category:
            coverage[company][category] += 1

    coverage_rows = [
        {"company": company, "categories": dict(sorted(categories.items())), "checks": sum(categories.values())}
        for company, categories in sorted(coverage.items())
    ]
    return {
        "source_register": input_path.name,
        "checks": len(rows),
        "companies": len(coverage),
        "status_counts": dict(sorted(status_counts.items())),
        "coverage": coverage_rows,
        "errors": errors,
        "delivery_ready": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_evidence(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["delivery_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
