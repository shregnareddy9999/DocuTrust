# PS21 Task Specification

> **This file is a work order for the assigned developer and their AI coding agent.**
>
> Do not expand the scope without explicit approval from the project lead.

---

## Task Information

**Task:** `Frontend upload, results, and review dashboard`
**Task ID:** `11` (`docs/implementation-plan.md` step 11)
**Assigned To:** `Unassigned` (suggested: Member D)
**Branch:** `feature/task-11-frontend`
**Priority:** `Critical` — this is what the judges actually look at
**Status:** `Not Started`

---

# 1. Goal

## Objective

Build every page and component in `docs/frontend.md` against the frozen `docs/api.md` contract:
upload, document detail, verification result, review, blockchain receipt, and the single-screen demo
dashboard.

Expected outcome: a complete flow from category selection through to a chain receipt, with
verification and blockchain status rendered as **separate** badges, the synthetic-data banner on
every result view, and honest loading, error, and empty states everywhere.

## Why This Exists

Step 11 of `docs/implementation-plan.md`. The backend can be flawless and the project still fails if
the interface overclaims or hides uncertainty.

This task carries the honesty commitment into the only place a judge will actually see it. A green
"VERIFIED" badge would undo everything Tasks 07 and 09 did carefully. The wording rules in
`AGENTS.md` Rule 2 and `docs/glossary.md` are enforced **here**, on screen, or they are not enforced
at all.

It is also the task with the most schedule freedom: `docs/api.md` is frozen, so this can start right
after Task 01 against a mock server and be largely finished before Task 10 exists.

---

# 2. Authoritative Documentation

* `AGENTS.md` — Rules 1, 2, 4, 5
* `docs/frontend.md` — **authoritative**: folder layout, hard rules, page flow
* `docs/api.md` — **authoritative**: every request and response shape
* `docs/glossary.md` §"Words we deliberately do not use" — the wording contract
* `docs/verification-rules.md` §"Status vocabulary" — the exact UI wording per status
* `docs/category-schemas.md` — via `GET /document-types`, never hardcoded
* `docs/deployment-demo.md` — the presenter wording table
* `docs/judging-and-pitch.md` — what judges see and probe
* `docs/configuration.md` — `VITE_API_BASE_URL`

---

# 3. Scope

## In Scope

* All six pages from `docs/frontend.md`: `UploadPage`, `DocumentDetailPage`,
  `VerificationResultPage`, `ReviewPage`, `BlockchainReceiptPage`, `DemoDashboardPage`.
* All components: `StatusBadge`, `FieldComparisonTable`, `SyntheticDataBanner`, `UploadDropzone`,
  `LoadingState`, `ErrorState`, `EmptyState`.
* `src/api/` — client with error-envelope parsing, plus the four module wrappers.
* `src/types/api.ts` — TypeScript types mirroring `docs/api.md` exactly.
* `src/state/` — `useDocument`, `useVerification` hooks.
* A mock server (`msw` or static JSON) so development proceeds before Task 10.
* `vitest` + React Testing Library tests.

## Out of Scope

* Backend changes of any kind. If the backend differs from `docs/api.md`, **report it** — do not
  adapt the frontend to undocumented behaviour. One of the two is wrong and someone has to decide
  which.
* Authentication or login (`docs/decisions.md` D-11).
* A state-management library — page-level hooks are sufficient (`docs/frontend.md`).
* WebSocket, SSE, or any polling loop — verification is synchronous and returns a terminal status
  directly (`docs/document-processing.md` §"Processing-state contract").
* A registry admin UI.
* Any UI string not traceable to `docs/verification-rules.md`, `docs/category-schemas.md`, or
  `docs/api.md`.

---

# 4. Allowed Files / Areas

```text
frontend/src/**                 (all pages, components, api, state, types)
frontend/package.json
frontend/vite.config.ts
frontend/.env.example
frontend/src/mocks/**           (mock server)
frontend/src/**/*.test.tsx      (tests)
```

### Explicitly Not Allowed

```text
backend/**                      — report differences; do not fix them here
docs/**                         — propose changes; do not make them
```

---

# 5. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Task 01 (Vite scaffold, `VITE_API_BASE_URL`) | **Hard** | The scaffold |
| `docs/api.md` | **Contract** | Frozen. This is what makes the early start possible |
| Task 10 (real backend) | **Integration** | Needed only for final verification |
| Task 06 (`GET /document-types`) | **Integration** | Mockable until it lands |

### Dependency Status

* [x] Dependency exists and is ready (`api.md` frozen)
* [x] Being developed separately (Task 10)
* [x] Requires coordination: report every real-backend difference to Task 10's owner immediately

