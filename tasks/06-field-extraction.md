# PS21 Task Specification

> **This file is a work order for the assigned developer and their AI coding agent.**
>
> Do not expand the scope without explicit approval from the project lead.

---

## Task Information

**Task:** `Category-specific field extraction`
**Task ID:** `06` (`docs/implementation-plan.md` step 6)
**Assigned To:** `Unassigned` (suggested: Member A)
**Branch:** `feature/task-06-extraction`
**Priority:** `Critical` — on the critical path; blocks Task 07
**Status:** `Not Started`

---

# 1. Goal

## Objective

Map `OcrResult` onto the four category schemas in `docs/category-schemas.md`, producing the
`extracted_fields` structure that `docs/api.md` specifies and Task 07 consumes.

Expected outcome: a clean academic-certificate fixture yields all six fields with plausible
confidence; a document missing a field yields `null` plus a `missing_field:<name>` warning; and
nothing is ever invented.

## Why This Exists

Step 6 of `docs/implementation-plan.md`. This is where unstructured text becomes structured data,
and it carries the project's most dangerous temptation.

When a schema declares six required fields and OCR produced five, there is enormous pull toward
filling in the sixth — from a nearby region, a pattern guess, a default. **Do not.** A fabricated
`student_id` that happens to match the registry produces a `VERIFIED_MATCH` that is entirely
fictional. `AGENTS.md` Rule 1 covers inventing contracts; this task extends it to inventing *data*.
A `null` with a warning is always correct. A guess is never correct, no matter how good.

---

# 2. Authoritative Documentation

* `AGENTS.md` — Rules 1, 5, 12
* `docs/category-schemas.md` — **authoritative**: field names, types, required flags, `match_field`
  flags, and the four fixtures
* `docs/document-processing.md` §"Extraction behavior" — **authoritative** for missing-field and
  confidence handling
* `docs/api.md` — `GET /documents/{id}/extraction` response shape and
  `GET /document-types`
* `docs/data-model.md` — `extraction_results.extracted_fields_json` structure
* `docs/backend.md` — `services/extraction_service.py`, `domain/schemas/`
* `docs/architecture.md` — `domain/` is pure; no FastAPI, PaddleOCR, or Web3 imports
* `docs/verification-rules.md` — how Task 07 consumes this output
* `docs/decisions.md` — D-06 (no LLM)
* `logs/task-05-ocr.md` — the published `OcrResult` shape

---

# 3. Scope

## In Scope

* `backend/app/domain/schemas/__init__.py` — a registry mapping category → schema definition, plus
  the loader that `GET /document-types` serves.
* `backend/app/domain/schemas/{academic_certificate,institutional_id,pan_like_demo,government_certificate}.py`
  — per-category field definitions, label patterns, and format validators.
* `backend/app/services/extraction_service.py` — maps `OcrResult` → `extracted_fields`, writes
  `extraction_results.extracted_fields_json` and warnings.
* `backend/app/api/document_types.py` — `GET /document-types` sourced from the schema registry.
* `GET /documents/{id}/extraction` per `docs/api.md`.
* `backend/tests/test_extraction.py`.

## Out of Scope

* Any comparison against the registry — **Task 07**. This task produces fields; it does not judge
  them.
* Any status assignment. `REVIEW_REQUIRED`, `VERIFIED_MATCH` and the rest belong to Task 07. This
  task's only status is `extraction_results.status` (`SUCCEEDED`/`FAILED`), which Task 05 already
  sets.
* Reading `LOW_CONFIDENCE_THRESHOLD` — Task 07's job.
* OCR itself — **Task 05**.
* Any LLM-assisted parsing (`docs/decisions.md` D-06).
* Adding, renaming, or removing a field — that is a `docs/category-schemas.md` change requiring
  project-lead approval.

---

# 4. Allowed Files / Areas

```text
backend/app/domain/schemas/__init__.py
backend/app/domain/schemas/academic_certificate.py
backend/app/domain/schemas/institutional_id.py
backend/app/domain/schemas/pan_like_demo.py
backend/app/domain/schemas/government_certificate.py
backend/app/services/extraction_service.py
backend/app/api/document_types.py
backend/tests/test_extraction.py               (new)
```

### May Modify If Required

