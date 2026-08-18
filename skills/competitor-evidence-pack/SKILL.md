---
name: competitor-evidence-pack
description: Build a source-linked competitive-intelligence pack from approved public webpages when facts, observations, inferences, and access failures must remain clearly separated.
---

# Competitor Evidence Pack

Collect only the approved public evidence needed for the decision. Deliver a
compact evidence register and a brief that distinguishes observation from
interpretation.

## Required outcome

1. Confirm the target companies, approved source categories, collection date,
   and comparison window.
2. For every check, record a unique evidence ID, company, category, source URL,
   collection time, status, observed fact, and confidence.
3. Preserve access failures. A blocked or missing page is not evidence that the
   underlying event did not happen.
4. Label every analytical statement as fact, inference, or recommendation.
5. Report coverage by company and category before writing the executive brief.

Run `scripts/validate_evidence.py` on the evidence register before delivery.

## Boundaries

- Public sources only; no login bypass, CAPTCHA bypass, private-person research,
  cold outreach, or automated posting.
- Respect website terms, robots directives, and reasonable request rates.
- Do not turn weak evidence into financial, legal, or investment advice.
- Do not expose confidential client context in filenames, examples, or commits.
