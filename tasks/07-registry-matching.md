# PS21 Task Specification

> **This file is a work order for the assigned developer and their AI coding agent.**
>
> Do not expand the scope without explicit approval from the project lead.

---

## Task Information

**Task:** `Registry matching and deterministic rules`
**Task ID:** `07` (`docs/implementation-plan.md` step 7)
**Assigned To:** `Unassigned` (suggested: Member B)
**Branch:** `feature/task-07-rules`
**Priority:** `Critical` — on the critical path; this is the heart of the system
**Status:** `Not Started`

---

# 1. Goal

## Objective

Implement `normalization.py`, `matching.py`, `rules.py`, `status.py`, and `verification_service.py`
exactly per `docs/verification-rules.md`: find the applicable synthetic registry record, compare
match fields, run the deterministic rule set, and assign exactly one of six statuses via the
documented precedence order.

Expected outcome: every one of the six statuses is reachable and correct; every outcome carries
field-level evidence and a reason code; and identical inputs always produce identical results.

## Why This Exists

Step 7 of `docs/implementation-plan.md`. **This is the task the project is judged on.** It is where
"cross-check records with authorized databases, detect forged or tampered documents" from the
problem statement actually happens.

It is also where the project's intellectual position lives. A lesser system outputs a confidence
percentage and hopes nobody asks how it was computed. This one outputs a named status, the exact
field that disagreed, the expected and observed values, and the rule that produced the conclusion.
That is harder to build and enormously easier to defend (`docs/judging-and-pitch.md`).

Two distinctions carry most of the weight, and both are easy to get wrong:

**`NO_TRUSTED_RECORD` is not `INTEGRITY_MISMATCH`.** No reference to check against is a completely
different statement from a reference that disagrees. Conflating them means telling someone with a
genuine document that it looks forged, purely because they are not in your registry
(`AGENTS.md` Rule 4).

**A technical failure is not a verdict.** A database error is `PROCESSING_FAILED`, never a mismatch
(`AGENTS.md` Rule 3).

---

# 2. Authoritative Documentation

* `AGENTS.md` — Rules 3, 4, 5, 8
* `docs/verification-rules.md` — **authoritative** (entire document): normalization, matching steps
  1–6, the rule table, the status vocabulary, and the precedence order
* `docs/category-schemas.md` — `match_field` flags and identifying keys
* `docs/data-model.md` — `verification_results` columns and their JSON shapes
* `docs/api.md` — `POST /documents/{id}/verify`, `GET /verifications/{id}`
* `docs/architecture.md` — `domain/` purity; the failure-isolation table
* `docs/configuration.md` — `LOW_CONFIDENCE_THRESHOLD` (0.70)
* `docs/decisions.md` — D-04 (deterministic, not ML), D-15 (precedence order)
* `docs/workflow.md` Stage 5
* `logs/task-06-extraction.md` — the `extracted_fields` shape

---

# 3. Scope

## In Scope

* `backend/app/domain/status.py` — the six verification statuses and four blockchain statuses as
  enums. The single definition; nothing redefines them anywhere.
* `backend/app/domain/normalization.py` — the normalization rules, applied identically to extracted
  and registry values.
* `backend/app/domain/matching.py` — matching steps 1–6, returning the applicable record (or none)
  plus per-field comparisons.
* `backend/app/domain/rules.py` — the five documented rules, plus the precedence function.
* `backend/app/services/verification_service.py` — loads extraction and registry, calls the domain
  functions, writes `verification_results`.
* `POST /documents/{document_id}/verify` and `GET /verifications/{verification_id}` per
  `docs/api.md`.
* `backend/tests/test_matching_rules.py`.

## Out of Scope

* Human review — **Task 08**. This task produces statuses; it does not act on them.
* Blockchain submission — **Task 09/10**. Verification never touches the chain.
* OCR or extraction — Tasks 05/06.
* Any new rule, status, or reason code not in `docs/verification-rules.md` — that is a contract
  change requiring project-lead approval.
* Any ML model, scoring function, or probability (`docs/decisions.md` D-04).
* Image forensics or tamper detection — out of project scope.

---

# 4. Allowed Files / Areas