```text
backend/app/api/documents.py    (add GET /documents/{id}/extraction only)
backend/app/main.py             (register the document_types router)
```

---

# 5. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Task 05 (`OcrResult`) | **Hard** | The input shape. Published in `logs/task-05-ocr.md` |
| Task 02 (`extraction_repo`) | **Hard** | Persistence |
| Task 03 (sample documents) | **Integration** | Validating that fixtures map cleanly |
| `docs/category-schemas.md` | **Contract** | Frozen |

### Dependency Status

* [x] Being developed alongside Task 05 (same owner)
* [x] Requires coordination: Task 07 consumes the `extracted_fields` shape; Task 11 consumes
      `GET /document-types`

### Parallel-development notes

Once `OcrResult` is published, this task can be built entirely against hand-constructed `OcrResult`
objects — no OCR run required. Start the moment Member A has the shape, even before Task 05 merges.

---

# 6. Contracts That Must Be Preserved

### Field names

**Exactly as `docs/category-schemas.md` lists them.** `semester_or_year`, not `semester`.
`certificate_or_marksheet_id`, not `marksheet_id`. `demo_pan_code`, not `pan_number`. Task 07
matches on these literally, Task 11 renders them, and the registry fixtures use them as JSON keys.

### `extracted_fields` shape (`docs/api.md`)

```json
{
  "student_name": { "value": "Aarav Demo", "confidence": 0.94, "source": "ocr" },
  "certificate_or_marksheet_id": { "value": null, "confidence": null, "source": "ocr" }
}
```

* `value` is `null` when not found — never `""`, never `"N/A"`, never omitted.
* `confidence` is `null` when `value` is `null`.
* `source` is `"ocr"` here. `"corrected"` is written only by Task 08.
* Every field in the category's schema appears as a key, found or not. A consumer must never have to
  distinguish "absent key" from "null value".

### Never invent (`AGENTS.md` Rule 1, extended to data)

* No inferred value, no pattern-generated default, no "probably this" from an adjacent region.
* No cross-field inference — do not derive `semester_or_year` from a course name.
* If a value fails its format validator, keep the extracted value, set the warning, and let Task 07
  decide. Do not silently coerce it into shape.

### Warnings

* `missing_field:<name>` for every required field with a `null` value.
* `unrecognized_date_format:<name>` when a date field is present but not `YYYY-MM-DD`
  (`docs/category-schemas.md`).
* `invalid_format:<name>` when a value fails its declared format validator.
* Warnings are strings in a list, appended to the existing `warnings_json` from Task 05, never
  replacing it.

### `demo_pan_code` format validator

Six characters. **Must reject** anything matching the real PAN pattern `^[A-Z]{5}[0-9]{4}[A-Z]$`
(`docs/category-schemas.md`). This is enforced in the validator, not left to convention — it is the
mechanism that prevents the demo from ever displaying something a viewer could mistake for a real
PAN number.

### Purity (`docs/architecture.md`)

`domain/schemas/` imports nothing from FastAPI, PaddleOCR, Web3, or SQLAlchemy. Plain data in,
plain data out. `extraction_service.py` is the layer that touches repositories.

### `GET /document-types`

Served **from the schema registry**, not from a hand-maintained copy. This is what keeps the frontend
in sync with `docs/category-schemas.md` automatically (`docs/frontend.md`, hard rule).

---

# 7. Implementation Requirements

### Requirement 1 — Schema definitions

Each category module declares its fields as data:

```python
FIELDS = [
    FieldDef(name="student_name", label="Student Name", type="text",
             required=True, match_field=True,
             labels=["student name", "name of student", "candidate name"]),
    ...
]
```

`labels` are the on-document text patterns the mapper looks for. Keep them a list — real documents
label the same field several ways, and a single hardcoded string is brittle.

### Requirement 2 — Label-based mapping

For each field: scan `OcrResult.regions` for a region whose text matches one of the field's labels
(case-insensitive, whitespace-tolerant), then take the value from the same region after the label,
or from the nearest region to the right or below. Assign that region's confidence to the field.

Be explicit about the strategy you implement and document it in the log. A simple, predictable
approach that fails visibly beats a clever one that fails silently.

### Requirement 3 — Not found means null

