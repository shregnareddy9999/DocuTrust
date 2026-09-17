# PS21 Task Specification

> **This file is a work order for the assigned developer and their AI coding agent.**
>
> Do not expand the scope without explicit approval from the project lead.

---

## Task Information

**Task:** `PaddleOCR adapter and preprocessing`
**Task ID:** `05` (`docs/implementation-plan.md` step 5)
**Assigned To:** `Unassigned` (suggested: Member A)
**Branch:** `feature/task-05-ocr`
**Priority:** `Critical` — on the critical path; blocks Task 06
**Status:** `Not Started`

---

# 1. Goal

## Objective

Implement the preprocessing and OCR pipeline exactly per `docs/document-processing.md` steps 1–8:
PDF page rendering, conservative image preprocessing, PaddleOCR behind a swappable adapter
interface, and the normalized `OcrResult` that Task 06 consumes.

Expected outcome: a clean fixture extracts text with plausible confidence; a degraded fixture
extracts with low confidence and warnings; a corrupt file produces `FAILED` rather than a silent
empty success; and the entire default test suite runs without PaddleOCR ever executing.

## Why This Exists

Step 5 of `docs/implementation-plan.md`. Two design constraints shape everything here.

**The adapter boundary is what keeps this project buildable.** PaddleOCR's raw response is a nested
list structure that would be miserable to depend on directly, and at least one teammate may not be
able to install it at all (`docs/ENVIRONMENT-REPORT.md`). Normalizing to `OcrResult` inside
`paddleocr_adapter.py` means Task 06, Task 07, and every test build against a stable shape and run
with `fake_adapter.py`.

**OCR is recognition, never verification.** Confidence describes character recognition. It is never
a fraud probability, an authenticity score, or a risk rating (`AGENTS.md` Rule 5). Everything this
task returns is evidence for a later decision, never the decision itself.

---

# 2. Authoritative Documentation

* `AGENTS.md` — Rules 3, 5, 10, 11
* `docs/document-processing.md` — **authoritative** (entire document): pipeline steps 1–8,
  PaddleOCR boundaries, failure states, security controls
* `docs/backend.md` — `adapters/ocr/`, `services/ocr_service.py`
* `docs/architecture.md` — adapters are the only place external runtimes are imported
* `docs/configuration.md` — `OCR_ENGINE`, `OCR_LANGUAGE`, `OCR_TIMEOUT_SECONDS`,
  `LOW_CONFIDENCE_THRESHOLD`, `MAX_PDF_PAGES`
* `docs/data-model.md` — `extraction_results` columns; `documents.processing_state`
* `docs/testing.md` — the `integration` marker convention
* `docs/decisions.md` — D-02 (PaddleOCR), D-06 (no mandatory LLM), D-16 (synchronous for MVP)
* `docs/ENVIRONMENT-REPORT.md` — the pinned versions Task 01 established
* `docs/workflow.md` Stages 2–3

---

# 3. Scope

## In Scope

* `backend/app/adapters/ocr/base.py` — the `OcrAdapter` interface and the `OcrResult` dataclass.
* `backend/app/adapters/ocr/paddleocr_adapter.py` — PaddleOCR (English, CPU), normalizing to
  `OcrResult`.
* `backend/app/adapters/ocr/fake_adapter.py` — deterministic canned responses supporting at minimum:
  clean text, low confidence, no text, raises, and times out.
* `backend/app/services/ocr_service.py` — the pipeline: PDF page rendering, per-page preprocessing,
  adapter invocation, multi-page assembly, `extraction_results` persistence, `processing_state`
  transitions.
* An adapter factory selecting the implementation from `OCR_ENGINE`.
* `paddleocr` and the agreed PDF library added to `requirements.txt` at the versions from
  `docs/ENVIRONMENT-REPORT.md`.
* `backend/tests/test_ocr_pipeline.py`.

## Out of Scope

* Mapping OCR text to category fields — **Task 06**. This task returns text and regions; it knows
  nothing about `student_name`.
* `GET /documents/{id}/extraction` — **Task 06/10**.
* Any confidence-based *decision* (what counts as too low, what triggers review) — that is
  `docs/verification-rules.md`, **Task 07**. This task reports confidence faithfully and stops.
* Any LLM or vision model (`docs/decisions.md` D-06).
* Deciding when the pipeline runs — **Task 10**.
* Image forensics, tamper detection, or manipulation analysis — out of project scope entirely.

---

# 4. Allowed Files / Areas

