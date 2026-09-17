# PS21 Task Specification

> **This file is a work order for the assigned developer and their AI coding agent.**
>
> Do not expand the scope without explicit approval from the project lead.

---

## Task Information

**Task:** `End-to-end tests, demo rehearsal, and handoff`
**Task ID:** `12` (`docs/implementation-plan.md` step 12)
**Assigned To:** `Unassigned` (project lead — this is the lead's task)
**Branch:** `feature/task-12-e2e`
**Priority:** `Critical` — this is the task that converts a working project into a winning demo
**Status:** `Not Started`

---

# 1. Goal

## Objective

Verify every required scenario in `docs/testing.md` against the fully integrated system, implement
the retention cleanup script `docs/data-model.md` promises, rehearse `docs/deployment-demo.md` end
to end from a clean checkout, and produce the fallback materials that make the demo survive
a laptop failure.

Expected outcome: every scenario passes from a clean checkout; the demo runs start to finish without
improvisation; and if the worst happens on stage, a recording and screenshots carry the presentation.

## Why This Exists

Step 12 of `docs/implementation-plan.md`. **Everything up to here built the system. This task makes
it demonstrable.**

Hackathon projects fail on stage for reasons that have nothing to do with code quality: a stale
contract address, a database seeded three days ago that has since drifted, an OCR model that was
never downloaded on the presenting laptop, a startup order nobody wrote down. Every one of those is
preventable by doing the run once, deliberately, from nothing.

There is also one genuine implementation deliverable here. `docs/data-model.md` §"Retention"
promises `cleanup_expired.py`, and no earlier task builds it. Shipping documentation that describes
a script that does not exist is exactly the kind of gap a thorough judge finds.

---

# 2. Authoritative Documentation

* `AGENTS.md` — Rule 12 above all; this task is where unverified claims become visible failures
* `docs/testing.md` — **authoritative**: the required scenarios
* `docs/deployment-demo.md` — **authoritative**: startup order and the demo script
* `docs/judging-and-pitch.md` — the narrative, the wording table, and the presentation checklist
* `docs/data-model.md` §"Retention" — the cleanup script's specification
* `docs/troubleshooting.md` — demo-day emergencies; extend it with whatever you hit
* `docs/setup.md` — the clean-checkout path being verified
* `docs/requirements.md` §"Acceptance criteria (system-level)" — the bar
* Every `logs/task-NN-*.md` — expected outcomes recorded by each task

---

# 3. Scope

## In Scope

* `backend/app/fixtures/cleanup_expired.py` — the retention script from `docs/data-model.md`.
* `backend/tests/test_cleanup.py`.
* `backend/tests/test_e2e_scenarios.py` — automated coverage of every `docs/testing.md` required
  scenario, using fakes so it runs in CI-like conditions.
* A **clean-checkout verification run**: fresh clone, follow `docs/setup.md` verbatim, record every
  point where reality diverges from the document, and fix the document.
* A **full demo rehearsal** following `docs/deployment-demo.md`, timed.
* Fallback materials: a screen recording of a successful run, and screenshots of every key screen.
* `docs/DEMO-CHECKLIST.md` — a single printable page for demo day.
* Corrections to `docs/setup.md`, `docs/deployment-demo.md`, and `docs/troubleshooting.md` wherever
  the rehearsal proves them wrong.
* A final documentation consistency pass (§7 Requirement 6).

## Out of Scope

* New features of any kind. If something is missing, it is a decision for the project lead about
  scope, not something to add here under deadline pressure.
* Fixing bugs in another task's module — **report to its owner**. If the owner is unavailable and
  the bug is demo-blocking, the lead decides and the fix ships as a **separate, clearly-labelled**
  commit, never buried in this branch's diff.
* Performance optimisation beyond confirming `NFR-09`.
* Redesigning the UI.
* Rewriting a contract document to match observed behaviour — that needs an explicit decision, not a
  quiet edit.

---

# 4. Allowed Files / Areas

```text
backend/app/fixtures/cleanup_expired.py
backend/tests/test_cleanup.py            (new)
backend/tests/test_e2e_scenarios.py      (new)
docs/DEMO-CHECKLIST.md                   (new)
docs/setup.md                            (corrections from the clean-checkout run)
docs/deployment-demo.md                  (corrections from the rehearsal)
docs/troubleshooting.md                  (additions from what actually went wrong)
demo/                                    (recording, screenshots, staged fixture files)
```

### May Modify Only With Project-Lead Approval

```text
Anything under backend/app/ other than fixtures/cleanup_expired.py
frontend/**
```

---

# 5. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Task 10 (integrated backend) | **Hard** | Nothing to verify otherwise |
| Task 11 (frontend) | **Hard** | The demo is the UI |
| Task 03 (all eleven samples) | **Hard** | The scenarios |
| A machine that runs real PaddleOCR and Hardhat | **Hard (environment)** | Must be the presenting machine |

### Dependency Status

* [ ] Dependencies exist and are ready
* [x] Being developed separately (Tasks 10, 11)
* [x] External dependency: the demo machine must have OCR weights downloaded **before** demo day

### Parallel-development notes

`cleanup_expired.py` and `test_e2e_scenarios.py` can be written against the contracts before Tasks 10
and 11 finish. `docs/DEMO-CHECKLIST.md` can be drafted from `docs/deployment-demo.md` at any time.
Only the rehearsal itself needs everything merged — and it needs to happen **more than once**, so
schedule the first pass earlier than feels necessary.

---

# 6. Contracts That Must Be Preserved

### Nothing new ships here

This task verifies. Every temptation to add "one small thing" at this stage is a temptation to ship
something untested into the demo. `AGENTS.md` Rule 12 is the governing rule for the whole task.

### Cleanup script (`docs/data-model.md` §"Retention")

* Deletes uploaded files older than `RETENTION_DAYS` (default 7) and **blanks**
  `extraction_results.raw_ocr_json`.
* **Preserves** `extracted_fields_json` and every `verification_results`, `review_actions`, and
  `blockchain_records` row. The audit trail outlives the raw data — that is the entire point of
  having a retention policy rather than a delete button.
* **Never** touches synthetic registry rows or demo fixtures — they are exempt.
* Never deletes on-chain data. It cannot, and must not pretend to.
* Dry-run mode by default; deletion requires an explicit flag. A retention script that deletes on
  first invocation, in a repository someone might run casually, is a foot-gun.

### Documentation corrections

Where the rehearsal proves a document wrong, **the document is corrected**. Where a document
describes intended behaviour the code does not implement, that is a **bug report to the owner**, not
a documentation edit. The distinction matters: quietly rewriting `docs/api.md` to match a bug means
the bug is now the specification.

### Honest reporting

The rehearsal report states what actually happened, including what failed. A rehearsal that only
records successes is worthless — the failures are the reason for rehearsing.

---

# 7. Implementation Requirements

### Requirement 1 — Cleanup script

`python -m app.fixtures.cleanup_expired [--delete]`:

1. Find `documents` older than `RETENTION_DAYS`.
2. Exclude anything referenced as a demo fixture.
3. For each: delete the file under `UPLOAD_DIR` (via Task 04's `safe_upload_path()`) and blank
   `raw_ocr_json`.
4. Leave every other row untouched.
5. Print a summary: counts, bytes freed, rows affected.
6. Without `--delete`, report what *would* happen and change nothing.

### Requirement 2 — Automated scenario tests

`backend/tests/test_e2e_scenarios.py` covers every `docs/testing.md` required scenario and every
`docs/requirements.md` system-level acceptance criterion, using fake adapters:

* Matching fixture → `VERIFIED_MATCH`, all required fields shown matched.
* Unsupported/corrupt file rejected **before** any OCR or verification runs.
* No registry record → `NO_TRUSTED_RECORD`, and the response contains nothing implying forgery.
* Wrong field → `INTEGRITY_MISMATCH` naming the field with expected and observed values.
* Degraded scan → `REVIEW_REQUIRED`; correction saved separately from the original; re-verification
  updates status while preserving history.
* Chain stopped → verification status unchanged; blockchain shows `FAILED` or `PENDING`.
* **No blockchain payload contains a document, raw OCR text, or an identity field value** — assert
  directly against the submitted arguments.
* The whole suite passes with no live external dependency.

### Requirement 3 — Clean-checkout verification

On a machine that has never run this project — or after deleting `venv/`, `node_modules/`, `data/`,
and `.env`:

1. Clone fresh.
2. Follow `docs/setup.md` **exactly as written**, changing nothing and improvising nothing.
3. **Record every divergence**: a missing step, a wrong command, an undocumented prerequisite, an
   unmentioned error.
4. Fix `docs/setup.md` so the next person does not hit any of them.
5. Repeat until a clean run works with zero improvisation.

Doing this honestly is uncomfortable and it is the single highest-value hour in this task.

### Requirement 4 — Demo rehearsal

Following `docs/deployment-demo.md` exactly:

1. Start the Hardhat node.
2. Deploy the contract; record the address.
3. Update `.env`; start the backend.
4. Seed the registry; confirm four records.
5. Start the frontend.
6. Walk all five scenarios (`docs/judging-and-pitch.md` §3).
7. Kill the chain node mid-flow and confirm isolation.
8. **Time the whole thing.**

Then correct `docs/deployment-demo.md` wherever it was wrong, and rehearse again. **At least twice**,
and the second pass must be clean.

### Requirement 5 — Fallback materials

* A screen recording of a complete successful run, all five scenarios, with narration.
* Screenshots of every key screen at presentation resolution.
* Fixture files staged in an obvious folder — nobody hunts for a file on stage.
* All of it on the presenting laptop **and** somewhere else.

A laptop that will not boot is not a hypothetical, and a recording turns a catastrophe into an
inconvenience.

### Requirement 6 — Documentation consistency pass

Verify, across the whole set:

* Every status name in the docs matches `docs/verification-rules.md`.
* Every field name matches `docs/category-schemas.md`.
* Every endpoint matches `docs/api.md`.
* Every environment variable matches `docs/configuration.md`.
* Every decision referenced as resolved actually has a `D-NN` entry.
* No document references a file that does not exist.
* No document still says "to be decided" about something that has been decided.

### Requirement 7 — `docs/DEMO-CHECKLIST.md`

One printable page: the startup sequence with exact commands, the five scenarios in order with their
expected statuses, the wording reminders from `docs/judging-and-pitch.md` §4, and the emergency
table from `docs/troubleshooting.md` §7. This is what sits next to the laptop.

---

# 8. Testing Requirements

## Automated Tests

`backend/tests/test_cleanup.py`:
* A document older than `RETENTION_DAYS` → file deleted, `raw_ocr_json` blanked.
* A recent document → untouched.
* `extracted_fields_json` and all verification/review/blockchain rows **survive** cleanup.
* Registry rows and demo fixtures are never touched.
* Without `--delete`, nothing changes and a report is printed.
* A missing file on disk is handled without crashing.

`backend/tests/test_e2e_scenarios.py` — as specified in §7 Requirement 2.

Run the **entire** suite:

```bash
cd backend && pytest
cd frontend && npm test
cd chain && npx hardhat test
```

All three, green, from a clean checkout.

## Manual Verification

1. Clean-checkout run per §7 Requirement 3 — zero improvisation.
2. Two full rehearsals per §7 Requirement 4 — the second one clean.
3. Chain-down isolation confirmed live.
4. Single-page timing recorded against `NFR-09`.
5. Every screen read aloud; nothing overclaims.
6. Fallback materials verified to open on another machine.
7. Documentation consistency pass complete.

## The rehearsal report

Record in `logs/task-12-e2e.md`:

* Date, machine, and who ran it
* Wall-clock time from cold start to first scenario
* Each scenario, with its actual result
* **Everything that went wrong**, and whether it was fixed or worked around
* Documents corrected, and how
* Remaining risks for demo day

---

# 9. Acceptance Criteria

* [ ] `cleanup_expired.py` implemented per `docs/data-model.md`, dry-run by default.
* [ ] Cleanup preserves `extracted_fields_json` and all audit rows; never touches fixtures.
* [ ] `test_e2e_scenarios.py` covers every `docs/testing.md` scenario and every
      `docs/requirements.md` acceptance criterion.
* [ ] **Asserted: no blockchain payload contains a document, OCR text, or identity field value.**
* [ ] All three suites pass from a clean checkout.
* [ ] Clean-checkout run completed with zero improvisation; `docs/setup.md` corrected.
* [ ] **Two full rehearsals completed; the second one clean.**
* [ ] All five scenarios verified live with real OCR and a real chain.
* [ ] Chain-down isolation verified live.
* [ ] Timing recorded against `NFR-09`.
* [ ] Screen recording and screenshots produced and stored in two places.
* [ ] Fixture files staged.
* [ ] `docs/DEMO-CHECKLIST.md` written and printed.
* [ ] Documentation consistency pass complete; every inconsistency fixed or logged.
* [ ] `docs/troubleshooting.md` extended with whatever actually went wrong.
* [ ] Rehearsal report in `logs/task-12-e2e.md`, including failures.
* [ ] **No new feature was added during this task.**
* [ ] `git diff` reviewed; branch pushed; PR prepared.

---

# 10. Known Risks

* **Discovering a real bug late.** Likely, and the whole reason this task exists. The lead decides:
  fix it, or cut the scenario from the demo. Both are legitimate. Silently hoping it does not happen
  on stage is not.
* **Rehearsing on the wrong machine.** Rehearsing on a dev laptop and presenting on another means
  rehearsing nothing. The presenting machine must have OCR weights, Node, and a working `.env`.
* **Stale local state.** A database seeded days ago has drifted. Always start from a fresh database
  and a fresh seed. This is the most common cause of a fixture that "worked yesterday".
* **Contract address drift.** Hardhat resets on restart. The `.env` address goes stale every single
  time. It is on the checklist for a reason.
* **Rehearsing once.** The first rehearsal always finds problems. The second proves the fixes
  worked. One rehearsal proves nothing.
* **Scope creep under pressure.** "While I'm in here" is how untested code enters a demo.
* **Fixing documentation to match a bug.** That makes the bug the specification. Report it instead.

---

# 11. Open Questions

* **If a scenario cannot be made to work in time**, the lead decides whether to cut it from the demo
  or delay. Cutting a scenario and saying so honestly is far better than attempting it live and
  failing. Record the decision.
* **Who presents which section** is the lead's call. Everyone presenting must have read
  `docs/judging-and-pitch.md` §4.
* **Whether to demo with the real chain or the fake adapter** — real is much stronger and worth the
  risk, given that chain failure is itself a demonstrable feature. The lead confirms.

---

# 12. Handoff Notes

* The rehearsal report is the single most useful artifact this task produces. Write it honestly.
* Give every presenter `docs/DEMO-CHECKLIST.md` and `docs/judging-and-pitch.md` at least a day ahead.
* Tell each task owner what you found in their area, with reproductions.
* Note anything deferred, so the lead can decide whether to mention it proactively in the pitch —
  which, per `docs/judging-and-pitch.md` §7, is usually the stronger move.
* Confirm in writing which machine presents and that it is fully provisioned.

---

# 13. Definition of Done

```text
Cleanup script implemented and tested
        +
All scenario tests passing
        +
All three suites green from a clean checkout
        +
Clean-checkout run completed with zero improvisation
        +
Two rehearsals completed, second one clean
        +
Fallback materials produced and stored in two places
        +
DEMO-CHECKLIST.md written and printed
        +
Documentation consistency pass complete
        +
Rehearsal report written, including failures
        +
No new features added
        +
Git diff reviewed
        +
Branch pushed
        ↓
PR ready — and the team is ready to present
```

---

## Final Agent Instruction

Before making changes:

1. Read `AGENTS.md`, especially Rule 12.
2. Read `docs/testing.md`, `docs/deployment-demo.md`, and `docs/judging-and-pitch.md` completely.
3. Read `docs/data-model.md` §"Retention" for the cleanup specification.
4. Read every `logs/task-NN-*.md` for expected outcomes.
5. Read this task file completely.
6. State your plan before coding.

During implementation:

* **Add no new features.** This task verifies. If something is missing, that is a scope decision for
  the project lead.
* Fix no other task's module. Report with a reproduction.
* Correct a document when the rehearsal proves it wrong. **Never** rewrite a contract document to
  match a bug.
* Follow `docs/setup.md` and `docs/deployment-demo.md` **literally** during verification — improvising
  defeats the purpose entirely.
* Record what fails. A rehearsal report listing only successes is worthless.
* Make the cleanup script dry-run by default.

If a demo-blocking bug appears, **stop and escalate to the project lead** with a reproduction.

Before PR:

* Run all three suites from a clean checkout and report exact output.
* Confirm both rehearsals are complete and the second was clean.
* Confirm fallback materials exist in two places.
* Confirm `docs/DEMO-CHECKLIST.md` is printed.
* Review `git diff` and `git status`; confirm no feature crept in.
* Write the rehearsal report in `logs/task-12-e2e.md`.
* Push and open the PR per `docs/git-workflow.md`.
