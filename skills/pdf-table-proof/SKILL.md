---
name: pdf-table-proof
description: Verify PDF-to-table extraction when every output row needs source-file and page lineage, exception handling, and completeness checks. Do not use for merely summarizing a PDF.
---

# PDF Table Proof

Treat extraction and verification as separate stages. The goal is not only a
spreadsheet; it is a spreadsheet a reviewer can trace back to the source.

## Required outcome

1. Record source filename, one-based page number, record identifier, field name,
   extracted value, and QA status for every row or field group.
2. Preserve raw text for ambiguous values instead of normalizing by guess.
3. Check missing pages, duplicate record identifiers, type errors, and totals
   that can be reconciled safely.
4. Separate extraction failures from source-document ambiguity.
5. Deliver the table, proof manifest, exception list, and limitations.

Run `scripts/build_proof_manifest.py` on the extraction register to verify the
minimum lineage contract. It validates evidence structure; it does not prove
that OCR or transcription is correct, so visually inspect material exceptions.

## Boundaries

- Never invent unreadable text.
- Do not remove page references from the final deliverable.
- Do not execute embedded files, macros, or links from untrusted PDFs.
- Keep regulated, identity, and customer documents private.
