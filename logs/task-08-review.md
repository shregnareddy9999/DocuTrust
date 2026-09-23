# Task 08 — Integrity checks and human review — Development Log

**Owner:** Task 08
**Branch:** current checkout (do not commit here unless the lead names `feature/task-08-review`)
**Started:** 2026-09-23
**Status:** Ready for review (do not mark the task complete in the tracker)

---

## Objective

Named reviewer can `ACCEPT`, `CORRECT`, or `UNRESOLVED` a verification. Corrections are additive.
Re-evaluation always goes through Task 07 `evaluate()`. The original OCR entries and original
verification rows are never overwritten.

## Contracts this task implements

- `docs/api.md` — `POST /verifications/{id}/review`, `GET /verifications/{id}` `review_actions`,
  `GET /documents/{id}/verifications`
- `docs/verification-rules.md` — human review; ACCEPT does not skip mismatch or missing required
- `docs/data-model.md` — `review_actions`; `supersedes_verification_id`; current = max `created_at`
- `docs/decisions.md` — D-11 free-text `reviewer_ref`; D-18 new verification row; D-23 current
- `AGENTS.md` Rule 9 — additive corrections
- `tasks/08-integrity-review.md`

## Decisions I made inside my own scope

| Date | Decision | Why | Reversible? |
|---|---|---|---|
| 2026-09-23 | Corrected fields stored as a **list of entries** per field name | Keeps original OCR object and corrected object side by side without inventing a nested `ocr`/`corrected` map not in GET extraction | Yes if Task 11 prefers another shape |
| 2026-09-23 | `review_repo.list_for_verification` stays newest-first; GET reverses to oldest-first | Task 02 test asserts DESC; `api.md` requires chronological GET | Yes |
| 2026-09-23 | Commit `review_actions` **before** `evaluate()`; second commit for extraction append + new verification | Re-eval failure must not erase the audit row; `get_db` does not auto-commit | No without losing Req 2 |
| 2026-09-23 | ACCEPT always re-runs `evaluate()` with `confidence_confirmed_fields` = schema `match_field` names, and always writes a new verification | Does not force `VERIFIED_MATCH`; skips only the low-confidence check | Yes if lead wants ACCEPT to skip a new row when nothing was LOW_CONFIDENCE |
| 2026-09-23 | UNRESOLVED: `new_verification_id` is JSON `null` | Matches existing manual check and `api.md` "no re-evaluation" | Documented for Task 11 |
| 2026-09-23 | `GET /documents/{id}/verifications` lives on the verifications router | Same router already owns `POST /documents/{id}/verify`; avoids Task 04 `documents.py` | Yes |

## Field-entry storage shape (Task 11)

After a `CORRECT` of `student_id`, `extraction_results.extracted_fields_json` looks like:

```json
{
  "student_id": [
    {"value": "DEMO-STU-OO1", "confidence": 0.69, "source": "ocr"},
    {"value": "DEMO-STU-001", "confidence": null, "source": "corrected"}
  ]
}
```

Uncorrected fields remain a single object `{value, confidence, source: "ocr"}`.
Effective values for `evaluate()`: latest `source: "corrected"` if present, else OCR `value`.
ACCEPT does not append entries and does not change stored confidence.

## Review workflow

1. Validate `reviewer_ref`, action, corrections (schema keys only).
2. Insert `review_actions` on the **reviewed** verification. `session.commit()`.
3. `UNRESOLVED` stops. Status unchanged. `new_verification_id` is `null`.
4. `ACCEPT` / `CORRECT`: build effective fields, `find_applicable_record` + `evaluate()`, insert a
   new `verification_results` row with `supersedes_verification_id`, second commit.
5. If step 4 raises: rollback the second unit of work only; review row remains; original
   verification and (for CORRECT) extraction JSON remain as they were at step 2.

A status is never assigned by the reviewer. `VERIFIED_MATCH` after review still means matched our
synthetic demo reference (reviewer-corrected), not issuer confirmation.

## API

- `POST /api/v1/verifications/{verification_id}/review` → `201 {review_action_id, new_verification_id, new_status}`
- `GET /api/v1/verifications/{verification_id}` → `review_actions` oldest → newest
- `GET /api/v1/documents/{document_id}/verifications` → newest first; exactly one `is_current`
- Unknown document → `404 DOCUMENT_NOT_FOUND`
- Unknown verification → `404 VERIFICATION_NOT_FOUND`

## Tests added or strengthened

- ACCEPT always creates a new row; missing required stays `REVIEW_REQUIRED`; mismatch stays `INTEGRITY_MISMATCH`
- ACCEPT confidence read back from DB (`student_id` OCR still `0.69` / `source: ocr`)
- GET document verification history, newest first, one current, 404
- GET review_actions oldest first
- CORRECT preserves OCR list entries; successive A → B → C
- UNRESOLVED: no new row, status unchanged, action persisted
- Re-evaluation failure: review survives; original verification unchanged; extraction unchanged
- Registry snapshot unchanged after ACCEPT / CORRECT / UNRESOLVED

## Tests (this session)

| Command | Last run | Result |
|---|---|---|
| `cd backend && .\venv\Scripts\python.exe -m pytest tests/test_review.py -q` | 2026-09-23 | **28 passed in 1.85s** |
| `cd backend && .\venv\Scripts\python.exe -m pytest -q --tb=short` | 2026-09-23 | **224 passed, 1 deselected in 8.92s** |

Exact focused output:

```
28 passed in 1.85s
```

Exact full-suite output:

```
224 passed, 1 deselected in 8.92s
```

## Manual verification already performed (not re-run in this session)

These were reported as already walked; this session did **not** repeat them against a live server:

1. Degraded academic certificate → `REVIEW_REQUIRED`
2. CORRECT `semester_or_year` → new verification, still `REVIEW_REQUIRED` because
   `certificate_or_marksheet_id` remained missing
3. CORRECT `certificate_or_marksheet_id` → new verification → `VERIFIED_MATCH`
4. Original OCR preserved (`source: ocr`, value null) plus corrected entries
   (`source: corrected`, confidence null) for those two fields
5. UNRESOLVED → review action created, `new_verification_id` null, status `REVIEW_REQUIRED`
6. ACCEPT → review action + new verification, status stayed `REVIEW_REQUIRED` because required
   fields were missing

No live PaddleOCR run was performed here (Python 3.14, no paddle wheel).

## Known limitations

- Tracker must not be marked complete by this session (`AGENTS.md`).
- No commit/push/PR.
- Task 10 still decides whether a corrected verification re-submits on-chain.
- Task 11 UI not touched.
- `review_repo.list_for_verification` remains newest-first for Task 02; only the GET handler sorts
  oldest-first.

## Handoff

- Files: `backend/app/services/review_service.py`, `backend/app/api/verifications.py`,
  `backend/tests/test_review.py`, `logs/task-08-review.md`
- Task 11: list-of-entries extraction shape; UNRESOLVED `new_verification_id` is `null`; ACCEPT
  `new_verification_id` is the **new** row, not the reviewed one
- Task 10: each CORRECT/ACCEPT produces a new verification id
