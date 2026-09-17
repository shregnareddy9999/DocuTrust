# PS21 Task Specification

> **This file is a work order for the assigned developer and their AI coding agent.**
>
> Do not expand the scope without explicit approval from the project lead.

---

## Task Information

**Task:** `Secure upload and file handling`
**Task ID:** `04` (`docs/implementation-plan.md` step 4)
**Assigned To:** `Unassigned` (suggested: project lead — shared surface)
**Branch:** `feature/task-04-upload`
**Priority:** `Critical` — blocks Task 05; it is also the project's only untrusted-input boundary
**Status:** `Not Started`

---

# 1. Goal

## Objective

Implement `POST /documents` and `GET /documents/{id}` per `docs/api.md`, with content-based
validation, safe server-side storage, SHA-256 fingerprinting, and the `documents` row.

Expected outcome: a valid upload returns `201` with a `document_id` and `processing_state:
"UPLOADED"`; every invalid upload is rejected with its exact documented error code, before anything
downstream touches the file.

## Why This Exists

Step 4 of `docs/implementation-plan.md`. This endpoint is **the only place in PS21 where untrusted
bytes enter the system**. Everything after it — preprocessing, OCR, extraction, matching — assumes
the file has already been validated. If that assumption is wrong, it is wrong everywhere at once.

Two specific dangers this task defends against: path traversal via a crafted filename (which is why
the stored name is always server-generated), and content-type spoofing (which is why validation
reads magic bytes rather than trusting the browser).

---

# 2. Authoritative Documentation

* `AGENTS.md` — Rules 1, 3, 12
* `docs/api.md` — **authoritative**: `POST /documents`, `GET /documents/{id}`, error envelope,
  the exact codes `400 INVALID_CATEGORY`, `413 FILE_TOO_LARGE`, `415 UNSUPPORTED_MEDIA_TYPE`,
  `422 EMPTY_OR_CORRUPT_FILE`