### Parallel-development notes

**Start right after Task 01.** Build the entire frontend against a mock server implementing
`docs/api.md`. Mock every status and every error code — including the ones that are hard to produce
on a real backend, like a chain timeout. By the time Task 10 lands, integration should be a
configuration change and a round of verification.

---

# 6. Contracts That Must Be Preserved

### Never hardcode a field list (`docs/frontend.md`, hard rule)

Every category form and every field table renders from `GET /document-types`. Not from a constant,
not from a copy of `docs/category-schemas.md`. This is what keeps the frontend automatically correct
when the schema changes, and hardcoding is the single easiest way to make it silently wrong.

### Two badges, always separate

Verification status and blockchain status are **never** merged into one "overall status". A
blockchain `FAILED` with a verification `VERIFIED_MATCH` is a normal, correct state and must read as
one. Merging them would imply the chain validates the document, which is precisely the claim this
project refuses to make.

### `StatusBadge` is the only mapping

Status → label and colour lives in exactly one component. No status string appears as a literal
anywhere else in JSX. Labels come from `docs/verification-rules.md` §"Status vocabulary":

| Status | Label |
|---|---|
| `PENDING` | "Processing…" |
| `VERIFIED_MATCH` | "Matched our synthetic demo reference" |
| `REVIEW_REQUIRED` | "Needs human review" |
| `NO_TRUSTED_RECORD` | "No matching reference found in the demo registry — not evidence of a fake document" |
| `INTEGRITY_MISMATCH` | "Mismatch found" + the exact field(s) |
| `PROCESSING_FAILED` | "Could not complete verification — technical error" |

**Never** "Verified ✓", "Authentic", "Genuine", "Valid", or a checkmark that reads as authenticity
approval.

### Synthetic-data banner (`NFR-08`)

`SyntheticDataBanner` renders on **every** screen showing a registry match or a verification status.
Not a subtle footnote — visible at projector distance. This is a project requirement, not styling.

### Never hide a mismatch

`FieldComparisonTable` shows **every** match field, matched and unmatched, with extracted and
registry values side by side. No collapsing, no "show details" hiding failures behind a click. The
mismatch detail is the most persuasive thing on screen (`docs/judging-and-pitch.md` §3).

### Never fake a transaction

No placeholder hash, no optimistic `CONFIRMED`, no success animation for a failed submission. If the
backend says `FAILED`, the UI says failed and explains what that means and does not mean.

### All three states, every page (`docs/frontend.md`)

Loading, error, and empty. A blank white screen while OCR runs for eight seconds is a bug. A judge
watching it assumes the app crashed.

### Types mirror `docs/api.md`

`src/types/api.ts` matches the documented shapes exactly. If the backend returns something
different, **that is a bug to report**, not a type to loosen.

---

# 7. Implementation Requirements

### Requirement 1 — API client

`src/api/client.ts`: fetch wrapper reading `VITE_API_BASE_URL`, parsing the `docs/api.md` error
envelope, and throwing a typed `ApiError` with `code` and `message`. Components render `message` and
never a raw exception.

### Requirement 2 — Mock server

Implement all ten endpoints. Provide fixtures for **every** status and **every** documented error
code. Make the mode switchable — a query flag or an env var — so you can demonstrate any state on
demand. This is also genuinely useful for rehearsal: it lets you show a scenario that is awkward to
produce live.

### Requirement 3 — Upload page

Category picker populated from `GET /document-types`. Drag-and-drop plus file picker. Client-side
hints about accepted types and size, with the authoritative rejection still coming from the server.
Distinct, useful messages for each of `400`, `413`, `415`, `422` — `docs/troubleshooting.md` §3
describes what each one means to a user.

### Requirement 4 — Document detail

Extracted fields with per-field confidence. Missing fields shown explicitly as "not found", never
silently omitted. Warnings translated into plain language — `missing_field:student_id` renders as
"Student ID could not be read from the document". Low-confidence values visually flagged without
implying anything about authenticity.

### Requirement 5 — Verification result

The status badge, the reason in plain language, the full `FieldComparisonTable`, the rule results,
the review history if any, and the blockchain badge as a **separate** element.

**Do not poll.** `POST /documents/{id}/verify` is synchronous and its response already carries a
terminal status (`docs/document-processing.md` §"Processing-state contract"). Show a loading state
for the duration of that call, then render the result. A `PENDING`-to-terminal transition never
happens, so a polling loop would be waiting on nothing — and it would mask how long OCR actually
takes, which the user needs to see.

