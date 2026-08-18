#!/usr/bin/env python3
"""Run all three ProofPack validators against bundled safe fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    with tempfile.TemporaryDirectory(prefix="proofpack-demo-") as directory:
        output_root = Path(directory)

        excel_dir = output_root / "excel"
        process = run(
            [
                sys.executable,
                "skills/excel-audit/scripts/audit_csv.py",
                "skills/excel-audit/assets/synthetic_customers.csv",
                "--key",
                "email",
                "--dedupe",
                "keep-first",
                "--output-dir",
                str(excel_dir),
            ]
        )
        try:
            summary = json.loads((excel_dir / "audit_summary.json").read_text(encoding="utf-8"))
            passed = process.returncode == 0 and summary["reconciliation_ok"]
            detail = f'{summary["input_rows"]} input -> {summary["output_rows"]} retained'
        except (OSError, KeyError, json.JSONDecodeError) as error:
            passed, detail = False, str(error)
        results.append(("excel-audit", passed, detail))

        pdf_output = output_root / "pdf-proof.json"
        process = run(
            [
                sys.executable,
                "skills/pdf-table-proof/scripts/build_proof_manifest.py",
                "skills/pdf-table-proof/assets/synthetic_extraction.csv",
                "--output",
                str(pdf_output),
            ]
        )
        try:
            summary = json.loads(pdf_output.read_text(encoding="utf-8"))
            passed = process.returncode == 0 and summary["proof_ready"]
            detail = f'{summary["rows"]} fields across {summary["source_pages"]} source pages'
        except (OSError, KeyError, json.JSONDecodeError) as error:
            passed, detail = False, str(error)
        results.append(("pdf-table-proof", passed, detail))

        evidence_output = output_root / "evidence-check.json"
        process = run(
            [
                sys.executable,
                "skills/competitor-evidence-pack/scripts/validate_evidence.py",
                "skills/competitor-evidence-pack/assets/public_demo_evidence.csv",
                "--output",
                str(evidence_output),
            ]
        )
        try:
            summary = json.loads(evidence_output.read_text(encoding="utf-8"))
            passed = process.returncode == 0 and summary["delivery_ready"]
            detail = f'{summary["checks"]} checks across {summary["companies"]} placeholder companies'
        except (OSError, KeyError, json.JSONDecodeError) as error:
            passed, detail = False, str(error)
        results.append(("competitor-evidence-pack", passed, detail))

    for name, passed, detail in results:
        print(f'[{"PASS" if passed else "FAIL"}] {name}: {detail}')

    passed_count = sum(passed for _, passed, _ in results)
    overall = passed_count == len(results)
    print(f'[{"PASS" if overall else "FAIL"}] ProofPack demo: {passed_count}/{len(results)} validators passed')
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
