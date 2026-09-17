# PS21 Task Specification

> **This file is a work order for the assigned developer and their AI coding agent.**
>
> Do not expand the scope without explicit approval from the project lead.

---

## Task Information

**Task:** `Synthetic registry and seed fixtures`
**Task ID:** `03` (`docs/implementation-plan.md` step 3)
**Assigned To:** `Unassigned` (suggested: Member C)
**Branch:** `feature/task-03-registry`
**Priority:** `High` — Task 07 cannot be tested without it; the demo cannot run without it
**Status:** `Not Started`

---

# 1. Goal

## Objective

Implement `seed_registry.py`, which idempotently populates `registry_records` with the four locked
fixtures from `docs/category-schemas.md`, and produce the synthetic sample documents in
`backend/app/fixtures/sample_documents/` that the demo and the test suite both depend on.

Expected outcome: `python -m app.fixtures.seed_registry` on a fresh database creates exactly four
active registry records; running it again changes nothing; and `sample_documents/` contains, per
category, a matching document, a mismatching document, plus the two special cases the demo needs —
an unregistered document and a degraded scan.

## Why This Exists

Step 3 of `docs/implementation-plan.md`. This task produces the **reference data the entire
verification story is told against**, and the **five documents the demo actually shows**. Task 07
cannot be meaningfully tested without it, and Task 12's rehearsal is impossible without it.

It also carries this project's sharpest ethical line. `AGENTS.md` Rule 7 exists mostly because of
this task: the temptation to grab a teammate's real marksheet "just as a test file" is real, and the
answer is no — not once, not temporarily, not with a note to remove it later.

---

# 2. Authoritative Documentation

* `AGENTS.md` — Rules 2, 7 (no real data), 4 (no record ≠ forged)
* `docs/category-schemas.md` — **authoritative**: the four schemas and the four exact fixtures
* `docs/data-model.md` — `registry_records` columns; `source_label` is always `"synthetic-demo"`
* `docs/workflow.md` Stage 0 — the do/don't list this task implements
* `docs/verification-rules.md` — matching, so the fixtures exercise every status
* `docs/security-privacy.md` — synthetic-data policy
* `docs/testing.md` — required scenarios the fixtures must support
* `docs/deployment-demo.md` — the demo run these documents feed
* `docs/backend.md` — `fixtures/` layout

---

# 3. Scope

## In Scope

* `backend/app/fixtures/seed_registry.py` — idempotent seeding of the four fixtures in
  `docs/category-schemas.md`, runnable as `python -m app.fixtures.seed_registry`.
* `backend/app/fixtures/sample_documents/` — generated synthetic documents (see §7 Requirement 3 for
  the exact file list).
* `backend/app/fixtures/generate_samples.py` — the script that renders those documents
  programmatically from the fixture values, so they can be regenerated and can never drift from the
  registry.
* `backend/tests/test_seed_registry.py`.
* A short `backend/app/fixtures/README.md` explaining what each sample document demonstrates.

## Out of Scope

* Matching or comparison logic — **Task 07**.
* OCR — **Task 05**. This task produces images; it does not read them.
* Any fifth category or extra fixture per category beyond §7 — that would be a
  `docs/category-schemas.md` change requiring project-lead approval.
* The retention cleanup script — **Task 12**.
* An admin UI for managing registry records — not in MVP scope.

---

# 4. Allowed Files / Areas

```text
backend/app/fixtures/seed_registry.py
backend/app/fixtures/generate_samples.py
backend/app/fixtures/sample_documents/*        (generated assets)
backend/app/fixtures/README.md
backend/tests/test_seed_registry.py            (new)
```

### May Modify If Required

```text
backend/requirements.txt   (Pillow, if Task 01 did not already include it)
```

---

# 5. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Task 02 (`registry_records` model + `registry_repo`) | **Hard** | Seeding writes through the repository |
| `docs/category-schemas.md` | **Contract** | Frozen. The fixture values are literally specified |
| Pillow | **Hard (library)** | Rendering sample documents |

### Dependency Status

* [x] Dependency exists and is ready (once Task 02 merges)
* [x] Requires coordination: Task 05 and Task 06 consume the sample documents

### Parallel-development notes

`generate_samples.py` needs nothing but Pillow, so the sample documents can be built while Task 02 is
still in flight. Only `seed_registry.py` waits on the repository layer.

---

# 6. Contracts That Must Be Preserved

### Fixture values

**Character for character from `docs/category-schemas.md`.** `"Aarav Demo"`, `"DEMO-STU-001"`,
`"B.Tech CSE"`, `"5"`, `"DEMO-MARK-001"` — and the equivalents for the other three categories. A
changed space or a changed case here breaks Task 07's tests and the demo simultaneously, in a way
that looks like a matching bug rather than a seeding bug.