```text
backend/app/domain/status.py
backend/app/domain/normalization.py
backend/app/domain/matching.py
backend/app/domain/rules.py
backend/app/services/verification_service.py
backend/app/api/verifications.py               (verify + get only)
backend/tests/test_matching_rules.py           (new)
```

### May Modify If Required

```text
backend/app/main.py    (register the verifications router)
```

---

# 5. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Task 06 (`extracted_fields` shape) | **Hard** | The input. Published in `logs/task-06-extraction.md` |
| Task 03 (seeded registry) | **Hard** | Nothing to match against otherwise |
| Task 02 (`verification_repo`, `registry_repo`) | **Hard** | Persistence and lookup |
| `docs/verification-rules.md` | **Contract** | Frozen, including precedence |

### Dependency Status

* [x] Dependencies exist once Tasks 02, 03, 06 merge
* [x] Requires coordination: Task 08 extends this service with review-triggered re-runs

### Parallel-development notes

`domain/` here is pure and takes plain dicts. Build and fully test `normalization.py`,
`matching.py`, and `rules.py` against hand-written dicts **before** Task 06 merges — they need
nothing but the shape, which is published early. Only `verification_service.py` waits on the
database.

---

# 6. Contracts That Must Be Preserved

### Status precedence (`docs/verification-rules.md`, `docs/decisions.md` D-15)

Evaluated in this exact order, first match wins:

1. OCR/extraction failed → `PROCESSING_FAILED`
2. Any required field missing, **or** any match field's confidence below `LOW_CONFIDENCE_THRESHOLD`
   → `REVIEW_REQUIRED`
3. No applicable registry record → `NO_TRUSTED_RECORD`
4. Applicable record exists and any match-field comparison fails → `INTEGRITY_MISMATCH`
5. Applicable record exists and all match-field comparisons pass → `VERIFIED_MATCH`

This order is **not a judgement call**. Implement it as a literal ordered sequence of checks, so the
code reads the same way the document does. That makes it reviewable and makes disagreements about
behaviour resolvable by reading one function.

Note carefully: step 2 runs **before** step 3. A low-confidence document with no registry record is
`REVIEW_REQUIRED`, not `NO_TRUSTED_RECORD` — because we cannot yet trust the key we would have
looked it up by.

### Matching (`docs/verification-rules.md` steps 1–6)

1. Candidates are `registry_records` with the document's `category` and `active = true`.
2. A candidate matches if **all** `match_field: true` fields are non-null on the extracted side and
   equal post-normalization.
3. Exactly one candidate satisfies step 2 → matched record.
4. Zero satisfy step 2, but a record shares the **identifying key** → that record is the
   *applicable reference*; its disagreeing fields are reported individually. This is what produces
   `INTEGRITY_MISMATCH` rather than a blanket no-record.
5. No record shares even the identifying key → `NO_TRUSTED_RECORD`.
6. More than one candidate satisfies step 2 → `PROCESSING_FAILED` with a reason naming a registry
   data error. **This points at a seeding bug, not a document problem** — never report it as a
   mismatch.

Identifying keys: `student_id`, `id_number`, `demo_pan_code`, `certificate_number`
(`docs/category-schemas.md`).

### Normalization

Applied **identically** to both sides before comparison:

* Text: trim, collapse internal whitespace, case-fold **for comparison only** — the stored value
  keeps its original casing.
* Dates: must already be `YYYY-MM-DD`; anything else is excluded from date comparison with a warning.
* **Never strip or replace characters in a way that changes an identifier's meaning.** Do not
  remove hyphens from `DEMO-STU-001`, do not strip letters, do not "fix" `O` to `0`. That last one
  is exactly the OCR error the human-review path exists for (`docs/workflow.md` Stage 6) — silently
  correcting it here would mean the system confidently matches a document it misread.

Both original and normalized values are retained for audit display.

### Rules (`docs/verification-rules.md`)

The five documented rules: `required_field_presence`, `field_match`, `category_schema_validity`,
`date_consistency`, `known_fixture_duplicate`.

`date_consistency` has **no implemented check for the current four categories** — it is a declared
placeholder. Implement it as a no-op that always passes, and **do not invent a check for it**
(`AGENTS.md` Rule 1).

