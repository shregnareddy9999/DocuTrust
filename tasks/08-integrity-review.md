# PS21 Task Specification

> **This file is a work order for the assigned developer and their AI coding agent.**
>
> Do not expand the scope without explicit approval from the project lead.

---

## Task Information

**Task:** `Integrity checks and human review`
**Task ID:** `08` (`docs/implementation-plan.md` step 8)
**Assigned To:** `Unassigned` (suggested: Member B)
**Branch:** `feature/task-08-review`
**Priority:** `High` — the demo's most persuasive scenario depends on it
**Status:** `Not Started`

---

# 1. Goal

## Objective

Implement `review_service.py` and `POST /verifications/{id}/review` per `docs/api.md` and
`docs/verification-rules.md`: a named reviewer can `ACCEPT`, `CORRECT`, or mark `UNRESOLVED`, and a
correction re-runs the **same** rule evaluation against corrected values, producing a **new**
verification row while preserving everything that came before.

Expected outcome: correcting an OCR misread turns `REVIEW_REQUIRED` into `VERIFIED_MATCH`, the
original OCR value remains visible, the original verification row is untouched, and the whole chain
is auditable.

## Why This Exists

Step 8 of `docs/implementation-plan.md`. OCR will misread characters — `DEMO-STU-OO1` for
`DEMO-STU-001` is the canonical case. A system that guessed would be dangerous. A system that
refused to conclude and escalated to a human is correct, and the review path is what makes that
refusal useful rather than a dead end.

This is also the scenario that wins the room. Most demos show a happy path. Showing an OCR error,
correcting it, and then demonstrating that *both* the original reading and the correction are
permanently recorded is what separates an audit trail from a database
(`docs/judging-and-pitch.md` §3).

The discipline that makes it work: **corrections are additive, never destructive**
(`AGENTS.md` Rule 9). An audit trail that can be edited is not an audit trail.

---

# 2. Authoritative Documentation

* `AGENTS.md` — Rules 2, 9
* `docs/verification-rules.md` §"Human review" — **authoritative**
* `docs/api.md` — `POST /verifications/{id}/review` request and response
* `docs/data-model.md` — `review_actions`; the note that a `CORRECT` never overwrites original OCR
* `docs/decisions.md` — D-11 (no auth; free-text `reviewer_ref`), D-18 (corrections create new rows)
* `docs/workflow.md` Stage 6
* `docs/security-privacy.md` — reviewer identity is unauthenticated in MVP, and that is documented
* `logs/task-07-rules.md` — the `evaluate()` signature

---

# 3. Scope

## In Scope

* `backend/app/services/review_service.py` — apply a review action, write `review_actions`, and for
  `CORRECT`, merge corrections and re-evaluate.
* `POST /verifications/{verification_id}/review` in `backend/app/api/verifications.py`.
* Review history exposed on `GET /verifications/{id}` (or a sibling field per `docs/api.md`).
* `backend/tests/test_review.py`.

## Out of Scope

* Authentication or reviewer accounts — **explicitly out of MVP scope** (`docs/decisions.md` D-11).
  `reviewer_ref` is free text. Do not build a login.
* Changing rule logic — **Task 07** owns it. This task calls `evaluate()`; it never reimplements or
  bypasses it.
* Editing registry records — a reviewer must not be able to alter the reference data
  (`docs/workflow.md` Stage 6).
* Blockchain re-submission on a corrected verification — **Task 10** decides that wiring.
* The review UI — **Task 11**.
* Bulk review or a reviewer queue — not in MVP scope.

---

# 4. Allowed Files / Areas

```text
backend/app/services/review_service.py
backend/app/api/verifications.py        (add the review endpoint only)
backend/tests/test_review.py            (new)
```

### May Modify If Required

```text
backend/app/repositories/review_repo.py   (query helpers if Task 02 left a gap)
```

---

# 5. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Task 07 (`evaluate()`, `verification_service`) | **Hard** | Re-evaluation goes through the same function |
| Task 02 (`review_repo`, `verification_repo`) | **Hard** | Persistence |
| Task 06 (`extracted_fields` shape) | **Hard** | Corrections merge into it |

### Dependency Status

* [x] Dependencies exist once Task 07 merges
* [x] Requires coordination: Task 10 decides whether a corrected verification re-submits on-chain;
      Task 11 builds the UI against this endpoint

### Parallel-development notes

Same owner as Task 07, so the `evaluate()` signature is already known. The service can be written
immediately after Task 07's domain layer stabilises, before Task 07's endpoints are finished.