```text
backend/app/adapters/ocr/base.py
backend/app/adapters/ocr/paddleocr_adapter.py
backend/app/adapters/ocr/fake_adapter.py
backend/app/adapters/ocr/__init__.py          (factory)
backend/app/services/ocr_service.py
backend/requirements.txt                       (add paddleocr + PDF library)
backend/tests/test_ocr_pipeline.py             (new)
```

### May Modify If Required

```text
backend/tests/conftest.py     (register the fake OCR adapter fixture)
```

---

# 5. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Task 01 (`Settings`, `ENVIRONMENT-REPORT.md`) | **Hard** | Pinned versions come from the report |
| Task 04 (`safe_upload_path()`, stored files) | **Hard** | Reads what upload stored |
| Task 02 (`extraction_repo`, `documents_repo`) | **Hard** | Persistence and state transitions |
| Task 03 (sample documents) | **Integration** | The integration test and degraded-sample tuning |
| PaddleOCR + first-run weights | **Hard (environment)** | Download once, online, during setup |

### Dependency Status

* [x] Dependencies exist once Tasks 01, 02, 04 merge
* [x] Requires coordination: PDF library with Task 04; degraded sample tuning with Task 03
* [x] External dependency: PaddleOCR weights provisioned before demo day

### Parallel-development notes

Build the entire pipeline against `fake_adapter.py` first. It needs no PaddleOCR at all, which means
this task can be largely complete before the real adapter is even installable. Write
`paddleocr_adapter.py` last and verify it once, manually.

---

# 6. Contracts That Must Be Preserved

### The adapter boundary (`AGENTS.md` Rule 10)

* `paddleocr` is imported **only** inside `paddleocr_adapter.py`. Not in `ocr_service.py`, not in
  tests, not in `base.py`.
* PaddleOCR's raw nested-list response never escapes that module. `ocr_service.py` sees `OcrResult`
  and nothing else. This is what makes the engine swappable (`NFR-05`).
* The interface is `run(image: PIL.Image) -> OcrResult`.

### `OcrResult` — publish this shape early

```python
@dataclass
class OcrRegion:
    text: str
    confidence: float          # 0.0–1.0
    bbox: tuple[int, int, int, int]
    page: int                  # 1-indexed

@dataclass
class OcrResult:
    text: str                  # all regions joined in reading order
    regions: list[OcrRegion]
    mean_confidence: float | None   # None when no regions
    engine_name: str
    engine_version: str
    warnings: list[str]
```

Task 06 builds directly against this. Publish it in the log the day it stabilises, and treat any
later change as a cross-task contract change.

### Pipeline (`docs/document-processing.md` steps 1–8)

* The stored original is **never** modified. Preprocessing works on an in-memory copy.
* PDFs render page by page, long edge capped at 2000px, up to `MAX_PDF_PAGES`.
* Preprocessing is conservative: grayscale, EXIF orientation, light denoise and contrast. Never
  redraw, never aggressively threshold, never reconstruct content.
* `OCR_TIMEOUT_SECONDS` (default 30) is enforced **per page**.
* `engine_version` is read from the installed package at runtime, never hardcoded.

### Outcome semantics — these three are different states

| Situation | Result |
|---|---|
| Text extracted | `SUCCEEDED`, `processing_state = OCR_DONE` |
| No text at all | `SUCCEEDED` + `no_text_detected` warning, `OCR_DONE`. A legitimate outcome |
| OCR raised or timed out | `FAILED`, `processing_state = OCR_FAILED`. **Never** a silent empty success |

Collapsing the middle row into the third — or into the first with empty text — is the specific bug
this table exists to prevent. `docs/verification-rules.md` routes them to different statuses.

* One failed page in a multi-page PDF records a warning; the other pages' text survives. One bad
  page never erases the document.

### Confidence (`AGENTS.md` Rule 5)

Reported faithfully, per region. Never thresholded here, never converted into a score, never used to
decide anything. `LOW_CONFIDENCE_THRESHOLD` belongs to Task 07 — do not read it in this task.

### Testing (`AGENTS.md` Rule 11)

The default suite uses `fake_adapter.py` exclusively. The single real-PaddleOCR test is marked
`@pytest.mark.integration` and excluded by default.

---

# 7. Implementation Requirements

### Requirement 1 — Interface and result types

`base.py` defines `OcrAdapter` (abstract, one method) plus the dataclasses above. No implementation
detail from any engine leaks in here.

### Requirement 2 — PaddleOCR adapter

