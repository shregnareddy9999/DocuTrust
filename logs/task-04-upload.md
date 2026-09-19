# Task 04 — Secure upload and file handling — Development Log

**Owner:** Member A / AI session
**Branch:** `feature/task-04-upload`
**Started:** 2026-09-19
**Status:** Ready for review

---

## Contracts this task implements

- `docs/api.md` — `POST /documents`, `GET /documents/{id}`, error envelope
- `docs/document-processing.md` — Supported input, validation, pipeline steps 1–2
- `docs/security-privacy.md` — Upload threat model and controls
- `docs/data-model.md` — `documents` columns
- `docs/configuration.md` — `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `MAX_PDF_PAGES`, `ALLOWED_MIME_TYPES`
- `docs/category-schemas.md` — Four valid category values
- `docs/workflow.md` Stage 1
- `docs/backend.md` — `api/documents.py`, `services/upload_service.py`
- `tasks/04-secure-upload.md` — Full work order

---

## Decisions I made inside my own scope

| Date | Decision | Why | Reversible? |
|---|---|---|---|
| 2026-09-19 | Stream upload to temp file (`{uuid}.tmp`) under UPLOAD_DIR, validate against temp file, atomic rename to final storage key | Meets streaming size enforcement + validation before DB write + atomic finalization | Yes |
| 2026-09-19 | Use `pypdfium2==4.28.0` for PDF page counting (coordinated with Task 05 owner) | Single library for both tasks; Task 05 needs rendering | Yes (with coordination) |
| 2026-09-19 | Compare declared `content_type` with sniffed MIME type, reject mismatch with 415 | Requirement: "Reject a mismatch between sniffed and declared type" | Yes |
| 2026-09-19 | Global settings object replaced via monkeypatch in test fixture for upload_service to use test paths | upload_service imports settings at module level; functions read at runtime | Yes |

---

## Interfaces I published for other tasks

```python
# upload_service.py
def safe_upload_path(storage_key: str) -> Path:
    """Resolve path and assert containment in UPLOAD_DIR. Every file read goes through this."""

async def process_upload(file: UploadFile, category_str: str) -> Document:
    """Stream, validate, store, create Document row. Returns created Document."""

# api/documents.py
POST /documents (multipart: file, category) -> 201 {document_id, category, processing_state}
GET /documents/{document_id} -> 200 {document_id, category, original_filename, processing_state, uploaded_at}

# Error codes (exact):
# 400 INVALID_CATEGORY
# 413 FILE_TOO_LARGE (byte size or page count)
# 415 UNSUPPORTED_MEDIA_TYPE (type not allowed or declared vs sniffed mismatch)
# 422 EMPTY_OR_CORRUPT_FILE (zero bytes, corrupt, encrypted)
# 404 DOCUMENT_NOT_FOUND
# 500 INTERNAL_ERROR (with correlation_id)
```

---

## Progress

### 2026-09-19
- **Did:** Coordinated PDF library choice with Task 05 owner → `pypdfium2` for both tasks; recorded in `docs/decisions.md` D-25
- **Did:** Pinned `pypdfium2==4.28.0` in `backend/requirements.txt`; verified install and import
- **Did:** Created test fixtures: `corrupt.png` (truncated), `encrypted.pdf`, `multi_page_6.pdf`, `single_page.pdf`, `large.bin` (11MB)
- **Did:** Implemented `backend/app/services/upload_service.py` with:
  - Streaming chunked upload to temp file (`{uuid}.tmp`) with size enforcement during streaming
  - SHA-256 computed incrementally
  - Magic-byte sniffing (PDF: `%PDF-`, PNG: `\x89PNG\r\n\x1a\n`, JPEG: `\xff\xd8\xff`)
  - Structural validation: Pillow `verify()` for images, `pypdfium2.PdfDocument` for PDFs (page count, encryption detection)
  - Declared vs sniffed MIME type mismatch check
  - Atomic rename from temp to final `{uuid}{ext}` storage key
  - `safe_upload_path()` helper with `pathlib.Path.resolve()` containment check
  - DB row creation only after all validation; cleanup on failure
- **Did:** Implemented `backend/app/api/documents.py` with `POST /documents` and `GET /documents/{id}`
- **Did:** Registered router in `backend/app/main.py`
- **Did:** Added custom `HTTPException` handler in `main.py` for exact error envelope format
- **Did:** Wrote comprehensive `backend/tests/test_upload.py` covering all required cases
- **Did:** Updated test fixtures in `conftest.py` to monkeypatch global settings for upload_service
- **Verified by running:** `cd backend && .venv\Scripts\python -m pytest tests/test_upload.py -v` → 20 passed
- **Verified by running:** `cd backend && .venv\Scripts\python -m pytest` → 98 passed (full suite)

---

## Blockers and open questions

| # | Question | Asked on | Answer | Resolved |
|---|---|---|---|---|
| 1 | PDF library choice | 2026-09-19 | `pypdfium2` for both Task 04 and Task 05 | ✅ |

---

## Tests

| Command | Last run | Result |
|---|---|---|
| `cd backend && .venv\Scripts\python -m pytest tests/test_upload.py -v` | 2026-09-19 | 20 passed |
| `cd backend && .venv\Scripts\python -m pytest` | 2026-09-19 | 98 passed |

---

## Known limitations at handoff

- PDF library `pypdfium2==4.28.0` pinned; Task 05 must use same version
- Test fixtures use temporary directories; manual verification needed for production paths
- Global exception handler catches `HTTPException` and returns exact error envelope per `api.md`
- `safe_upload_path()` is the only path resolution helper; all future file reads must use it

---

## Handoff notes

- **Files changed:** `backend/app/api/documents.py`, `backend/app/services/upload_service.py`, `backend/app/main.py`, `backend/tests/test_upload.py`, `backend/tests/conftest.py`, `backend/requirements.txt`, `docs/decisions.md`
- **What the next task needs:** Task 05 reads stored files via `safe_upload_path(document.storage_key)` and transitions `processing_state` from `"UPLOADED"` onward
- **What I did NOT do:** OCR, preprocessing, extraction endpoints, retention cleanup, authentication, virus scanning — all out of scope per task file