# PS21 Task Specification

> **This file is a work order for the assigned developer and their AI coding agent.**
>
> Do not expand the scope without explicit approval from the project lead.

---

## Task Information

**Task:** `Backend workflow and API integration`
**Task ID:** `10` (`docs/implementation-plan.md` step 10)
**Assigned To:** `Unassigned` (suggested: project lead)
**Branch:** `feature/task-10-integration`
**Priority:** `Critical` — on the critical path; nothing works end to end until this lands
**Status:** `Not Started`

---

# 1. Goal

## Objective

Wire Tasks 02–09 into one coherent backend: complete the full `docs/api.md` surface, connect
upload → OCR → extraction → verification → blockchain, and make the whole pipeline work from a
single upload through to a chain receipt.

Expected outcome: a document uploaded through the API is processed, extracted, verified, and
recorded on-chain, with every endpoint in `docs/api.md` implemented and every documented error code
reachable.

## Why This Exists

Step 10 of `docs/implementation-plan.md`. Every preceding task built one piece against a contract.
This is where the contracts meet reality.

**Integration failures look different from unit failures.** Each component passed its own tests
against its own fakes. The bugs that appear here are the ones fakes cannot catch: a service
returning a shape slightly different from what the next one expects, a session committed at the
wrong moment, an exception type nobody handles at the boundary.

This task also resolves the remaining sequencing decisions — when OCR runs, when submission happens,
what a corrected verification does on-chain. Those were deliberately deferred to here because they
can only be answered once the pieces exist.

---

# 2. Authoritative Documentation

* `AGENTS.md` — all twelve rules; this task can violate any of them by accident
* `docs/api.md` — **authoritative**: the complete endpoint surface
* `docs/architecture.md` — **authoritative**: request lifecycle and the failure-isolation table
* `docs/workflow.md` — the end-to-end narrative this task makes real
* `docs/backend.md` — layering: API calls exactly one service; no business logic in routers
* `docs/decisions.md` — D-16 (synchronous for MVP)
* `docs/testing.md` — the required scenarios
* `docs/verification-rules.md`, `docs/blockchain.md` — the statuses being wired
* Every `logs/task-NN-*.md` — the published interfaces you are connecting

---

# 3. Scope

## In Scope

* Complete all ten endpoints in `docs/api.md`, verifying every one against the documented shape.
* `backend/app/services/` — the orchestration connecting upload → OCR → extraction → verification →
  blockchain.
* Resolve and implement the three sequencing decisions in §11.
* Transaction and session management across the flow.
* Consistent error mapping: every documented code reachable, nothing leaking internals.
* `backend/tests/test_api_documents.py`, `test_api_verifications.py`, and one full end-to-end
  pipeline test.
* Update `docs/api-manual-testing-guide.md` if any curl example drifted from reality.

## Out of Scope

* Changing any domain logic — Tasks 05–09 own their internals. If one is wrong, **report it to its
  owner**; do not patch it here. A fix applied in the integration branch will be silently reverted
  the next time that task's owner touches their module.
* Frontend — **Task 11**.
* End-to-end tests against the real UI and demo rehearsal — **Task 12**.
* New endpoints not in `docs/api.md`.
* Performance optimisation beyond meeting `NFR-09` (15s for a single page).
* Authentication — out of MVP scope (`docs/decisions.md` D-11).

---

# 4. Allowed Files / Areas

```text
backend/app/api/documents.py
backend/app/api/verifications.py
backend/app/api/document_types.py
backend/app/api/health.py
backend/app/main.py
backend/app/services/*.py          (orchestration only — not domain logic)
backend/tests/test_api_documents.py       (new)
backend/tests/test_api_verifications.py   (new)
backend/tests/test_e2e_pipeline.py        (new)
docs/api-manual-testing-guide.md          (corrections only)
```

### Explicitly Not Allowed

```text
backend/app/domain/**        — Tasks 06, 07 own these
backend/app/adapters/**      — Tasks 05, 09 own these
backend/app/models/**        — Task 02 owns these
backend/app/repositories/**  — Task 02 owns these
```

Finding a bug in one of these is a **normal and expected outcome** of this task. The correct
response is a message to its owner with a reproduction, not an edit.

---

# 5. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Tasks 02–09 | **Hard** | All of them. This is the convergence point |
| Every `logs/task-NN-*.md` | **Hard** | The published interfaces |