Initialise once at module or instance level — constructing `PaddleOCR()` per call is slow enough to
wreck the demo. Language from `OCR_LANGUAGE`, CPU inference. Map each detected region to an
`OcrRegion`, join text in reading order (top-to-bottom, then left-to-right), compute
`mean_confidence` across regions.

### Requirement 3 — Fake adapter

Deterministic, configurable modes: `clean` (high confidence), `low_confidence` (values below 0.70),
`empty` (no regions), `raises`, `timeout`. Every mode returns valid `OcrResult` structures — the
fakes must be realistic enough that Task 06 can be genuinely tested against them.

### Requirement 4 — Pipeline service

`ocr_service.process_document(document_id, session) -> ExtractionResult`:

1. Load the `documents` row; resolve the file via `safe_upload_path()`.
2. Set `processing_state = OCR_IN_PROGRESS`.
3. PDF → render pages (capped resolution, `MAX_PDF_PAGES`). Image → single page.
4. Preprocess each page in memory.
5. Run the configured adapter per page, with the per-page timeout.
6. Assemble a combined `OcrResult` with page-tagged regions.
7. Write `extraction_results` with `raw_ocr_json`, `warnings_json`, `engine_name`, `engine_version`,
   and `status`.
8. Set `processing_state` to `OCR_DONE` or `OCR_FAILED`.

`extracted_fields_json` is written by **Task 06**, not here. Leave it empty or null.

### Requirement 5 — Adapter factory

`OCR_ENGINE=paddleocr` → real adapter; `OCR_ENGINE=fake` → fake adapter. An unknown value fails at
startup (`docs/configuration.md` fail-fast), never falls back silently.

### Requirement 6 — Do not read `LOW_CONFIDENCE_THRESHOLD`

If you find yourself needing it here, you are implementing Task 07's job.

### Error Handling

* File missing on disk → `FAILED` with a clear warning. Do not attempt recovery.
* Adapter raises → catch, record the exception **type and message** in warnings (never a full
  traceback), set `FAILED`.
* Per-page timeout → that page fails with a warning; other pages continue.
* All pages fail → `FAILED`.
* Some pages fail → `SUCCEEDED` with per-page warnings.
* Zero regions across all pages → `SUCCEEDED` + `no_text_detected`.

---

# 8. Testing Requirements

## Automated Tests — default suite, fake adapter only

`backend/tests/test_ocr_pipeline.py`:

* Clean fake response → `SUCCEEDED`, `mean_confidence` populated, `processing_state = OCR_DONE`,
  `extraction_results` row written with `engine_name`/`engine_version`.
* Low-confidence fake → still `SUCCEEDED`; the low values pass through **unaltered** — assert the
  exact value, proving nothing thresholded or rounded it.
* Empty fake → `SUCCEEDED` with `no_text_detected` in warnings, **not** `FAILED`.
* Raising fake → `FAILED`, `OCR_FAILED`, exception type recorded, **no silent empty text**.
* Timeout fake → `FAILED` with a timeout warning.
* Multi-page PDF where page 2 raises → pages 1 and 3 text present, page-2 warning recorded,
  overall `SUCCEEDED`.
* Multi-page PDF where every page raises → `FAILED`.
* The original file on disk is byte-identical before and after processing.
* **No `paddleocr` import occurs during the default suite** — assert `"paddleocr" not in sys.modules`
  after a run. This is the cheapest possible guard on Rule 11 and it catches accidental top-level
  imports immediately.
* `OCR_ENGINE=nonsense` → startup fails.

Run:

```bash
cd backend && pytest tests/test_ocr_pipeline.py
```

## Integration Test — marked, excluded by default

One `@pytest.mark.integration` test running the real adapter against
`sample_documents/academic_certificate_match.png`: text extracted, `mean_confidence` above 0.5,
`engine_version` populated.

```bash
cd backend && pytest -m integration
```

## Manual Verification

1. Run the integration test. Print the extracted text and inspect it against the sample.
2. Run the real adapter against `academic_certificate_degraded.png`. Record the per-field confidence
   values in the log — **Task 03 needs these to tune the degraded sample**, and Task 07 needs them to
   sanity-check the 0.70 threshold.
3. Run against `academic_certificate_match.pdf` → same text as the PNG.
4. Run against a deliberately corrupted file → `FAILED`, clear warning, no empty success.
5. Time a single-page run and record it. `NFR-09` budgets 15 seconds for the whole chain.

---

# 9. Acceptance Criteria