**Every rule returns a boolean and a fixed human-readable reason string. No rule returns a number,
a weight, a probability, or a score** (`AGENTS.md` Rule 8). If a future maintainer wants a score,
that is a decision-log entry, not a local change.

### Determinism (`NFR-04`)

Identical normalized inputs plus identical configuration always produce an identical result. No
randomness, no time-dependence in the decision path, no iteration over an unordered set in a way
that affects which record is chosen.

### Output shape (`docs/data-model.md`, `docs/api.md`)

* `field_comparisons_json` — `[{field, extracted_value, registry_value, matched}]`, one entry per
  match field.
* `rule_results_json` — `[{rule_id, passed, reason}]`, one entry per rule, always all five.
* `reason_codes_json` — e.g. `["FIELD_MISMATCH:semester_or_year"]`.
* A **new** `verification_results` row per run (`docs/decisions.md` D-18). Never an update.
* `supersedes_verification_id` is **null** for every row this task writes — only Task 08's
  re-evaluation sets it (`docs/decisions.md` D-23).
* The committed row always carries a **terminal** status. `PENDING` is a column default that exists
  only inside the transaction and is never returned by any endpoint
  (`docs/document-processing.md` §"Processing-state contract").

### Purity

`domain/` imports no FastAPI, SQLAlchemy, PaddleOCR, or Web3. It takes dicts and returns dicts.

---

# 7. Implementation Requirements

### Requirement 1 — `status.py`

Python enums for the six verification statuses and four blockchain statuses. Every other module
imports from here. No status string is written as a literal anywhere else in the backend.

### Requirement 2 — `normalization.py`

`normalize_text(value) -> str`, `normalize_date(value) -> str | None`,
`normalize_for_comparison(value, field_type) -> tuple[str, str]` returning `(original, normalized)`.
Pure functions, no side effects.

### Requirement 3 — `matching.py`

```python
def find_applicable_record(
    category: str,
    extracted_fields: dict,
    candidates: list[dict],
    schema: CategorySchema,
) -> MatchResult
```

`MatchResult` carries the matched record (or `None`), whether it was a full match or only an
applicable reference, the per-field comparisons, and a flag for the multiple-candidates error.
Candidates are passed **in** — matching does not query the database (purity).

### Requirement 4 — `rules.py`

Each rule is a function `(extracted_fields, registry_record, schema) -> RuleResult`. Then:

```python
def evaluate(
    extraction_status: str,
    extracted_fields: dict,
    match_result: MatchResult,
    schema: CategorySchema,
    low_confidence_threshold: float,
) -> VerificationOutcome
```

`evaluate` implements the precedence order as a literal ordered sequence. Write it so a reader can
put `docs/verification-rules.md` beside it and check them off one by one.

### Requirement 5 — `verification_service.py`

1. Load the document and its latest successful extraction.
2. Extraction `FAILED` or absent → `PROCESSING_FAILED` immediately (precedence step 1).
3. Load active registry candidates for the category.
4. Call `find_applicable_record`, then `evaluate`.
5. Write a new `verification_results` row with all four JSON fields populated.

**Wrap registry loading in its own error handling.** A database error there is
`PROCESSING_FAILED` with a distinct reason — never "no record found"
(`docs/architecture.md` failure isolation). These two are a single `except` away from each other and
getting it wrong means a database hiccup silently reads as a clean bill of health.

### Requirement 6 — Endpoints

`POST /documents/{document_id}/verify` → `200 {verification_id, status, document_id}`;
`404 DOCUMENT_NOT_FOUND`; `409 EXTRACTION_NOT_READY` when there is no successful extraction.

`GET /verifications/{verification_id}` → the full documented shape including `field_comparisons`,
`rule_results`, and `reason_codes`; `404 VERIFICATION_NOT_FOUND`.

**`NO_TRUSTED_RECORD` and `REVIEW_REQUIRED` are `200` responses** (`docs/api.md`). They are valid
business outcomes, not errors.

### Error Handling