* `docs/document-processing.md` — **authoritative**: supported input, validation, pipeline steps 1–2
* `docs/security-privacy.md` — **authoritative**: upload threat model and controls
* `docs/data-model.md` — `documents` columns
* `docs/configuration.md` — `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `MAX_PDF_PAGES`, `ALLOWED_MIME_TYPES`
* `docs/category-schemas.md` — the four valid category values
* `docs/workflow.md` Stage 1
* `docs/backend.md` — `api/documents.py`, `services/upload_service.py`

---

# 3. Scope

## In Scope

* `backend/app/api/documents.py` — `POST /documents` (multipart: `file`, `category`) and
  `GET /documents/{document_id}`.
* `backend/app/services/upload_service.py` — validation, safe storage, SHA-256, page counting,
  `documents` row creation, and the path-safety helper.
* Router registration in `main.py`.
* `backend/tests/test_upload.py`.

## Out of Scope

* `GET /documents/{id}/extraction` — **Task 05/06/10** (it returns extraction data this task does not
  produce).
* Any OCR, preprocessing, or image manipulation — **Task 05**. This task stores bytes and counts PDF
  pages. It does not render them.
* Triggering the OCR pipeline. Whether upload kicks off processing automatically or a separate call
  does is **Task 10**'s integration decision (`docs/decisions.md` D-16). This task leaves
  `processing_state = "UPLOADED"` and stops.
* The retention cleanup script — **Task 12**.
* Virus scanning — out of MVP scope; note it in `docs/security-privacy.md` as deferred, do not build
  it.

---

# 4. Allowed Files / Areas

```text
backend/app/api/documents.py
backend/app/services/upload_service.py
backend/tests/test_upload.py           (new)
backend/tests/fixtures/               (small malformed test files, if needed)
```

### May Modify If Required

```text
backend/app/main.py           (register the documents router)
backend/requirements.txt      (python-multipart; pypdfium2 or pypdf for page counting)
```

### Coordination note

Task 10 completes the documents router. **This task owns a minimal version**; Task 10 verifies and
extends it. Do not implement Task 10's endpoints here, and Task 10 must not re-implement these.

---

# 5. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Task 01 (`Settings`, exception handler, app skeleton) | **Hard** | Limits come from `Settings` |
| Task 02 (`documents` model + `documents_repo`) | **Hard** | Row creation |
| `python-multipart` | **Hard (library)** | FastAPI multipart parsing |
| A PDF library for page counting | **Hard (library)** | Confirm against `docs/ENVIRONMENT-REPORT.md` |

### Dependency Status

* [x] Dependencies exist once Tasks 01 and 02 merge
* [x] Requires coordination: router ownership with Task 10; PDF library choice with Task 05

### Parallel-development notes

Coordinate the PDF library choice with Member A (Task 05) **before** pinning it. Both tasks open
PDFs; using two different libraries for that would be a needless inconsistency and a second failure
mode.

---

# 6. Contracts That Must Be Preserved

### API

* `POST /documents` accepts multipart `file` + `category`, returns `201 {document_id, category,
  processing_state}` exactly as `docs/api.md` specifies.
* Error codes are **exactly** the four documented ones. Not a generic `400` for everything. The
  distinction matters: `415` says "wrong type", `413` says "too big", `422` says "right type but
  broken" — and the frontend renders different guidance for each.
* `GET /documents/{document_id}` returns the documented metadata shape, never raw bytes.
* `404 DOCUMENT_NOT_FOUND` for an unknown ID.
* All errors use the `docs/api.md` envelope, produced by Task 01's global handler.

### Security (`docs/security-privacy.md`)

* **The stored filename is always server-generated.** The user's `original_filename` is stored for
  display only and never used to build a path. This is the path-traversal defence and it is
  non-negotiable.
* **Validate by content, not by claim.** Extension, declared MIME, *and* magic-byte signature must
  all agree with `ALLOWED_MIME_TYPES`. A `.png` that is actually a PDF is rejected.
* Size is checked against `MAX_UPLOAD_MB` **during** streaming, not after the whole file is in
  memory — otherwise the limit is unenforceable against a large upload.
* PDF page count is checked against `MAX_PDF_PAGES` before the row is created.
* `UPLOAD_DIR` is outside any static or publicly served route.
* Uploaded files are never executed, never passed to a shell, never used as a format string.
* No log line contains file contents. The original filename may be logged; its contents may not.

### Data

* A `documents` row is created **only** after every validation passes. A rejected upload leaves no
  row and no file on disk.
* `sha256` is computed over the original bytes as received.
* `mime_type` is the **sniffed** type, not the client-declared header.
* `page_count` is 1 for images, actual count for PDFs.
* `processing_state` starts as `"UPLOADED"`.

---

# 7. Implementation Requirements

### Requirement 1 — Category validation first

Validate `category` against the four values before touching the file at all. An invalid category is
`400 INVALID_CATEGORY` and costs nothing to detect.

### Requirement 2 — Streaming size check

Read the upload in chunks, accumulating both the SHA-256 and the byte count. Abort the moment the
count exceeds `MAX_UPLOAD_MB` and return `413 FILE_TOO_LARGE`. Do not read the whole file into
memory first and then measure it.

### Requirement 3 — Content-based type validation

Sniff the magic bytes (`%PDF-` for PDF, the PNG signature, the JPEG SOI marker) and confirm the
result is in `ALLOWED_MIME_TYPES`. Reject a mismatch between sniffed and declared type with `415
UNSUPPORTED_MEDIA_TYPE`. Do not fall back to trusting the extension when sniffing is inconclusive —
reject instead.

### Requirement 4 — Structural validation

* Images: open with Pillow and call `verify()`. A failure is `422 EMPTY_OR_CORRUPT_FILE`.
* PDFs: open with the agreed library, count pages. Failure to open — including encryption — is `422`.
  We do not prompt for a password (`docs/document-processing.md`). Exceeding `MAX_PDF_PAGES` is
  `413 FILE_TOO_LARGE` with a message that says it is the page count, not the byte size.
* Zero-byte upload is `422`.

### Requirement 5 — Safe storage

Generate `storage_key` as `{uuid4().hex}{ext}`, where `ext` derives from the **sniffed** type, never
from the user's filename. Write under `UPLOAD_DIR`. Provide a `safe_upload_path(storage_key)` helper
that resolves the path and asserts it stays inside `UPLOAD_DIR`; every read anywhere in the codebase
goes through it.

### Requirement 6 — Ordering

Validate everything → write the file → create the row. If row creation fails, delete the written
file. Never leave a file with no row (an orphan the cleanup script will not find) or a row with no
file (a phantom that breaks Task 05).

### Requirement 7 — `GET /documents/{id}`

Return exactly the `docs/api.md` shape. Never return `storage_key`, an absolute path, or the bytes.

### Error Handling

| Situation | Response |
|---|---|
| Category not one of four | `400 INVALID_CATEGORY` |
| Size exceeds `MAX_UPLOAD_MB` | `413 FILE_TOO_LARGE` |
| Page count exceeds `MAX_PDF_PAGES` | `413 FILE_TOO_LARGE`, message naming pages |
| Sniffed type not allowed, or disagrees with declared | `415 UNSUPPORTED_MEDIA_TYPE` |
| Zero bytes, corrupt, or encrypted | `422 EMPTY_OR_CORRUPT_FILE` |
| Unknown document ID | `404 DOCUMENT_NOT_FOUND` |
| Disk write fails | `500 INTERNAL_ERROR` with `correlation_id`, no path in the message |

No error message contains a filesystem path, a stack trace, or raw exception text.

---

# 8. Testing Requirements

## Automated Tests

`backend/tests/test_upload.py`, using FastAPI `TestClient` and a temp `UPLOAD_DIR`:

**Happy path**
* Valid PNG + valid category → `201`, correct body, file on disk under a server-generated name,
  `documents` row with correct `sha256`, `mime_type`, `byte_size`, `page_count = 1`,
  `processing_state = "UPLOADED"`.
* Valid single-page PDF → `201`, `page_count = 1`.
* Valid JPEG → `201`.

**Rejection**
* Invalid category → `400 INVALID_CATEGORY`.
* File over the limit → `413 FILE_TOO_LARGE`.
* PDF over `MAX_PDF_PAGES` → `413`, message mentions pages.
* `.txt` file → `415 UNSUPPORTED_MEDIA_TYPE`.
* **A PDF renamed to `.png`** → `415`. This is the content-sniffing test and it is the one that
  matters most.
* Zero-byte file → `422`.
* Truncated/corrupt PNG → `422`.
* Encrypted PDF → `422`.

**Security**
* **Filename `../../etc/passwd`** → the file lands inside `UPLOAD_DIR` under a generated name, and
  nothing is written outside it.
* Filename with null bytes, or 500 characters → handled, generated name used.
* Two uploads of identical content → two rows, two distinct `storage_key`s, identical `sha256`.
* Every rejection path leaves **no** row and **no** file on disk.

**Retrieval**
* `GET /documents/{id}` → documented shape; no `storage_key`, no path.
* Unknown ID → `404 DOCUMENT_NOT_FOUND`.

Run:

```bash
cd backend && pytest tests/test_upload.py
```

## Manual Verification

1. `curl -F "file=@sample.png" -F "category=academic_certificate" .../documents` → `201`.
2. Repeat with a `.txt` → `415`, correct envelope.
3. Upload a file named `../../../evil.png` → inspect `UPLOAD_DIR`; confirm nothing escaped.
4. `ls` the upload directory — every name is a UUID, none resembles a user-supplied filename.
5. Confirm `UPLOAD_DIR` is not reachable over HTTP.

---

# 9. Acceptance Criteria

* [ ] `POST /documents` matches `docs/api.md` on success and on all four error codes.
* [ ] Validation is content-based; a PDF renamed `.png` is rejected.
* [ ] Size is enforced during streaming, not after full buffering.
* [ ] PDF page count enforced against `MAX_PDF_PAGES`.
* [ ] Encrypted and corrupt files rejected with `422`; no password prompt.
* [ ] The stored filename is always server-generated; `original_filename` never builds a path.
* [ ] `safe_upload_path()` exists and is the only way file paths are resolved.
* [ ] A rejected upload leaves no row and no file.
* [ ] A failed row creation deletes the written file.
* [ ] `sha256`, sniffed `mime_type`, `byte_size`, `page_count`, `processing_state` all stored
      correctly.
* [ ] `GET /documents/{id}` never exposes `storage_key` or a path.
* [ ] No error message leaks a path, stack trace, or exception text.
* [ ] All tests pass, including the path-traversal and renamed-file cases.
* [ ] `git diff` reviewed; development log updated; branch pushed; PR prepared.

---

# 10. Known Risks

* **Trusting `UploadFile.content_type`.** FastAPI exposes it, the browser sets it, and an attacker
  controls it. It is a hint, never a decision.
* **Buffering before measuring.** `await file.read()` then `len()` makes `MAX_UPLOAD_MB`
  unenforceable. Stream in chunks.
* **Pillow's lazy loading.** `Image.open()` alone does not detect a truncated file; `verify()` is
  required. After `verify()` the image object is unusable — reopen if you need it, though this task
  does not.
* **Windows path handling.** Use `pathlib` and `.resolve()`; do not concatenate strings.
* **Router ownership collision with Task 10.** Talk to the lead before touching `documents.py` if
  Task 10 is already in flight.
* **Orphaned files after a failed row insert.** Requirement 6 exists for this; test it.

---

# 11. Open Questions

* **PDF library choice** (`pypdfium2` versus `pypdf`) must be agreed with Task 05 before pinning.
  Task 05 needs rendering, not just counting, which may decide it. Coordinate, record the choice in
  `docs/decisions.md`, then pin.
* **Resolved:** upload does *not* trigger OCR. `processing_state` stays `"UPLOADED"` and Task 10
  decides how processing is invoked (`docs/decisions.md` D-16).

---

# 12. Handoff Notes

* Publish in the log: the `upload_service` function signatures, the `safe_upload_path()` helper, and
  the confirmed PDF library.
* Task 05 reads stored files through `safe_upload_path()` and transitions `processing_state` onward
  from `"UPLOADED"`.
* Task 10 completes this router; tell the lead exactly which endpoints exist here so they are not
  duplicated.
* Task 11 renders the four error codes with distinct messages — confirm the codes with Member D.
* Task 12's cleanup script needs `UPLOAD_DIR` layout and the `storage_key` convention.

---

# 13. Definition of Done

```text
Implementation complete
        +
Tests passing (including path traversal and content-sniffing cases)
        +
Manual verification complete
        +
Scope verified (no OCR, no extraction endpoint)
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
2. Read `docs/security-privacy.md` and `docs/document-processing.md` §"Supported input" completely.
3. Read `docs/api.md` for the exact error codes.
4. Read this task file completely.
5. State your plan, including the validation order, before coding.

During implementation:

* Never trust the client-declared content type or the filename.
* Always generate the stored filename server-side.
* Stream and measure; never buffer then measure.
* Return the exact documented error code for each failure — not a generic 400.
* Leave no orphaned files and no phantom rows.
* Do not run OCR, render pages, or implement the extraction endpoint. Those belong to Tasks 05/06.
* Test incrementally, starting with the security cases.

If the PDF library choice is unsettled, **coordinate with Task 05's owner before pinning it**.

Before PR:

* Run the tests and report exact output.
* Manually attempt a path-traversal filename and confirm containment.
* Review `git diff` and `git status`.
* Update `logs/task-04-upload.md`.
* Push and open the PR per `docs/git-workflow.md`.
