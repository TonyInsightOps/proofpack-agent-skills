---
name: excel-audit
description: Audit and clean CSV or Excel-style tabular data when the result must include duplicate handling, exception records, and before/after reconciliation rather than an unexplained edited file.
---

# Excel Audit

Produce a reviewable dataset and an audit trail. Never silently guess a business
rule or overwrite the only source copy.

## Required outcome

1. Preserve an untouched source copy.
2. Confirm the row grain and the fields that define a duplicate.
3. Profile missing values, exact duplicates, format inconsistencies, and parsing
   failures before editing.
4. Apply only deterministic rules that are supplied or clearly safe. Flag fuzzy
   matches and ambiguous values for review.
5. Reconcile input rows to retained, merged, rejected, and unresolved rows.
6. Deliver the cleaned table, an exception log, a change summary, and the rules
   used.

For ordinary CSV files, run `scripts/audit_csv.py` to create a deterministic
baseline. For XLSX files, apply the same controls with an appropriate
spreadsheet workflow and retain sheet-level lineage.

## Boundaries

- Do not infer missing identities, amounts, dates, or categories.
- Do not merge fuzzy matches without an explicit rule or reviewer decision.
- Do not upload private data or publish customer records.
- Do not claim accuracy beyond the checks actually performed.
