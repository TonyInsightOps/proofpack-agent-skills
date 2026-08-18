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

## Responsible reports

For vulnerabilities in these scripts, open a private security advisory rather
than posting exploitable details in a public issue.