### Dependency Status

* [ ] Dependencies exist and are ready
* [x] Being developed separately — this task starts when Tasks 02–09 have all merged
* [x] Requires coordination: with every task owner, continuously

### Parallel-development notes

This task cannot start early, but it can **prepare** early: read every published interface, write
the integration tests against `docs/api.md` before the implementation exists, and list the shape
mismatches you expect. Tests written against the contract rather than the code find integration bugs
immediately instead of after a day of manual clicking.

---

# 6. Contracts That Must Be Preserved

### API surface (`docs/api.md`) — all ten, exactly

```
GET  /api/v1/health
GET  /api/v1/document-types
POST /api/v1/documents
GET  /api/v1/documents/{id}
GET  /api/v1/documents/{id}/extraction
GET  /api/v1/documents/{id}/verifications      ← history + is_current
POST /api/v1/documents/{id}/verify
GET  /api/v1/verifications/{id}
POST /api/v1/verifications/{id}/review
GET  /api/v1/verifications/{id}/blockchain
```

Field names, status codes, and error codes exactly as documented. Task 11 is building against this
in parallel — an undocumented difference here surfaces as a frontend bug someone else spends hours
on.

### Layering (`docs/backend.md`)

Routers parse the request, call **exactly one** service method, and map the result. No `if status ==
...` logic in a router, no repository call from a router, no business rule in the API layer.

### Failure isolation (`docs/architecture.md`) — verify the whole table

| Failure | Result |
|---|---|
| Upload validation fails | No document row; `4xx` |
| OCR fails | `extraction_results.status = FAILED`; verification → `PROCESSING_FAILED` |
| OCR low confidence | Extraction succeeds; verification → `REVIEW_REQUIRED` |
| No registry record | `NO_TRUSTED_RECORD` |
| Registry query errors | `PROCESSING_FAILED` — **distinct from** no-record |
| Rule mismatch | `INTEGRITY_MISMATCH` |
| Chain unreachable | `blockchain_records.recording_status = FAILED`; **verification unchanged** |

Every row gets an integration test. This table is the project's correctness specification and this
is the only task positioned to verify it end to end.

### Business outcomes are not errors

`NO_TRUSTED_RECORD` and `REVIEW_REQUIRED` return `200` (`docs/api.md`). A failed OCR returns `200`
with `status: "FAILED"` on the extraction endpoint, not a `4xx`.

### Error envelope

All errors go through Task 01's single handler. No route formats its own. No message contains a
stack trace, filesystem path, connection string, or `CHAIN_EVENT_SALT`.

### Session management

One database session per request, committed once at the end of a successful flow, rolled back on
error. **A partial pipeline must never leave a half-written state** — an extraction row written and
a verification row missing, with the document stuck in `OCR_IN_PROGRESS`, is worse than a clean
failure because nothing retries it.

---

# 7. Implementation Requirements

### Requirement 1 — Resolve the sequencing decisions

Three decisions were deferred to this task. Decide each explicitly, implement it, and **record it in
`docs/decisions.md` as a new `D-NN`**. Do not leave any of them implicit in code.

**(a) When does OCR run?** **Already resolved — D-19 is closed.** `POST /documents` stores and
returns `UPLOADED`; `POST .../verify` runs OCR on demand when no extraction exists, synchronously.
Implement exactly the sequence and state table in `docs/document-processing.md` §"Processing-state
contract". Do not re-open this; do not expose a state the backend cannot produce, and do not return
`PENDING` from any endpoint.

**(b) When does blockchain submission happen?** Recommended: automatically after a verification
reaches a terminal status, inside `POST .../verify`, non-blocking in the sense that a chain failure
never fails the verify call.

**(c) Does a corrected verification re-submit on-chain?** Recommended: yes — a new verification ID
produces a different `verificationRef`, so both events coexist and the correction is itself part of
the permanent record. Confirm with Task 09's owner.

### Requirement 2 — Complete the endpoints

Implement or verify all ten. For each, compare the actual response against `docs/api.md` field by
field. Where they differ, **the documentation is right and the code changes** — unless the
documentation is genuinely wrong, in which case stop and get project-lead approval for a doc update
in this same PR.

### Requirement 3 — Wire the pipeline