* [ ] `OcrAdapter` interface and `OcrResult` dataclasses defined and published.
* [ ] `paddleocr` is imported **only** in `paddleocr_adapter.py`; the raw response never escapes it.
* [ ] `fake_adapter.py` supports clean, low-confidence, empty, raises, and timeout modes.
* [ ] `ocr_service.py` implements `docs/document-processing.md` steps 1–8.
* [ ] The stored original is never modified.
* [ ] Per-page timeout enforced; one bad page never erases the others.
* [ ] Empty-text and OCR-failure are distinct outcomes, correctly classified.
* [ ] Confidence is passed through unaltered; `LOW_CONFIDENCE_THRESHOLD` is not read in this task.
* [ ] `engine_version` read at runtime.
* [ ] Adapter factory fails fast on an unknown `OCR_ENGINE`.
* [ ] Default suite passes and never imports `paddleocr`.
* [ ] The single `integration` test passes when run manually.
* [ ] Degraded-sample confidence values recorded in the log for Task 03 and Task 07.
* [ ] `git diff` reviewed; development log updated; branch pushed; PR prepared.

---

# 10. Known Risks

* **PaddleOCR initialisation cost.** Constructing the engine per call adds seconds per document.
  Initialise once.
* **First-run weight download.** Must happen online during setup. Confirm it has happened on the
  demo machine well before demo day, and make sure no test triggers it.
* **Raw response leakage.** The natural way to write this — returning PaddleOCR's structure and
  unpacking it in the service — is exactly the thing that makes the codebase unswappable and the
  tests un-fakeable. Normalize inside the adapter.
* **Over-aggressive preprocessing.** Heavy thresholding can erase faint text entirely, turning a
  readable scan into `no_text_detected`. Conservative means conservative.
* **Timeout implementation on Windows.** Signal-based timeouts do not work there. Use a thread or
  process with a join timeout, and test it on Windows if any teammate develops on one.
* **Reading order.** PaddleOCR returns regions in detection order, not reading order. Sort before
  joining, or Task 06's label matching will behave unpredictably.

---

# 11. Open Questions

* **PDF library** — settle with Task 04's owner if not already done; this task needs rendering, not
  just page counting, which may decide it. Record in `docs/decisions.md`.
* **Degraded-sample calibration** is expected to need one joint pass with Task 03's owner once real
  OCR runs. Not a blocker; budget the time.
* **Resolved:** synchronous processing for MVP (`docs/decisions.md` D-16). Do not introduce a task
  queue.

---

# 12. Handoff Notes

* **Publish `OcrResult` in the log the day it stabilises.** Task 06 is blocked on knowing this shape
  and can start the moment it exists, even before this task merges.
* Record real degraded-sample confidence values for Task 03 (tuning) and Task 07 (threshold sanity).
* Record single-page timing against the `NFR-09` budget.
* Tell Task 10 how `process_document()` is invoked and what it returns.
* Note in the log which machines can run the real adapter — Task 12's rehearsal needs one that can.

---

# 13. Definition of Done

```text
Implementation complete
        +
Default suite passing with fake adapter only (no paddleocr import)
        +
Integration test verified manually at least once
        +
Degraded-sample confidence values recorded
        +
Scope verified (no field mapping, no threshold decisions)
        +
Git diff reviewed
        +
Development log updated with the OcrResult shape
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

1. Read `AGENTS.md`, especially Rules 5, 10, and 11.
2. Read `docs/document-processing.md` **completely** — it is this task's full specification.
3. Read `docs/ENVIRONMENT-REPORT.md` for pinned versions.
4. Read this task file completely.
5. State your plan, including the exact `OcrResult` shape, before coding.

During implementation:

* Build against `fake_adapter.py` first. Write `paddleocr_adapter.py` last.
* Never let PaddleOCR's raw response format escape its adapter module.
* Never let PaddleOCR be imported anywhere else, including tests.
* Keep empty-text, low-confidence, and failure as three distinct outcomes.
* Pass confidence through unaltered. Do not threshold it — that is Task 07's job.
* Never modify the stored original file.
* Test incrementally.

If PaddleOCR will not install on your machine, **say so and continue with the fake adapter** — the
architecture supports this deliberately. Report it to the project lead so they know which machines
can run the real engine.

Before PR:

* Run the default suite and report exact output, including the no-`paddleocr`-import assertion.
* Run `pytest -m integration` once and report the extracted text.
* Record degraded-sample confidence values and single-page timing in the log.
* Review `git diff` and `git status`.
* Update `logs/task-05-ocr.md` with the published `OcrResult` shape.
* Push and open the PR per `docs/git-workflow.md`.