No label match, or a match with no adjacent value → `value: null`, `confidence: null`, and the
`missing_field` warning if required. This is the whole point of the task.

### Requirement 4 — Format validators

Per field type: `text` non-empty after trimming; `date` must be `YYYY-MM-DD` or it gets
`unrecognized_date_format`; `integer` must parse. Plus the `demo_pan_code` rule above. A validation
failure **preserves the extracted value** and adds a warning — never discards or coerces it, because
the reviewer needs to see what was actually read.

### Requirement 5 — Extraction service

`extract_fields(document_id, session) -> dict`:

1. Load the latest successful `extraction_results` for the document.
2. Load the schema for `documents.category`.
3. Map `OcrResult` (deserialised from `raw_ocr_json`) to fields.
4. Run validators, collect warnings.
5. Write `extracted_fields_json` and the merged `warnings_json`.

If the extraction row's `status` is `FAILED`, do nothing and return — Task 07 will produce
`PROCESSING_FAILED` (`docs/verification-rules.md` precedence step 1).

### Requirement 6 — Endpoints

`GET /document-types` returns the array in `docs/api.md`, built from the registry.
`GET /documents/{id}/extraction` returns the documented shape, including `404 DOCUMENT_NOT_FOUND`,
`409 EXTRACTION_NOT_READY` while `OCR_IN_PROGRESS`, and — importantly — a `200` with
`status: "FAILED"` when OCR failed. That last one is **not** a 4xx
(`docs/architecture.md` failure isolation).

### Error Handling

* Unknown category on the document row → `500 INTERNAL_ERROR`; it means the database holds a value
  the enum should have prevented.
* Malformed `raw_ocr_json` → extraction fails with a clear warning, not a crash.
* No successful extraction row → `409 EXTRACTION_NOT_READY`.
* A validator raising → caught, recorded as `invalid_format:<name>`; one bad field never aborts the
  whole mapping.

---

# 8. Testing Requirements

## Automated Tests

`backend/tests/test_extraction.py`, using hand-built `OcrResult` objects:

**Mapping**
* Clean academic-certificate `OcrResult` → all six fields populated with correct values and
  confidence carried from the source regions.
* Each of the other three categories maps its documented fields.
* Every schema field appears as a key even when `null`.

**Not found**
* `OcrResult` missing the `certificate_or_marksheet_id` label → that field `null`, confidence
  `null`, `missing_field:certificate_or_marksheet_id` in warnings.
* Empty `OcrResult` → every field `null`, one `missing_field` warning per required field.
* **Assert that no field acquired a value that does not appear in the source `OcrResult` text.**
  This is the anti-invention test and it is the most important one in the file.

**Validators**
* Date `15-01-1999` → value preserved, `unrecognized_date_format:date_of_birth` warning.
* Date `1999-01-15` → no warning.
* `demo_pan_code` of `"ABCDE1234F"` (real PAN shape) → `invalid_format:demo_pan_code`.
* `demo_pan_code` of `"DP1234"` → no warning.

**Schema registry**
* `GET /document-types` returns all four categories with fields matching
  `docs/category-schemas.md` exactly — assert against the literal expected structure.
* No category is missing a field, and no extra field appears.

**Endpoint**
* `GET /documents/{id}/extraction` → documented shape.
* Unknown ID → `404`.
* `OCR_IN_PROGRESS` → `409 EXTRACTION_NOT_READY`.
* OCR-failed document → **`200` with `status: "FAILED"`**, not a 4xx.

**Purity**
* Importing `domain/schemas/*` pulls in no FastAPI, SQLAlchemy, PaddleOCR, or Web3 module.

Run:

```bash
cd backend && pytest tests/test_extraction.py
```

## Manual Verification

1. With Task 05's integration test output, run extraction on the real `academic_certificate_match.png`
   OCR result. All six fields should populate. If they do not, the label patterns and the Task 03
   sample are out of sync — fix them together.
2. Run against `academic_certificate_degraded.png`. Record which fields come back low-confidence;
   Task 07 needs this.
3. `curl .../document-types` → compare against `docs/category-schemas.md` line by line.

---

# 9. Acceptance Criteria