`POST /documents` → validate, store, `documents` row (Task 04).
Processing → `ocr_service.process_document` (Task 05) → `extraction_service.extract_fields` (Task 06).
`POST .../verify` → `verification_service` (Task 07) → on terminal status →
`blockchain_service.submit_verification` (Task 09).
`POST .../review` → `review_service` (Task 08) → re-verification → chain per decision (c).

### Requirement 4 — Error mapping

Every documented code reachable end to end. Map each service exception to exactly one status and
code, in one place. Unhandled exceptions produce `500 INTERNAL_ERROR` with a `correlation_id` and
nothing internal in the message.

### Requirement 5 — Blockchain never blocks verification

A chain failure inside `POST .../verify` leaves the verification response unchanged and correct. The
blockchain state is visible only through `GET .../blockchain`. Wrap the submission so no exception
from it can escape into the verify response path.

### Requirement 6 — Performance check

Time a single-page document through the full pipeline. `NFR-09` budgets 15 seconds. If it exceeds
that, report it with the breakdown — do not silently accept it, and do not fix it by removing the
frontend's loading state.

### Error Handling

* Any service exception → its documented code.
* Unhandled → `500` with correlation ID.
* Pipeline partial failure → session rolled back; no half-written state.
* Chain failure → contained; never escapes into the verify response.

---

# 8. Testing Requirements

## Automated Tests

`backend/tests/test_api_documents.py` — every documents endpoint, success and every error code,
response shapes asserted against `docs/api.md` **literally**, not against what the code returns.

`backend/tests/test_api_verifications.py` — every verifications endpoint, all six statuses through
the API, review flow, blockchain endpoint enabled and disabled.

`backend/tests/test_e2e_pipeline.py` — the full flow with fake OCR and fake chain adapters:

* Upload → process → verify → `VERIFIED_MATCH` → chain `CONFIRMED`.
* Upload → process → verify → `INTEGRITY_MISMATCH` → chain `CONFIRMED` with `outcomeCode = 3`.
* Upload → process → verify → `NO_TRUSTED_RECORD` → chain `CONFIRMED` with `outcomeCode = 2`.
* Upload → process (low confidence) → verify → `REVIEW_REQUIRED` → correct → new verification
  `VERIFIED_MATCH` → chain records both events.
* Upload → OCR fails → verify → `PROCESSING_FAILED`, extraction endpoint returns `200` with
  `status: "FAILED"`.
* **Chain unavailable → verification completes normally, blockchain shows `FAILED`, and the
  verification row is byte-identical to the chain-available case.** This is the failure-isolation
  proof.
* Registry error → `PROCESSING_FAILED`, asserted **not** `NO_TRUSTED_RECORD`.
* A partial pipeline failure leaves no half-written state.

Run:

```bash
cd backend && pytest
```

The **entire** suite — every task's tests together. Cross-task regressions are exactly what this
task exists to catch.

## Manual Verification

Follow `docs/api-manual-testing-guide.md` end to end with curl, with real PaddleOCR and a real
Hardhat node:

1. Health → all components reported correctly.
2. Document types → matches `docs/category-schemas.md`.
3. Upload each of Task 03's five academic-certificate scenarios and walk each to completion.
4. Verify each produces its expected status (recorded in `logs/task-07-rules.md`).
5. Perform a real review correction and confirm both verifications exist on-chain.
6. Stop the Hardhat node, run a verification, confirm isolation.
7. Time a single-page document end to end.
8. Correct any drift in `docs/api-manual-testing-guide.md`.

---

# 9. Acceptance Criteria

* [ ] All ten endpoints implemented and verified field by field against `docs/api.md`.
* [ ] `GET /documents/{id}/verifications` returns newest-first with exactly one `is_current: true`.
* [ ] "Current" is resolved only via `verification_repo.get_latest_for_document()`.
* [ ] No endpoint returns `PENDING`.
* [ ] D-20 and D-21 resolved, implemented, and recorded in `docs/decisions.md`; D-19 implemented as already specified.
* [ ] Full pipeline works end to end for all five demo scenarios.
* [ ] Every row of the failure-isolation table verified by a test.
* [ ] **A chain failure never changes a verification result** — proven by test.
* [ ] `NO_TRUSTED_RECORD` and `REVIEW_REQUIRED` return `200`.
* [ ] A failed extraction returns `200` with `status: "FAILED"`, not a `4xx`.
* [ ] Every documented error code reachable.
* [ ] No error message leaks internals or secrets.
* [ ] Routers contain no business logic and call exactly one service each.
* [ ] No partial-failure half-written state.
* [ ] **No file under `domain/`, `adapters/`, `models/`, or `repositories/` was modified.**
* [ ] The full suite passes.
* [ ] `docs/api-manual-testing-guide.md` matches reality.
* [ ] Single-page timing recorded against `NFR-09`.
* [ ] `git diff` reviewed; development log updated; branch pushed; PR prepared.