---

# 6. Contracts That Must Be Preserved

### Additive history (`AGENTS.md` Rule 9, `docs/decisions.md` D-18)

* A `CORRECT` **adds** a field entry with `source: "corrected"`. The original `source: "ocr"` entry
  is preserved and remains retrievable. This is what lets the UI show original and corrected side by
  side (`docs/workflow.md` Stage 6).
* A `CORRECT` writes a **new** `verification_results` row with
  `supersedes_verification_id` set to the reviewed verification's ID. The previous row keeps its
  original status, comparisons, and reason codes, permanently (`docs/decisions.md` D-23).
* The `review_actions` row attaches to the verification that was **reviewed**, not to the one the
  correction produced. The history therefore reads: verification A (`REVIEW_REQUIRED`) → review
  action on A → verification B (`VERIFIED_MATCH`, superseding A).
* After a correction, "current" is B purely because it has the greatest `created_at`. Nothing is
  flagged, mutated, or deleted to make that true, and no module computes it independently
  (`docs/data-model.md` §"Which verification is current").
* `review_actions` rows are never updated or deleted.
* If you find yourself writing an `UPDATE` against `extraction_results.extracted_fields_json` that
  replaces an OCR value, stop — that is the exact failure this rule exists to prevent.

### The same rules, always

Re-evaluation calls Task 07's `evaluate()` with identical logic and the identical precedence order.
A reviewed document gets a status because the rules produced it — **never because a reviewer chose
it, and never because the code took a shortcut for reviewed items.**

### Action semantics (`docs/verification-rules.md`)

| Action | Behaviour |
|---|---|
| `ACCEPT` | Keep current values, record that a human reviewed. Does not by itself change status **unless** it resolves a low-confidence flag — see Requirement 3 |
| `CORRECT` | Requires `corrections`; merges them, re-evaluates, writes a new verification row |
| `UNRESOLVED` | A human looked and could not resolve it. Status stays `REVIEW_REQUIRED`; the review is visible in history |

### API (`docs/api.md`)

* Request: `{reviewer_ref, action, corrections?, comment?}`.
* `corrections` required only when `action = CORRECT`.
* Response `201 {review_action_id, new_verification_id, new_status}`.
* For `ACCEPT` and `UNRESOLVED` where no re-evaluation occurred, `new_verification_id` may reference
  the existing verification — be consistent and document which you chose in the log.
* Errors: `400 INVALID_ACTION`, `404 VERIFICATION_NOT_FOUND`, `422 MISSING_CORRECTIONS`.

### Honest wording (`AGENTS.md` Rule 2)

A post-review `VERIFIED_MATCH` is still "matched our synthetic demo reference (reviewer-corrected)".
Human review is **not** issuer confirmation, and no response text, log line, or reason code may
suggest otherwise.

### Reviewer scope

A reviewer may correct extracted values. A reviewer may **not** edit registry records, delete
history, alter a blockchain record, or set a status directly.

---

# 7. Implementation Requirements

### Requirement 1 — Validate the action

Action must be one of the three, or `400 INVALID_ACTION`. `CORRECT` without `corrections`, or with an
empty object, is `422 MISSING_CORRECTIONS`. Every correction key must be a field in that category's
schema — an unknown field name is `422`, because accepting it would put data in the record that no
rule will ever read.

### Requirement 2 — Record the review action first

Write the `review_actions` row before any re-evaluation. If re-evaluation then fails, the fact that a
human reviewed is still recorded — losing that would be losing audit data to a technical error.

### Requirement 3 — `ACCEPT` and the low-confidence flag

`ACCEPT` means a human looked at the values and confirms they are right as read. That resolves the
*uncertainty*, so re-evaluation for an `ACCEPT` treats the reviewed match fields as confidence-
confirmed and skips precedence step 2's confidence check for them — while **every other check still
runs unchanged**. A `VERIFIED_MATCH` after `ACCEPT` still had to pass the actual field comparison.

Implement this explicitly, not by mutating stored confidence values. Pass a flag into re-evaluation.
Overwriting a stored confidence with `1.0` would destroy the record of what OCR actually reported,
which the audit trail needs.

Missing required fields are **not** resolved by `ACCEPT` — a missing field is missing regardless of
who looked at it. `ACCEPT` on a document with a missing required field leaves it `REVIEW_REQUIRED`.

### Requirement 4 — `CORRECT`

1. Load the current extraction's `extracted_fields`.
2. For each correction, **add** an entry with `source: "corrected"`, `confidence: null`, preserving
   the original `"ocr"` entry.