* [ ] Four schema modules with field names exactly matching `docs/category-schemas.md`.
* [ ] `extracted_fields` matches the `docs/api.md` shape; every schema field present as a key.
* [ ] A not-found field is `null` with `null` confidence and a `missing_field` warning.
* [ ] **No value is ever invented, inferred, defaulted, or derived from another field.**
* [ ] Confidence is carried from the source region, unmodified.
* [ ] `source` is `"ocr"` for everything this task writes.
* [ ] Format validators produce warnings and preserve the extracted value.
* [ ] `demo_pan_code` rejects the real PAN pattern.
* [ ] `domain/schemas/` is pure — no framework, ORM, or engine imports.
* [ ] `GET /document-types` is served from the registry, not a copy.
* [ ] `GET /documents/{id}/extraction` returns `200` + `status: "FAILED"` for a failed OCR, not a 4xx.
* [ ] `LOW_CONFIDENCE_THRESHOLD` is not read anywhere in this task.
* [ ] Tests pass, including the anti-invention assertion.
* [ ] `git diff` reviewed; development log updated; branch pushed; PR prepared.

---

# 10. Known Risks

* **Invention under pressure.** When a fixture fails to map cleanly, the fastest fix looks like a
  fallback default. It is the worst possible fix. Fix the label patterns or the fixture.
* **Label patterns drifting from Task 03's samples.** The most likely functional bug here. Keep a
  test that asserts the real sample maps cleanly, and when it breaks, fix both sides together with
  Task 03's owner.
* **Regions out of reading order.** If Task 05 did not sort them, adjacency logic misbehaves
  unpredictably. Verify sorting before debugging your own mapper.
* **Over-engineering the mapper.** Fuzzy matching, edit distance, and layout inference all sound
  appealing and all fail in ways that are hard to explain on stage. Simple and predictable wins.
* **Silently dropping an invalid value.** The reviewer needs to see what OCR actually read in order
  to correct it. Preserve and warn.

---

# 11. Open Questions

* **The exact adjacency strategy** (same region after the label, versus nearest-right, versus
  nearest-below) is left to the implementer, because it depends on how Task 03's samples are laid
  out. Pick one, document it in the log, and keep it simple. If it proves inadequate on real
  samples, that is a conversation with Task 03's owner about layout, not a reason to add inference.
* If a real sample needs a label pattern not currently in the schema module, adding it to the
  `labels` list is in scope. Adding a new *field* is not.

---

# 12. Handoff Notes

* **Publish the `extracted_fields` shape in the log.** Task 07 builds matching directly against it,
  and Task 08 writes `source: "corrected"` entries into it.
* Tell Member B (Task 07) which fields come back low-confidence on the degraded sample.
* Tell Member D (Task 11) that `GET /document-types` is live, so the frontend can stop mocking it.
* Record the adjacency strategy you chose and why.
* Note any Task 03 sample that needed a layout change, so it is not "fixed" back later.

---

# 13. Definition of Done

```text
Implementation complete
        +
Tests passing (including the anti-invention assertion)
        +
Real sample verified to map cleanly
        +
Scope verified (no comparison, no status, no threshold)
        +
Git diff reviewed
        +
Development log updated with the extracted_fields shape
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
2. Read `docs/category-schemas.md` **completely** — field names are literal contracts.
3. Read `docs/document-processing.md` §"Extraction behavior".
4. Read `logs/task-05-ocr.md` for the `OcrResult` shape.
5. Read this task file completely.
6. State your plan, including the adjacency strategy, before coding.

During implementation:

* **Never invent a field value.** Not a default, not a guess, not an inference from another field.
  `null` plus a warning is always the correct answer when OCR did not produce evidence.
* Copy field names exactly from `docs/category-schemas.md`.
* Every schema field appears as a key, found or not.
* Preserve invalid values and warn; never coerce or discard.
* Keep `domain/schemas/` pure.
* Do not read `LOW_CONFIDENCE_THRESHOLD` or assign any verification status.
* Test incrementally, starting with the not-found cases.

If a sample document will not map cleanly, **fix the label patterns or coordinate a layout change
with Task 03's owner**. Do not add a fallback.

Before PR:

* Run the tests and report exact output.
* Verify a real sample maps cleanly end to end.
* Review `git diff` and `git status`.
* Update `logs/task-06-extraction.md` with the published shape and your adjacency strategy.
* Push and open the PR per `docs/git-workflow.md`.
