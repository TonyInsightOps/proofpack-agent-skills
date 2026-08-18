# Security and privacy

ProofPack is designed for local processing, but repository history is public
when a repository is public. Prevention matters more than deletion.

## Never commit

- passwords, API keys, tokens, cookies, or session exports;
- passports, national IDs, bank or card records;
- home addresses, private phone numbers, or personal contact lists;
- customer files without written permission;
- confidential contracts, chat exports, pricing, payment paths, or signatures;
- production databases or unredacted screenshots.

Use a new staging folder, synthetic fixtures, and an explicit file allowlist.
Review `git diff --cached` before every public push. If a credential is exposed,
revoke or rotate it immediately; removing a file from a later commit is not
enough.

Delivery manifests contain filenames and content hashes. Hashes do not
anonymize sensitive material, and a manifest is not a digital signature. Use
sanitized relative filenames, keep private manifests in the approved delivery
channel, and never publish a customer manifest as proof of authenticity.

## Responsible reports

For vulnerabilities in these scripts, open a private security advisory rather
than posting exploitable details in a public issue.