3. Build the effective field set: corrected value where present, otherwise OCR value.
4. Call `evaluate()` with the effective set, treating corrected fields as confidence-confirmed.
5. Write a new `verification_results` row with `supersedes_verification_id` set to the reviewed
   verification's ID.
6. Return the new ID and status.

The storage shape for holding both entries is an implementation choice — for example, keying by
field with `{"ocr": {...}, "corrected": {...}}`, or a list of entries per field. Pick one, keep it
consistent with `docs/api.md`'s response shape, and **publish it in the log**, because Task 11
renders both values side by side.

### Requirement 5 — `UNRESOLVED`

Record the action and comment. No re-evaluation. Status unchanged. The point is that the attempt is
visible in history.

### Requirement 6 — Review history

`GET /verifications/{id}` exposes the review actions for that verification in chronological order,
each with `reviewer_ref`, `action`, `corrections`, `comment`, `created_at`.

### Error Handling

| Situation | Response |
|---|---|
| Unknown verification ID | `404 VERIFICATION_NOT_FOUND` |
| Action not one of the three | `400 INVALID_ACTION` |
| `CORRECT` with no corrections | `422 MISSING_CORRECTIONS` |
| Correction naming a field not in the schema | `422` with the offending name |
| Empty `reviewer_ref` | `422` — the audit trail needs an attributed reviewer, even unauthenticated |
| Re-evaluation raises | `500 INTERNAL_ERROR`; the `review_actions` row still persists |

---

# 8. Testing Requirements

## Automated Tests

`backend/tests/test_review.py`:

**Actions**
* `ACCEPT` → `review_actions` row created, `action = ACCEPT`, `reviewer_ref` stored.
* `CORRECT` with a valid correction → new `verification_results` row, new status returned.
* `UNRESOLVED` → row created, status unchanged, no new verification row.

**The central scenario**
* Start from `REVIEW_REQUIRED` caused by a low-confidence `student_id` misread as `DEMO-STU-OO1`.
  Correct it to `DEMO-STU-001`. Assert **all** of:
  * the new verification status is `VERIFIED_MATCH`
  * a new `verification_results` row exists
  * **the original row still exists, still `REVIEW_REQUIRED`, with its original comparisons**
  * the original OCR value `DEMO-STU-OO1` is still retrievable with `source: "ocr"`
  * the corrected value is present with `source: "corrected"`
  * the new row's `supersedes_verification_id` equals the original verification's ID
  * `verification_repo.get_latest_for_document()` now returns the new row, and `GET
    /documents/{id}/verifications` lists both with `is_current` true on exactly one

That single test encodes the entire audit guarantee.

**Non-destruction**
* After a correction, the original `extraction_results` row's OCR values are unchanged.
* After two successive corrections, all three verification rows exist in order.
* No service function updates a `verification_results.status` in place.

**`ACCEPT` semantics**
* `ACCEPT` on a low-confidence but correctly-matching document → `VERIFIED_MATCH`.
* `ACCEPT` on a document with a **missing required field** → still `REVIEW_REQUIRED`.
* `ACCEPT` on a document with a genuine field mismatch → `INTEGRITY_MISMATCH`, **not**
  `VERIFIED_MATCH`. Accepting the reading does not accept the disagreement.
* Stored confidence values are unchanged after `ACCEPT` — assert directly.

**Validation**
* Unknown verification → `404`.
* Invalid action → `400`.
* `CORRECT` without corrections → `422`.
* Correction naming `not_a_field` → `422`.
* Empty `reviewer_ref` → `422`.

**Scope**
* No review path can modify a `registry_records` row — assert the registry is unchanged after a
  correction.

Run:

```bash
cd backend && pytest tests/test_review.py
```

## Manual Verification

1. Upload `academic_certificate_degraded.png` → verify → `REVIEW_REQUIRED`.
2. `GET /verifications/{id}` → note which field is low-confidence.
3. `POST .../review` with `action: CORRECT` and the right value.
4. Confirm the response gives a new verification ID and `VERIFIED_MATCH`.
5. `GET` the **original** verification ID → still `REVIEW_REQUIRED`, unchanged.
6. `GET /documents/{id}/extraction` → both the OCR value and the corrected value are visible.
7. Confirm the registry is untouched.

---

# 9. Acceptance Criteria