---

# 10. Known Risks

* **Fixing other people's modules.** The strongest temptation in this task. It creates merge
  conflicts, it gets reverted, and it means the owner never learns their module had a bug. Report
  with a reproduction instead.
* **Shape mismatches between services.** Each was tested against its own fakes. Where two real
  components meet, assumptions diverge. Expect this; it is the normal work of integration.
* **Chain failure leaking into the verify path.** An unhandled exception from submission inside
  `POST .../verify` would fail the whole call and break failure isolation invisibly.
* **Session commit timing.** Commit too early and a later failure leaves inconsistent state; too
  late and the flow holds a transaction open across a slow OCR run.
* **Documenting around a bug.** If the code returns something different from `docs/api.md`, the
  default is that the code is wrong. Changing the doc to match the code requires project-lead
  approval, and it invalidates whatever Task 11 built against it.
* **Synchronous OCR blocking the request.** Accepted for MVP (D-16), but the frontend must show
  honest progress. Do not fix slow OCR by hiding it.

---

# 11. Open Questions

All three must be resolved **by this task**, recorded in `docs/decisions.md`:

* ~~**(a) OCR trigger point.**~~ **Closed — D-19.** Implement `docs/document-processing.md`
  §"Processing-state contract" as written.
* **(b) Blockchain submission trigger.** Recommendation in §7 Requirement 1; confirm with Task 09.
* **(c) Corrected-verification re-submission.** Recommendation in §7 Requirement 1; confirm with
  Tasks 08 and 09.

Do not leave any of these implicit. An undocumented sequencing decision is exactly the kind of thing
that changes silently three commits later.

---

# 12. Handoff Notes

* Publish in the log: the three resolved decisions, the confirmed endpoint behaviours, and any place
  where the real backend differs from `docs/api.md` **before** Task 11 finishes.
* Tell Task 11 immediately about any shape difference — they are coding against `api.md` right now.
* Tell Task 12 which scenarios are verified end to end and the timing numbers.
* Report every bug found in another task's module to its owner, with a reproduction.
* Note any performance concern for the demo machine.

---

# 13. Definition of Done

```text
All ten endpoints implemented and verified
        +
Three sequencing decisions resolved and documented
        +
Full test suite passing
        +
All five scenarios verified manually with real OCR and real chain
        +
Failure isolation proven
        +
Scope verified (no domain/adapter/model/repository edits)
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

1. Read `AGENTS.md`.
2. Read `docs/api.md` **completely** — all ten endpoints.
3. Read `docs/architecture.md` §"Failure isolation table" — you are verifying every row.
4. Read every `logs/task-NN-*.md` for the published interfaces.
5. Read this task file completely.
6. State your plan, including your recommendation on each of the three open questions, before coding.

During implementation:

* **Do not edit files under `domain/`, `adapters/`, `models/`, or `repositories/`.** Finding bugs
  there is expected; report them to their owners with a reproduction.
* Assert response shapes against `docs/api.md`, not against what the code currently returns.
* Keep routers thin — parse, call one service, map the result.
* Ensure a chain failure can never escape into the verify response.
* Resolve all three sequencing decisions explicitly and document them.
* Run the **full** suite frequently — cross-task regressions are the point.

If the real backend differs from `docs/api.md`, **the default is that the code is wrong**. Changing
the documentation needs project-lead approval and a same-PR update, because Task 11 is building
against it right now.

Before PR:

* Run the full suite and report exact output.
* Walk `docs/api-manual-testing-guide.md` end to end with real OCR and a real chain.
* Verify failure isolation by stopping the node mid-flow.
* Record single-page timing.
* Review `git diff` and `git status`; confirm no out-of-scope files.
* Update `logs/task-10-integration.md` with the three decisions.
* Push and open the PR per `docs/git-workflow.md`.