The rendered sample document must contain **exactly** the same values, which is why it is generated
from the same source constants rather than hand-made.

### Synthetic data policy (`AGENTS.md` Rule 7)

* Every identifier is `DEMO-` prefixed or an obviously fictional name.
* `demo_pan_code` values are **6 characters**, and must never match the real 10-character PAN pattern
  `AAAAA9999A`. `docs/category-schemas.md` fixes `"DP1234"`.
* No real person's name, no real institution's name (`"Example Technical Institute"` is deliberately
  generic), no real certificate number, no real date of birth.
* `source_label` is always `"synthetic-demo"`. It is never changed to anything that could read as
  authoritative.
* No sample document carries a government emblem, a real institutional logo, or a real seal.

### Data model

* `registry_records.active` defaults `true`; inactive records are excluded from matching
  (`docs/verification-rules.md`).
* `synthetic_record_key` is unique per category — this is what makes seeding idempotent.
* `fields_json` contains exactly the fields `docs/category-schemas.md` lists for that fixture, and
  no others.

---

# 7. Implementation Requirements

### Requirement 1 — Fixture constants in one place

Define the four fixtures once, as module-level constants, and have both `seed_registry.py` and
`generate_samples.py` import them. Two hand-maintained copies will diverge — and when they do, the
symptom appears in Task 07 as an unexplained mismatch.

### Requirement 2 — Idempotent seeding

For each fixture: look up by `(category, synthetic_record_key)`; create if absent; if present and
identical, do nothing; if present and different, **report the difference and do not overwrite** — a
divergence means someone edited data by hand, and silently reverting it would hide that.

Print a clear summary: created / unchanged / divergent, per record. A demo operator running this an
hour before presenting needs to see at a glance that the registry is correct.

### Requirement 3 — Sample documents

`generate_samples.py` renders simple, legible, printed-text documents with Pillow — a title, then
labelled field rows. Clean, high-contrast, OCR-friendly. Required output:

```text
academic_certificate_match.png          exactly the DEMO-STU-001 values          → VERIFIED_MATCH
academic_certificate_mismatch.png       same, but semester_or_year = "6"         → INTEGRITY_MISMATCH
academic_certificate_unregistered.png   student_id = "DEMO-STU-999", not seeded  → NO_TRUSTED_RECORD
academic_certificate_degraded.png       the match doc, blurred + low contrast    → REVIEW_REQUIRED
institutional_id_match.png              exactly the DEMO-ID-001 values
institutional_id_mismatch.png           holder_name differs
pan_like_demo_match.png                 exactly the DEMO-PAN-001 values
pan_like_demo_mismatch.png              date_of_birth differs
government_certificate_match.png        exactly the DEMO-GOV-001 values
government_certificate_mismatch.png     issuing_authority_label differs
academic_certificate_match.pdf          the match document as a single-page PDF  → exercises the PDF path
```

Eleven files. The four `academic_certificate_*` variants carry the demo narrative (`docs/workflow.md`,
`docs/judging-and-pitch.md` §3), which is why that category gets the full set.

The degraded variant needs care: blurred enough that per-field confidence lands below
`LOW_CONFIDENCE_THRESHOLD` (0.70), but still visibly a document. Tune it once real OCR runs in Task
05, and record the parameters you settled on in the log.

### Requirement 4 — Every sample is visibly demo data

Each rendered document carries a footer line: `SYNTHETIC DEMO DOCUMENT — NOT A REAL CERTIFICATE`.
It should be legible to a judge looking at a projector. This is not decoration; it is the same
honesty commitment the UI banner enforces (`NFR-08`).

### Requirement 5 — Fixture README

`backend/app/fixtures/README.md`: one line per sample document stating which status it is expected
to produce and why. This is what the demo operator reads under pressure.

### Error Handling

* Database unavailable → seeding fails loudly with a clear message. Never a partial silent seed.
* A divergent existing record → report and skip; exit non-zero so a script wrapper notices.
* `sample_documents/` missing → create it.
* Re-running `generate_samples.py` overwrites deterministically — identical inputs, identical output.

---

# 8. Testing Requirements

## Automated Tests

`backend/tests/test_seed_registry.py`, against the temp-DB fixture from Task 02:

* Fresh database → seeding creates exactly four active records.
* Running it a second time → still exactly four; nothing duplicated, nothing modified.
* Each record's `fields_json` matches `docs/category-schemas.md` **exactly** — assert against the
  literal expected dict, not against the same constant the seeder used, or the test proves nothing.
* `source_label == "synthetic-demo"` on every record.
* `active is True` on every record.
* Every `synthetic_record_key` starts with `DEMO-`.
* `demo_pan_code` is 6 characters and does not match `^[A-Z]{5}[0-9]{4}[A-Z]$` — a direct assertion
  against the real PAN pattern, so nobody can weaken this by accident.
