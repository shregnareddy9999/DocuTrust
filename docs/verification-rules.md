# Verification Rules and Human Review

Implemented in `backend/app/domain/normalization.py`, `matching.py`, `rules.py`, `status.py`. Pure
functions — no DB/HTTP/OCR imports (`architecture.md`). This module never determines legal
authenticity; it only ever reports "does this match the configured synthetic record, and does it
pass documented deterministic checks."

## Normalization (`normalization.py`)

Applied identically to extracted values and registry values before comparison:

- Text fields: trim leading/trailing whitespace, collapse internal repeated whitespace, case-fold
  for comparison only (the *stored* value keeps original casing).
- Date fields: must already be `YYYY-MM-DD` (`document-processing.md`); any other format is left as
  extracted and excluded from date comparisons, with `warnings: ["unrecognized_date_format:<field>"]`.
- No normalization step ever strips or replaces characters in a way that changes an identifier's
  meaning (e.g., never strip letters from an alphanumeric ID). Both the original and normalized
  value are retained for audit display.

## Matching (`matching.py`)

For a document's category:
1. Look up `registry_records` where `category` matches and `active = true`.
2. A candidate record matches if **all** `match_field: true` fields (per `category-schemas.md`)
   are non-null on the extracted side and equal (post-normalization) to the candidate.
3. If exactly one candidate record satisfies step 2 → that's the matched record.
4. If zero candidates satisfy step 2 but a record shares the document's identifying key field (e.g.,
   `student_id`, `id_number`, `demo_pan_code`, `certificate_number`) → treat that record as the
   "applicable reference" for mismatch reporting (its non-matching fields are reported individually)
   rather than reporting a blanket "no record."
5. If no record shares even an identifying key field → `NO_TRUSTED_RECORD`.
6. More than one record satisfies step 2 (should not happen with clean fixtures) → treated as a data
   error in the registry fixtures, reported as `PROCESSING_FAILED` with a specific reason — this
   points at a seeding bug, not a document problem.

## Rule engine (`rules.py`) — initial deterministic baseline

| Rule ID | Checks |
|---|---|
| `required_field_presence` | Every `required: true` field (per category) has a non-null extracted value |
| `field_match` | Every `match_field: true` field equals the applicable registry record's value (post-normalization) |
| `category_schema_validity` | Extracted values conform to the field's declared `type`/format (e.g., `demo_pan_code` is 6 chars) |
| `date_consistency` | Where a category declares related date fields, they are logically consistent (none implemented as required for MVP categories today — placeholder for extension; do not invent a check not listed in `category-schemas.md`) |
| `known_fixture_duplicate` | The extracted identifying key exactly matches a **different** registry record's key with mismatching other fields — flagged distinctly as "possible fixture confusion," not fraud |

No rule may produce a numeric score, weighted probability, or "AI fraud score" — every rule is a
boolean pass/fail with a fixed, human-readable reason string.

## Status vocabulary (`status.py`) — locked

| Status | Meaning | UI wording |
|---|---|---|
| `PENDING` | Verification not yet run/complete | "Processing…" |
| `VERIFIED_MATCH` | All required+match fields match an active synthetic registry record | "Matched our synthetic demo reference" — never "authentic" or "verified by government" |
| `REVIEW_REQUIRED` | Missing required field, low-confidence field, or ambiguous extraction, before a conclusive comparison can be made | "Needs human review" |
| `NO_TRUSTED_RECORD` | No registry record shares even the identifying key | "No matching reference found in the demo registry — not evidence of a fake document" |
| `INTEGRITY_MISMATCH` | An applicable reference exists but one or more `field_match` fields disagree | "Mismatch found" + exact field(s) |
| `PROCESSING_FAILED` | A technical failure prevented verification (OCR failure, registry data error) | "Could not complete verification — technical error" |

## Status precedence (resolves the "ambiguity" left open in the earlier draft)

Evaluated in this exact order; the first matching condition wins:

1. OCR/extraction itself failed → `PROCESSING_FAILED`.
2. Any `required_field_presence` failure, OR any extracted `match_field` value has OCR confidence
   below `LOW_CONFIDENCE_THRESHOLD` (default `0.70`, see `configuration.md`) → `REVIEW_REQUIRED`.
3. No applicable registry record for the category+identifying key → `NO_TRUSTED_RECORD`.
4. An applicable record exists and any `field_match` comparison fails → `INTEGRITY_MISMATCH`.
5. An applicable record exists and all `field_match` comparisons pass → `VERIFIED_MATCH`.

A reviewer's `CORRECT` action re-runs this exact precedence against the corrected values as a new
verification row (`data-model.md`) — the precedence logic itself is never bypassed for a reviewed
document.

## Human review (`review_service.py`)

- Actions: `ACCEPT` (keep current extracted values, mark reviewed, does not by itself change status
  unless it resolves a low-confidence flag), `CORRECT` (supply new field values, triggers re-
  evaluation), `UNRESOLVED` (record that a human looked and could not resolve it — status stays
  `REVIEW_REQUIRED`, but the review is visible in history).
- The original OCR-extracted value is never overwritten; a correction is stored as an additional
  field entry (`source: "corrected"`) and referenced by the new verification row.
- A review action never claims external issuer confirmation — the UI text for a post-review
  `VERIFIED_MATCH` still says "matched our synthetic demo reference (reviewer-corrected)."

## Explicit non-goals

- This module never computes an "authenticity likelihood," never runs image forensics, and never
  auto-labels anything "forged." See `problem-statement-mapping.md` for why, and for the honest
  framing to use when explaining this design choice.