| Situation | Result |
|---|---|
| Extraction missing or `FAILED` | `PROCESSING_FAILED`, reason `EXTRACTION_FAILED` |
| Registry query raises | `PROCESSING_FAILED`, reason `REGISTRY_ERROR` — distinct from no-record |
| Multiple candidates fully match | `PROCESSING_FAILED`, reason `REGISTRY_DATA_ERROR` |
| Unknown category | `500 INTERNAL_ERROR` |
| A rule function raises | `PROCESSING_FAILED`, reason naming the rule; never a mismatch |

---

# 8. Testing Requirements

This task needs the most thorough tests in the project. Every status, every precedence branch.

## Automated Tests

`backend/tests/test_matching_rules.py`:

**Normalization**
* Whitespace and case differences normalize to equal.
* `DEMO-STU-001` is never altered — hyphens preserved, letters preserved.
* `O` versus `0` do **not** normalize to equal. Assert this explicitly; it is the property that
  makes the review flow necessary and meaningful.
* `15-01-1999` fails date normalization and is excluded from comparison.

**Matching**
* All match fields equal → matched record.
* Identifying key matches, one other field differs → applicable reference returned, that field
  flagged, `is_full_match = False`.
* No record shares the identifying key → no applicable record.
* An `active = false` record that would otherwise match → not a candidate.
* Two active records fully matching → multiple-candidates error flag.

**Each status reachable**
* `VERIFIED_MATCH` — clean match.
* `INTEGRITY_MISMATCH` — one match field differs; the response names it with expected vs. observed.
* `NO_TRUSTED_RECORD` — unregistered identifying key.
* `REVIEW_REQUIRED` via missing required field.
* `REVIEW_REQUIRED` via confidence below 0.70 on a match field.
* `PROCESSING_FAILED` via failed extraction.
* `PROCESSING_FAILED` via registry error — and assert it is **not** `NO_TRUSTED_RECORD`.

**Precedence — the critical tests**
* Failed extraction **and** a would-be mismatch → `PROCESSING_FAILED` (step 1 wins).
* Missing required field **and** no registry record → `REVIEW_REQUIRED` (step 2 beats step 3).
* Low confidence **and** a would-be match → `REVIEW_REQUIRED` (step 2 beats step 5).
* Applicable record with a mismatch, all confidences high → `INTEGRITY_MISMATCH`.

**Determinism**
* The same input evaluated 100 times yields byte-identical output.
* Candidate list order does not affect the result.

**No scoring**
* Assert no `RuleResult` field holds a float or int that could read as a score. Inspect the returned
  structures directly.

**Purity**
* Importing `domain/matching.py` and `domain/rules.py` pulls in no FastAPI, SQLAlchemy, PaddleOCR, or
  Web3.

**Endpoints**
* `POST .../verify` → `200` with the documented body.
* `NO_TRUSTED_RECORD` and `REVIEW_REQUIRED` both return `200`, not an error status.
* `GET /verifications/{id}` → full shape with all three JSON arrays populated.
* Two verify calls on one document → two rows; the first is unchanged.

Run:

```bash
cd backend && pytest tests/test_matching_rules.py
```

## Manual Verification

With the registry seeded and Task 03's samples:

1. `academic_certificate_match.png` → `VERIFIED_MATCH`, all six comparisons matched.
2. `academic_certificate_mismatch.png` → `INTEGRITY_MISMATCH` naming `semester_or_year`, expected
   `5`, observed `6`.
3. `academic_certificate_unregistered.png` → `NO_TRUSTED_RECORD`.
4. `academic_certificate_degraded.png` → `REVIEW_REQUIRED` with the reason stating which field.
5. Stop the database mid-verify → `PROCESSING_FAILED`, not a mismatch.

Record all five in the log. Task 12's rehearsal depends on these exact outcomes.

---

# 9. Acceptance Criteria