For history, call `GET /documents/{id}/verifications`. **Never compute "current" client-side by
sorting timestamps** — the endpoint marks exactly one entry `is_current`, and that is the project's
only definition (`docs/decisions.md` D-23).

### Requirement 6 — Review page

Reachable from `REVIEW_REQUIRED` and `INTEGRITY_MISMATCH`. Reviewer name field (free text —
`docs/decisions.md` D-11), the three actions, a correction form pre-filled with extracted values, and
a comment box.

**Show the original OCR value alongside any correction**, visually distinct (`docs/workflow.md`
Stage 6). After submission, display the new status and make it clear a new verification record was
created rather than the old one being edited. Post-review wording is "matched our synthetic demo
reference (reviewer-corrected)".

### Requirement 7 — Blockchain receipt

Transaction hash, chain ID, contract address, recording status, timestamps. Plus a short plain-
language explanation of **what this proves and what it does not** — the wording is in
`docs/blockchain.md` and `docs/judging-and-pitch.md` §3. When disabled, show `NOT_REQUESTED`
clearly rather than an empty panel.

**When `recording_status: "FAILED"`, render `error_code`** translated to plain language (e.g.
`RPC_UNAVAILABLE` → "Could not reach the blockchain network"), per `docs/frontend.md`
§"Blockchain failure detail". Never show a bare error code with no explanation, and never imply the
verification result is affected by a chain failure.

### Requirement 8 — Demo dashboard

A single screen assembling the same data for projector use, using the same hooks with no separate
logic. Optimise for legibility at distance: large text, high contrast, no dense tables.

### Error Handling

* Network failure → `ErrorState` with a retry, never a blank page.
* `ApiError` → the envelope's `message`.
* Unknown ID → a clear not-found state.
* A slow `verify` call → keep the loading state honest; on timeout or network failure, show
  `ErrorState` with retry. Never silently swallow it.
* Never a raw exception, stack trace, or `[object Object]` on screen.

---

# 8. Testing Requirements

## Automated Tests

`vitest` + React Testing Library:

**Wording — the most important tests in this file**
* `StatusBadge` renders the exact documented label for each of the six statuses.
* **Assert that "Verified", "Authentic", "Genuine", and "Valid" appear nowhere in any rendered
  output for any status.** A snapshot-wide string assertion. This is the wording contract made
  mechanical, and it is the thing most likely to regress under time pressure.
* `NO_TRUSTED_RECORD` renders text explicitly stating it is not evidence of a fake document.

**Structure**
* `SyntheticDataBanner` is present on every result-bearing page.
* Verification and blockchain badges render as separate elements — assert both exist independently.
* `FieldComparisonTable` renders every match field, including unmatched ones. A mismatch is never
  hidden behind a toggle.

**Data sourcing**
* The category form renders from the `GET /document-types` mock. Assert that changing the mock
  changes the form — which proves nothing is hardcoded.

**States**
* Every page renders loading, error, and empty states appropriately.
* A pending verification shows a progress indicator, never a blank screen.

**Review**
* The correction form pre-fills with extracted values.
* Original OCR and corrected values both render, visually distinguishable.
* Post-correction wording includes "(reviewer-corrected)".

**Errors**
* Each of `400`, `413`, `415`, `422` renders a distinct, useful message.
* A network failure renders `ErrorState` with retry.
* No raw exception text reaches the DOM.

**Blockchain**
* `FAILED` renders as failed, with no success styling.
* `NOT_REQUESTED` renders clearly when disabled.
* No placeholder or fabricated transaction hash exists anywhere in the codebase.

Run:

```bash
cd frontend && npm test
```

## Manual Verification

Against the mock server first, then the real backend:

1. Full flow: upload → detail → result → review → blockchain receipt.
2. Every status renders correctly and reads honestly.
3. Read every screen aloud as if presenting. Anything that sounds like an authenticity claim is a
   bug — this five-minute exercise catches more wording problems than any test.
4. Check on a projector or an external display at presentation resolution.
5. Confirm no console errors anywhere in the flow.
6. Against the real backend: confirm every response matches `docs/api.md`. **Report any difference
   to Task 10's owner; do not adapt the frontend.**

---

# 9. Acceptance Criteria