* [ ] All three actions implemented with the documented semantics.
* [ ] `CORRECT` creates a new verification row with `supersedes_verification_id` set; the previous row is untouched.
* [ ] The review action attaches to the reviewed verification, not the one it produced.
* [ ] The original OCR value is preserved and retrievable alongside the correction.
* [ ] Re-evaluation goes through Task 07's `evaluate()` — no reimplementation, no bypass.
* [ ] A status is never hand-assigned by a reviewer.
* [ ] `ACCEPT` resolves confidence uncertainty **without** mutating stored confidence values.
* [ ] `ACCEPT` does not resolve a missing required field or a genuine mismatch.
* [ ] `review_actions` is written before re-evaluation and survives a re-evaluation failure.
* [ ] Corrections are validated against the category schema.
* [ ] Empty `reviewer_ref` rejected.
* [ ] No review path modifies a registry record.
* [ ] Review history exposed chronologically.
* [ ] Post-review wording still says "matched our synthetic demo reference (reviewer-corrected)".
* [ ] All tests pass, including the full central scenario.
* [ ] `git diff` reviewed; development log updated; branch pushed; PR prepared.

---

# 10. Known Risks

* **Overwriting instead of adding.** The natural implementation — set the corrected value on the
  field — destroys the audit trail. It is also nearly invisible in review, because the endpoint
  behaves correctly from the outside. The test that asserts the original OCR value is still
  retrievable is what catches it.
* **Updating the existing verification row.** Same failure, different table. A new row, every time.
* **Mutating confidence on `ACCEPT`.** Tempting and wrong; it erases what OCR actually reported.
  Pass a flag instead.
* **`ACCEPT` over-resolving.** Accepting a reading is not accepting a mismatch or conjuring a missing
  field. Three separate tests exist for this.
* **Drifting into a reviewer auth system.** Out of scope (`docs/decisions.md` D-11). Free-text
  `reviewer_ref`, documented as not production-acceptable, and that is the whole design.
* **Reimplementing precedence "just for the reviewed case".** Call `evaluate()`.

---

# 11. Open Questions

* **`new_verification_id` for `ACCEPT`/`UNRESOLVED` where no re-evaluation occurred** — reference the
  existing verification. Be consistent, and state it in the log so Task 11 renders it correctly.
  If you believe a new row should be written even without corrections, raise it with the project
  lead rather than deciding unilaterally.
* **Whether a corrected verification triggers a new blockchain submission** is **Task 10**'s
  decision. Do not implement chain logic here.

---

# 12. Handoff Notes

* **Publish the storage shape for original-plus-corrected field entries.** Task 11 renders both side
  by side and cannot build the review screen without it.
* Tell Task 10 that a `CORRECT` produces a new verification ID, and ask them to decide the chain
  re-submission behaviour explicitly.
* Tell Task 11 the exact request and response shapes, and that `new_verification_id` may equal the
  original for `ACCEPT`/`UNRESOLVED`.
* Record the manual walkthrough results — Task 12 rehearses this exact sequence, and it is the
  strongest moment in the demo.

---

# 13. Definition of Done

```text
Implementation complete
        +
Tests passing (including the full correction-preserves-history scenario)
        +
Manual walkthrough complete
        +
Scope verified (no auth, no rule changes, no registry edits, no chain logic)
        +
Git diff reviewed
        +
Development log updated with the field-entry storage shape
        +
No locked contracts violated
        +
Feature branch pushed
        ↓
PR ready
```

---

## Final Agent Instruction

Before making changes:

1. Read `AGENTS.md`, especially Rule 9.
2. Read `docs/verification-rules.md` §"Human review" and `docs/data-model.md`'s note on corrections.
3. Read `docs/api.md` for the review endpoint contract.
4. Read `logs/task-07-rules.md` for the `evaluate()` signature.
5. Read this task file completely.
6. State your plan, including how you will store original-plus-corrected entries, before coding.

During implementation:

* **Never overwrite an OCR value. Never update a verification row. Add, always.**
* Re-evaluate through Task 07's `evaluate()`. Do not reimplement it and do not special-case reviewed
  documents.
* Never let a reviewer set a status directly, edit the registry, or alter history.
* Do not mutate stored confidence on `ACCEPT` — pass a flag.
* Do not build authentication.
* Test the full correction scenario end to end before anything else.

If re-evaluation would need different rules for a reviewed document, **stop and ask the project
lead** — that would be a change to `docs/verification-rules.md`.

Before PR:

* Run the tests and report exact output.
* Walk the manual scenario and confirm the original verification row is untouched.
* Review `git diff` and `git status`.
* Update `logs/task-08-review.md` with the field-entry storage shape.
* Push and open the PR per `docs/git-workflow.md`.