* [ ] `status.py` is the single definition of all status values; no literals elsewhere.
* [ ] Normalization never alters identifier meaning; `O` and `0` stay distinct.
* [ ] Matching implements steps 1–6 including the applicable-reference case.
* [ ] Inactive records are excluded.
* [ ] Multiple full matches → `PROCESSING_FAILED` with a registry-data reason, never a mismatch.
* [ ] Precedence implemented as a literal ordered sequence matching `docs/verification-rules.md`.
* [ ] All six statuses reachable and individually tested.
* [ ] A registry error is `PROCESSING_FAILED`, provably distinct from `NO_TRUSTED_RECORD`.
* [ ] All five rules implemented; `date_consistency` is an explicit no-op, not an invented check.
* [ ] **No rule returns a score, weight, or probability.**
* [ ] Every outcome carries field comparisons, rule results, and reason codes.
* [ ] A new `verification_results` row per run; no row is ever updated.
* [ ] `supersedes_verification_id` is null on every row this task writes.
* [ ] No endpoint ever returns `PENDING`.
* [ ] `domain/` is pure.
* [ ] `NO_TRUSTED_RECORD` and `REVIEW_REQUIRED` return `200`.
* [ ] Determinism verified.
* [ ] All tests pass; all five manual scenarios verified and recorded.
* [ ] `git diff` reviewed; development log updated; branch pushed; PR prepared.

---

# 10. Known Risks

* **Collapsing `NO_TRUSTED_RECORD` into `INTEGRITY_MISMATCH`.** The single most consequential bug
  available in this project, and it will be the first thing a sharp judge probes.
* **A registry exception reading as "no record".** One `except` clause away. Test it explicitly.
* **Precedence written as nested conditionals.** It becomes unreviewable, and the step-2-before-step-3
  ordering gets lost. Write it flat and ordered.
* **Normalizing too aggressively to make a demo pass.** Explicitly forbidden (`AGENTS.md` Rule 8). If
  a fixture will not match, fix the fixture or the extraction — never loosen comparison.
* **Adding a score "for the UI".** No. `docs/decisions.md` D-04.
* **Implementing `date_consistency` because an empty rule looks unfinished.** It is declared and
  deliberately empty. Leave it.

---

# 11. Open Questions

* None. `docs/verification-rules.md` is complete, including precedence (D-15) and the multiple-match
  case. If something appears undefined, it is a documentation gap — report it to the project lead
  rather than choosing a behaviour.

---

# 12. Handoff Notes

* Publish in the log: the `evaluate()` signature and the `VerificationOutcome` shape. Task 08 calls
  `evaluate()` again with corrected values, and Task 10 wires it into the full flow.
* Tell Task 08 explicitly that re-evaluation must go through the **same** `evaluate()` — a reviewed
  document never gets a hand-assigned status.
* Tell Task 09/10 that verification never touches the chain; submission happens after, on a terminal
  status.
* Tell Task 11 the exact `field_comparisons` and `rule_results` shapes for the results table.
* Record the five manual scenario outcomes — Task 12 rehearses against them.

---

# 13. Definition of Done

```text
Implementation complete
        +
Tests passing (all six statuses + every precedence branch)
        +
All five manual scenarios verified and recorded
        +
Determinism verified
        +
Scope verified (no review, no blockchain, no scoring)
        +
Git diff reviewed
        +
Development log updated
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

1. Read `AGENTS.md`, especially Rules 3, 4, and 8.
2. Read `docs/verification-rules.md` **completely, twice**. It is this task's entire specification
   and the precedence order is exact.
3. Read `docs/category-schemas.md` for `match_field` flags and identifying keys.
4. Read `logs/task-06-extraction.md` for the input shape.
5. Read this task file completely.
6. State your plan, including how you will structure the precedence function, before coding.

During implementation:

* Implement precedence as a literal ordered sequence. Someone must be able to read your code beside
  the document and check them off.
* Keep `NO_TRUSTED_RECORD` and `INTEGRITY_MISMATCH` rigorously separate.
* Keep a registry **error** separate from a registry **miss**.
* Never return a score, weight, or probability from any rule.
* Never normalize in a way that changes an identifier's meaning.
* Leave `date_consistency` as a declared no-op.
* Keep `domain/` pure.
* Test each status individually before moving on.

If a fixture will not match, **fix the fixture or the extraction — never loosen the comparison
rules**, and never hand-assign a status.

Before PR:

* Run the tests and report exact output.
* Walk all five manual scenarios and record the outcomes.
* Review `git diff` and `git status`.
* Update `logs/task-07-rules.md` with the `evaluate()` signature and the scenario results.
* Push and open the PR per `docs/git-workflow.md`.
