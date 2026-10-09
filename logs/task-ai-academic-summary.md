# Task — AI Academic Summary

## Status
In progress.

## Objective
Add an isolated demo feature that generates a concise academic summary from existing OCR/extraction
data for selected synthetic academic documents using local Ollama.

## Scope Notes
- No database schema change.
- No OCR, verification, review, or blockchain behavior changed.
- Existing `.env`, `venv/`, and `venv311/` are not modified.
- Added local Ollama settings to `.env.example` and documentation with safe defaults.

## Work Log
- Inspected project docs, backend architecture, API routes, repositories, extraction storage,
  frontend routing, recent document state, mocks, and fixture generator.
- Added backend AI adapter interface, Ollama adapter, fake adapter, summary service, API router, and
  backend tests.
- Added frontend API wrapper, Academic Summary page, route/nav entry, mock handler, and page tests.
- Added synthetic academic summary fixture image generation and generated three PNGs.
- Added `docs/academic-summary.md` and updated API/config/fixture docs.
- Improved the existing Academic Summary page with direct academic uploads, original-file preview,
  guarded document deletion, duplicate-request prevention, and extraction-on-demand for uploaded
  academic documents that do not yet have OCR results.
- Added `GET /documents/{id}/file` for same-application previews/downloads without exposing file
  paths.
- Added `DELETE /documents/{id}` guarded so documents with verification history are not deleted.
- Shortened the Ollama prompt while preserving non-invention and no-verdict rules.

## Validation
- `.\venv311\Scripts\python.exe -m pytest tests\test_academic_summary.py -q` — 5 passed in 0.85s
  after fixing the test helper to use the fixture-managed test database.
- `.\venv311\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .test-tmp\pytest-academic-summary`
  — 301 passed, 1 deselected in 21.42s.
- `npm test -- AcademicSummaryPage.test.tsx` — 1 file passed, 2 tests passed.
- `npm run check` — stopped at pre-existing `src/pages/UploadPage.test.tsx(128,4): error TS1005:
  '}' expected`.
- `npm run lint` — same pre-existing `UploadPage.test.tsx` parse error; also reports an existing
  `SplashPage.tsx` exhaustive-deps warning.

## Correction Log
- Corrected the AI Summary page so it no longer reads from or writes to the shared recent-documents
  workflow. It now shows only files uploaded on that page during the current session.
- Restored recent document hydration so the original Documents page does not show upload-only
  documents that have no visible verification history.
- Kept the upload, preview, delete, and summary actions isolated to the AI Summary page.

## Correction Validation
- `npm test -- AcademicSummaryPage.test.tsx` - 1 file passed, 7 tests passed in 4.27s.
- `.\venv311\Scripts\python.exe -m pytest tests\test_academic_summary.py tests\test_api_documents.py`
  - 21 passed in 2.29s. Pytest warned that the default cache directory is not writable.
- `.\venv311\Scripts\python.exe -m pytest --basetemp .test-tmp\pytest -o cache_dir=.test-tmp\.pytest_cache`
  - 305 passed, 1 deselected in 21.80s.
- `npm run build` - stopped at pre-existing `src/pages/UploadPage.test.tsx(128,4): error TS1005:
  '}' expected`.
- `npm test` - Summary tests pass in the full run; suite still fails on existing
  `UploadPage.test.tsx` syntax error, existing wording scan hit, and existing
  `DocumentDetailPage.test.tsx` synthetic banner expectation. Reported total:
  16 files passed, 3 failed; 105 tests passed, 2 failed.
- `npm run lint` - same pre-existing `UploadPage.test.tsx` parse error; also reports existing
  `SplashPage.tsx` exhaustive-deps warning.
- `npm test` — new Academic Summary test passes; full suite still fails on existing
  `UploadPage.test.tsx` syntax error, existing wording scan hit in `BlockchainReceiptsPage.tsx`, and
  existing `DocumentDetailPage.test.tsx` synthetic banner expectation.
- `npm run build` — stopped at the same pre-existing `UploadPage.test.tsx(128,4)` syntax error.
- `.\venv311\Scripts\python.exe -m pytest tests\test_academic_summary.py tests\test_api_documents.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-summary-improvements`
  — 21 passed in 2.26s.
- `npm test -- AcademicSummaryPage.test.tsx` — 1 file passed, 7 tests passed.
- `.\venv311\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .test-tmp\pytest-summary-improvements`
  — 305 passed, 1 deselected in 22.20s.
- `npm run check` — stopped at pre-existing `src/pages/UploadPage.test.tsx(128,4): error TS1005:
  '}' expected`.
- `npm test` — Summary tests pass in the full run; suite still fails on existing
  `UploadPage.test.tsx` syntax error, existing wording scan hit in `BlockchainReceiptsPage.tsx`, and
  existing `DocumentDetailPage.test.tsx` synthetic banner expectation. Reported total:
  16 files passed, 3 failed; 105 tests passed, 2 failed.
- `npm run build` — stopped at the same pre-existing `UploadPage.test.tsx(128,4)` syntax error.
- `npm run lint` — same pre-existing `UploadPage.test.tsx` parse error; also reports existing
  `SplashPage.tsx` exhaustive-deps warning.