* A divergent pre-existing record is reported and not overwritten.
* Every file listed in §7 Requirement 3 exists in `sample_documents/`.

Run:

```bash
cd backend && pytest tests/test_seed_registry.py
```

## Manual Verification

1. Delete `data/app.db`, start the backend, run `python -m app.fixtures.seed_registry` → four records
   created, summary printed.
2. Run it again → "unchanged" for all four, nothing duplicated.
3. `python -m app.fixtures.generate_samples` → all eleven files appear.
4. Open each one. Confirm it is legible, the footer disclaimer is visible, and the values match the
   fixture.
5. Open the degraded variant. Confirm it looks plausibly like a bad phone photo rather than noise.
6. Search every generated file and the seed script for anything resembling real personal data. There
   must be none.

---

# 9. Acceptance Criteria

* [ ] Fixture values are defined once and shared between seeding and generation.
* [ ] `seed_registry.py` is idempotent and reports created/unchanged/divergent.
* [ ] A divergent record is reported, never silently overwritten.
* [ ] All four `docs/category-schemas.md` fixtures seed with exactly the documented values.
* [ ] `source_label` is `"synthetic-demo"` and `active` is `true` everywhere.
* [ ] All eleven sample documents from §7 exist and are legible.
* [ ] `demo_pan_code` is 6 characters and provably does not match the real PAN pattern.
* [ ] Every sample document carries the visible synthetic-demo footer.
* [ ] No real personal data, real institution name, real identifier, or real emblem anywhere.
* [ ] `backend/app/fixtures/README.md` maps each sample to its expected status.
* [ ] Tests pass.
* [ ] `git diff` reviewed; development log updated; branch pushed; PR prepared.

---

# 10. Known Risks

* **Registry values and rendered documents drifting apart.** The most likely bug in this task, and it
  surfaces in Task 07 as a mysterious matching failure. Requirement 1 exists to make it impossible.
* **The degraded sample being wrong in either direction.** Too clean and OCR reads it fine, so
  `REVIEW_REQUIRED` never triggers and the most interesting demo scenario is lost. Too degraded and
  OCR returns nothing, producing `no_text_detected` instead. It needs tuning against real OCR once
  Task 05 exists — budget a second pass and say so in the log.
* **"Just this once" real data.** Absolute prohibition (`AGENTS.md` Rule 7). If someone needs a
  realistic layout, render a realistic *layout* with fictional *values*.
* **Overly artistic sample documents.** Fancy fonts, watermarks, and background textures hurt OCR.
  Plain, high-contrast, boring documents are correct here.
* **Committing large binaries.** Keep each PNG small (a few hundred KB at most).

---

# 11. Open Questions

* **Degraded-sample parameters** (blur radius, contrast reduction, noise) cannot be finalised until
  real PaddleOCR runs in Task 05. Ship a reasonable first attempt, then tune with Member A once Task
  05 lands, and record the final values in the log. This is expected iteration, not a blocker.
* If any category needs a second mismatching variant to demonstrate a specific rule, that is a
  project-lead decision — propose it rather than adding it.

---

# 12. Handoff Notes

* Publish in the log: the exact sample filenames, and which status each is expected to produce.
* Task 05 uses `academic_certificate_match.png` for its integration test and
  `academic_certificate_degraded.png` for low-confidence behaviour.
* Task 06 uses the match samples to validate field mapping.
* Task 07 needs the seeded registry plus match, mismatch, and unregistered samples to cover every
  status.
* Task 12 uses all eleven in the rehearsal.
* Flag to Member A that the degraded sample will likely need one tuning pass together.

---

# 13. Definition of Done

```text
Implementation complete
        +
Tests passing
        +
All eleven samples generated and visually inspected
        +
No real personal data anywhere
        +
Scope verified
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

1. Read `AGENTS.md`, especially Rule 7.
2. Read `docs/category-schemas.md` completely — the fixture values are specified literally.
3. Read `docs/workflow.md` Stage 0.
4. Read this task file completely.
5. State your plan, including the fixture constants and the sample file list, before coding.

During implementation:

* Copy fixture values exactly. One space or one case difference breaks Task 07 and the demo.
* Define values once; import them in both scripts.
* **Never use real personal data, a real identifier, a real institution name, or a real emblem.**
  Not as a placeholder, not temporarily, not with a TODO.
* Keep sample documents plain and high-contrast. Optimise for OCR, not for looks.
* Test incrementally.

If a fixture value in `docs/category-schemas.md` looks wrong, **stop and ask the project lead** —
Task 07's tests are written against those exact values.

Before PR:

* Run the tests and report exact output.
* Visually open all eleven samples.
* Grep your own diff for anything that could be real data.
* Review `git diff` and `git status`.
* Update `logs/task-03-registry.md`.
* Push and open the PR per `docs/git-workflow.md`.