* [ ] All six pages and all components from `docs/frontend.md` implemented.
* [ ] Category fields render from `GET /document-types` — nothing hardcoded, proven by test.
* [ ] `StatusBadge` is the only status mapping; labels match `docs/verification-rules.md` exactly.
* [ ] **No "Verified", "Authentic", "Genuine", or "Valid" anywhere, for any status** — proven by test.
* [ ] `SyntheticDataBanner` on every result-bearing screen.
* [ ] Verification and blockchain badges always separate.
* [ ] `FieldComparisonTable` shows every match field; mismatches never hidden.
* [ ] Original OCR and corrected values both shown on review.
* [ ] Post-review wording includes "(reviewer-corrected)".
* [ ] Blockchain receipt explains what it proves **and what it does not**.
* [ ] A `FAILED` blockchain state renders its `error_code` in plain language, not a bare code.
* [ ] No fabricated transaction hash or optimistic `CONFIRMED` anywhere.
* [ ] Loading, error, and empty states on every page; no polling loop anywhere.
* [ ] Verification history comes from `GET /documents/{id}/verifications`; `is_current` is never computed client-side.
* [ ] All four upload error codes render distinct messages.
* [ ] No raw exception text on screen.
* [ ] `src/types/api.ts` mirrors `docs/api.md`.
* [ ] `npm test` passes.
* [ ] Full manual walkthrough against the real backend, no console errors.
* [ ] Any backend/`api.md` difference reported, not worked around.
* [ ] `git diff` reviewed; development log updated; branch pushed; PR prepared.

---

# 10. Known Risks

* **Wording drift.** "Verified" is the natural word and it is banned. It creeps in through button
  labels, page titles, toast messages, and `alt` text. The wide string assertion in §8 is the
  defence; write it early.
* **Hardcoding field lists during mock development.** Easy to do while the endpoint is mocked, easy
  to forget, and it breaks the single source of truth silently.
* **Merging the two badges for a cleaner design.** It looks better and it makes a false claim.
* **Hiding mismatches behind a "details" toggle.** Same instinct, same problem — the mismatch detail
  is the strongest thing you have.
* **Adapting to undocumented backend behaviour.** Feels helpful under deadline pressure; guarantees
  the contract and the implementation diverge permanently. Report instead.
* **Designing for a laptop screen.** Judges see a projector. Check early, not the night before.
* **Building a polling loop from habit.** The obvious pattern for an async-looking operation, and
  here it waits on a transition that never occurs. Read the processing-state contract first.
* **Optimistic UI.** Showing success before the backend confirms is the frontend version of claiming
  untested code works.

---

# 11. Open Questions

* **Visual design** (colours, typography, layout) is open within the constraint that status colours
  must not imply authenticity — avoid a reassuring green check for `VERIFIED_MATCH`; something
  neutral and informational fits the claim being made. Propose your palette to the project lead.
* **Whether `DemoDashboardPage` is the primary demo view or a fallback** is the lead's call
  (`docs/deployment-demo.md`). Build it either way.

---

# 12. Handoff Notes

* Report every backend/`api.md` difference to Task 10's owner **as you find it**, not at the end.
* Tell Task 12 which screens are demo-ready and which need the real backend.
* Note the mock-server mode switch — it is useful during rehearsal for showing awkward states.
* Record any UI string not directly traceable to a doc, so the lead can approve or replace it.
* Flag any screen that reads poorly on a projector.

---

# 13. Definition of Done

```text
All pages and components implemented
        +
Tests passing (including the wording assertions)
        +
Manual walkthrough against the real backend, no console errors
        +
Projector legibility verified
        +
Every screen read aloud and confirmed honest
        +
Scope verified (no backend or docs edits)
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

1. Read `AGENTS.md`, especially Rule 2.
2. Read `docs/frontend.md` completely — the hard rules are contracts.
3. Read `docs/api.md` completely — you are building against it, not against a running backend.
4. Read `docs/verification-rules.md` §"Status vocabulary" and `docs/glossary.md` §"Words we
   deliberately do not use".
5. Read this task file completely.
6. State your plan, including your mock-server strategy, before coding.

During implementation:

* **Never write "Verified", "Authentic", "Genuine", or "Valid" for any status.** Use the exact
  documented labels.
* **Never hardcode a category's field list.** Always `GET /document-types`.
* Keep verification and blockchain status as two separate badges, always.
* Never hide a mismatched field.
* Never fabricate a transaction hash or show optimistic success.
* Implement all three states on every page.
* Build against the mock first; integrate with the real backend last.

If the real backend differs from `docs/api.md`, **report it to Task 10's owner and stop** — do not
adapt the frontend to undocumented behaviour.

Before PR:

* Run `npm test` and report exact output.
* Walk the full flow against the real backend.
* Read every screen aloud and confirm nothing overclaims.
* Check legibility at projector resolution.
* Review `git diff` and `git status`; confirm no backend or docs changes.
* Update `logs/task-11-frontend.md`.
* Push and open the PR per `docs/git-workflow.md`.
