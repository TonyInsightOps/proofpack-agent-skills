from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ProofPackTests(unittest.TestCase):
    def test_excel_audit_reconciles_rows(self):
        module = load_module(
            "audit_csv",
            ROOT / "skills/excel-audit/scripts/audit_csv.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            result = module.audit_csv(
                ROOT / "skills/excel-audit/assets/synthetic_customers.csv",
                Path(directory),
                ["email"],
                "keep-first",
            )
            self.assertEqual(result["input_rows"], 5)
            self.assertEqual(result["output_rows"], 4)
            self.assertEqual(result["duplicate_groups"], 1)
            self.assertTrue(result["reconciliation_ok"])

    def test_excel_audit_does_not_overwrite_source(self):
        module = load_module(
            "audit_csv_overwrite",
            ROOT / "skills/excel-audit/scripts/audit_csv.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "cleaned.csv"
            source.write_text("id,email\n1,a@example.com\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                module.audit_csv(source, Path(directory), ["email"], "keep-first")

    def test_excel_audit_rejects_ragged_rows(self):
        module = load_module(
            "audit_csv_ragged",
            ROOT / "skills/excel-audit/scripts/audit_csv.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "ragged.csv"
            source.write_text("id,email\n1,a@example.com,unexpected\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "more fields"):
                module.audit_csv(source, Path(directory) / "output", ["email"])

    def test_pdf_manifest_is_proof_ready(self):
        module = load_module(
            "pdf_proof",
            ROOT / "skills/pdf-table-proof/scripts/build_proof_manifest.py",
        )
        result = module.build_manifest(
            ROOT / "skills/pdf-table-proof/assets/synthetic_extraction.csv"
        )
        self.assertTrue(result["proof_ready"])
        self.assertEqual(result["rows"], 6)

    def test_pdf_manifest_scopes_record_ids_to_source_file(self):
        module = load_module(
            "pdf_proof_multi_file",
            ROOT / "skills/pdf-table-proof/scripts/build_proof_manifest.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "register.csv"
            source.write_text(
                "record_id,source_file,page,field,extracted_value,qa_status,exception_note\n"
                "R001,one.pdf,1,total,10.00,pass,\n"
                "R001,two.pdf,1,total,20.00,pass,\n",
                encoding="utf-8",
            )
            result = module.build_manifest(source)
            self.assertTrue(result["proof_ready"])
            self.assertEqual(result["records"], 2)

    def test_pdf_manifest_rejects_blank_source_file(self):
        module = load_module(
            "pdf_proof_blank_source",
            ROOT / "skills/pdf-table-proof/scripts/build_proof_manifest.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "register.csv"
            source.write_text(
                "record_id,source_file,page,field,extracted_value,qa_status,exception_note\n"
                "R001,,1,total,10.00,pass,\n",
                encoding="utf-8",
            )
            result = module.build_manifest(source)
            self.assertFalse(result["proof_ready"])
            self.assertIn("source_file_required", {error["error"] for error in result["errors"]})

    def test_evidence_register_is_delivery_ready(self):
        module = load_module(
            "evidence",
            ROOT / "skills/competitor-evidence-pack/scripts/validate_evidence.py",
        )
        result = module.validate_evidence(
            ROOT / "skills/competitor-evidence-pack/assets/public_demo_evidence.csv"
        )
        self.assertTrue(result["delivery_ready"])
        self.assertEqual(result["companies"], 2)

    def test_evidence_register_rejects_untraceable_checks(self):
        module = load_module(
            "evidence_invalid",
            ROOT / "skills/competitor-evidence-pack/scripts/validate_evidence.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "evidence.csv"
            source.write_text(
                "evidence_id,company,category,source_url,collected_at,status,observation,confidence\n"
                "E001,ExampleCo,pricing,,2026-08-18T12:00:00,success,,n/a\n",
                encoding="utf-8",
            )
            result = module.validate_evidence(source)
            error_types = {error["error"] for error in result["errors"]}
            self.assertFalse(result["delivery_ready"])
            self.assertIn("public_http_url_required", error_types)
            self.assertIn("collected_at_needs_timezone_iso8601", error_types)
            self.assertIn("observation_required", error_types)
            self.assertIn("success_needs_confidence", error_types)

    def test_change_ledger_detects_deltas_without_timestamp_noise(self):
        module = load_module(
            "evidence_delta",
            ROOT / "skills/competitor-evidence-pack/scripts/compare_evidence.py",
        )
        result = module.compare_evidence(
            ROOT / "skills/competitor-evidence-pack/assets/public_demo_evidence.csv",
            ROOT / "skills/competitor-evidence-pack/assets/public_demo_evidence_current.csv",
        )
        self.assertEqual(
            result["counts"],
            {
                "added_check": 1,
                "changed": 2,
                "missing_from_current": 1,
                "unchanged": 1,
            },
        )
        self.assertEqual(result["review_needed"], 4)
        unchanged = next(change for change in result["changes"] if change["change_type"] == "unchanged")
        self.assertNotEqual(unchanged["baseline"]["collected_at"], unchanged["current"]["collected_at"])
        self.assertEqual(unchanged["baseline"]["fingerprint"], unchanged["current"]["fingerprint"])

    def test_change_ledger_rejects_duplicate_identities(self):
        module = load_module(
            "evidence_delta_duplicates",
            ROOT / "skills/competitor-evidence-pack/scripts/compare_evidence.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "evidence.csv"
            source.write_text(
                "evidence_id,company,category,source_url,collected_at,status,observation,confidence\n"
                "E001,ExampleCo,pricing,https://example.com/pricing,2026-08-18T12:00:00Z,success,One plan.,high\n"
                "E002,ExampleCo,pricing,https://example.com/pricing,2026-08-19T12:00:00Z,success,Two plans.,high\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate comparison identity"):
                module.compare_evidence(source, source)

    def test_delivery_manifest_detects_content_change(self):
        module = load_module(
            "delivery_integrity",
            ROOT / "scripts/delivery_integrity.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "cleaned.csv").write_text("id,value\n1,alpha\n", encoding="utf-8")
            (root / "exceptions.csv").write_text("row,issue\n", encoding="utf-8")
            manifest = module.build_manifest(root, ["exceptions.csv", "cleaned.csv"])
            manifest_path = root / "delivery-manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
            )

            initial = module.verify_manifest(root, manifest_path, strict_extras=True)
            self.assertTrue(initial["verified"])
            self.assertEqual(initial["counts"], {"verified": 2})

            (root / "cleaned.csv").write_text("id,value\n1,changed\n", encoding="utf-8")
            changed = module.verify_manifest(root, manifest_path, strict_extras=True)
            self.assertFalse(changed["verified"])
            changed_file = next(item for item in changed["files"] if item["path"] == "cleaned.csv")
            self.assertEqual(changed_file["status"], "changed")
            self.assertIn("hash_mismatch", changed_file["issues"])

    def test_delivery_manifest_rejects_unsafe_paths(self):
        module = load_module(
            "delivery_integrity_unsafe",
            ROOT / "scripts/delivery_integrity.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "unsafe manifest path"):
                module.build_manifest(root, ["../private.csv"])


if __name__ == "__main__":
    unittest.main()
