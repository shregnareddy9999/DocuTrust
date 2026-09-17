# Document Processing and OCR

## Supported input (resolves D-14)

- Formats: JPEG, PNG, PDF.
- `MAX_UPLOAD_MB = 10`, `MAX_PDF_PAGES = 5` (defaults; overridable via `configuration.md`).
- Language: English only for MVP (`PaddleOCR` `lang="en"`). Document this limitation in the demo
  script — do not silently attempt other scripts.
- Encrypted or unreadable PDFs are rejected with `422 EMPTY_OR_CORRUPT_FILE` — no attempt to prompt
  for a password.
- Content is validated by signature (magic bytes / `Pillow`/`pypdfium2` open check), not by file
  extension alone.

## Pipeline (implemented in `backend/app/services/ocr_service.py`)

1. Store the original bytes unchanged under `UPLOAD_DIR/{storage_key}`; never overwritten.
2. Re-check type/size/page-count server-side (never trust the client's declared `Content-Type`).
3. For PDFs: render each page (up to `MAX_PDF_PAGES`) to an image at a bounded resolution (long edge
   ≤ 2000px) using `pypdfium2`/`pdf2image`.
4. Apply conservative preprocessing per page: grayscale conversion, orientation correction (EXIF for
   images), light denoise/contrast normalization. Never redraw or reconstruct content — only
   readability adjustments that preserve the original meaning.
5. Run PaddleOCR (via `backend/app/adapters/ocr/paddleocr_adapter.py`) on each preprocessed page
   image; collect per-region text + confidence + bounding box.
6. Normalize the adapter's raw output into the internal `OcrResult` shape (`text`, `regions[]`,
   `mean_confidence`, `engine_version`) — this is the shape `extraction_service.py` consumes; it is
   never PaddleOCR's raw response format directly (keeps the adapter swappable, `NFR-05`).
7. `extraction_service.py` maps `OcrResult` to the category schema (`category-schemas.md`), keeping
   raw OCR text and normalized fields as separate values (`data-model.md`).
8. Persist `extraction_results` with `status: SUCCEEDED` or `FAILED`, plus any `warnings`.

## PaddleOCR boundaries

- PaddleOCR is an OCR engine, not an authenticity engine. Its confidence score describes character
  recognition confidence only — it is never used as, or converted into, a "fraud probability."
- `engine_name` and `engine_version` are recorded on every `extraction_results` row for
  reproducibility.
- The adapter interface (`backend/app/adapters/ocr/base.py`) is: `run(image: PIL.Image) -> OcrResult`.
  Tests use `fake_adapter.py`, which returns pre-programmed `OcrResult` values — no test may require
  a live PaddleOCR model download or run.
- Exact PaddleOCR/PaddlePaddle package versions are confirmed against the actual development
  environment (Windows and macOS/Linux team machines) during Task 01/05 before being pinned in
  `requirements.txt` — do not assume a version works cross-platform without checking.

## Extraction behavior

- A field with no OCR evidence is `null` with a `warnings` entry (`missing_field:<name>`) — never
  inferred or guessed.
- Confidence values are per-field, copied from the underlying OCR region confidence; they describe
  extraction certainty only, never document authenticity.
- Any future LLM-based parsing assist is optional, requires an explicit project-lead decision
  (`decisions.md` D-06), and — if ever added — may only *suggest* a field value with its own
  confidence; it may never set `status: SUCCEEDED` on its own or bypass a human review path for a
  low-confidence field.

## Failure states

| Situation | Result |
|---|---|
| File is corrupt / unreadable by the PDF/image library | `extraction_results.status = FAILED`; document `processing_state = OCR_FAILED`; downstream verification returns `PROCESSING_FAILED`, never a mismatch/no-record status |
| PaddleOCR raises or times out (`OCR_TIMEOUT_SECONDS`, default 30s/page) | Same as above |
| OCR succeeds but returns no text at all | `status: SUCCEEDED` with `extracted_fields` all `null` and a `warnings: ["no_text_detected"]` entry — this is a legitimate (if unhelpful) OCR outcome, not a pipeline failure, and verification proceeds to `REVIEW_REQUIRED` |
| A single page in a multi-page PDF fails | That page's warnings are recorded; other pages' text is still used — one bad page must not erase the whole document's result |

## Security controls

- Uploaded files are only ever read by this pipeline; never executed, never passed to a shell
  command, never parsed by a second library "just in case."
- File access is scoped to the one document being processed via a path-safety helper
  (`backend/app/services/upload_service.py`) — no user input is ever concatenated directly into a
  filesystem path.
- Extracted text returned to the frontend/API is treated as **display data only** — nothing in this
  project passes extracted text into a prompt or command execution context, so there is no prompt-
  injection surface to defend here (this project has no LLM/agent loop).

## Processing-state contract (authoritative — resolves D-19)

Processing is **synchronous** (`decisions.md` D-16). That has a consequence people keep getting
wrong, so it is written out here in full: most intermediate states are never visible to the caller
that triggered them, because that caller is blocked inside the request.

### The states, and who can actually observe each one

| `documents.processing_state` | Written when | Observable by the triggering client? | Observable by another client? |
|---|---|---|---|
| `UPLOADED` | `POST /documents` succeeds | **Yes** — returned in the 201 body | Yes |
| `OCR_IN_PROGRESS` | Start of the OCR run, inside `POST .../verify` | **No** — it is blocked in that call | **Yes** — a second request during the run sees it |
| `OCR_DONE` | OCR + extraction succeeded | **Yes** | Yes |
| `OCR_FAILED` | OCR raised or timed out | **Yes** | Yes |

`OCR_IN_PROGRESS` is retained deliberately. It is not decoration: it is the guard that lets a
concurrent request detect work already in flight and return `409 EXTRACTION_NOT_READY` instead of
starting a second OCR run over the same file.

### The sequence

1. `POST /documents` → validate, store, write the row with `UPLOADED`, return `201`. **No OCR runs
   here.**
2. `POST /documents/{id}/verify` → in one synchronous call:
   a. if no successful extraction exists, set `OCR_IN_PROGRESS`, run OCR and extraction, then set
      `OCR_DONE` or `OCR_FAILED`;
   b. run matching and rules;
   c. write the `verification_results` row **already carrying its terminal status**;
   d. attempt the chain submission (D-20), isolated so a chain failure cannot fail this call;
   e. return the verification ID and its terminal status.
3. `GET /documents/{id}/extraction` and `GET /verifications/{id}` are **read-only**. Neither ever
   triggers processing.

### `PENDING` is a column default, not an API state

`verification_results.status` has `PENDING` in its enum because the column is written before rules
run, inside the same transaction. **No API response ever returns `PENDING`**, because the row is
committed with a terminal status. Contributors must not build polling loops, spinners, or UI
branches that wait for `PENDING` to change — there is nothing to wait for.

`StatusBadge` still renders a `PENDING` label (`frontend.md`), but only as a defensive default. It
is not part of any normal flow.

### What this means for each consumer

- **Backend (Task 10):** `POST .../verify` blocks for the full OCR duration — expect several
  seconds. Do not add a background queue (D-16).
- **Frontend (Task 11):** show a loading state for the duration of the `POST .../verify` call. **Do
  not poll** — the response already carries the terminal status. Polling here would be waiting on a
  transition that never happens.
- **Manual testing guide:** no "poll until `OCR_DONE`" step. A single `verify` call returns the
  final result.
- **Nobody:** do not expose or document a state the backend cannot produce.
