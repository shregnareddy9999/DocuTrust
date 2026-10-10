# Aadhaar Link Demo Feature - Development Log

**Status:** Implemented locally, not committed or pushed.
**Scope:** Separate synthetic Aadhaar Link demo feature. No database schema changes, no new environment variables, no new dependencies, no changes to existing verification categories.

## 2026-10-10

### Supabase verification
- Read-only backend Supabase configuration check succeeded.
- `SUPABASE_URL` loaded.
- `SUPABASE_SERVICE_ROLE_KEY` loaded; the secret was not printed.
- `demo_citizens` readable: 2 rows.
- `demo_linked_documents` readable: 9 rows.

### Implementation
- Added FastAPI endpoints:
  - `POST /api/v1/aadhaar-link`
  - `GET /api/v1/aadhaar-link/assets/{document_ref}`
- Added backend-only Supabase REST reads for `demo_citizens` and `demo_linked_documents`.
- Added temporary upload validation and cleanup for Aadhaar demo uploads using the existing upload validation helpers.
- Added whitelisted local sample asset serving. Unknown or missing references return an error envelope.
- Added a React Aadhaar Link page, sidebar route, API wrapper, MSW mocks, responsive styling, and preview modal/panel.
- Generated 9 permanent synthetic sample assets under `backend/app/fixtures/sample_documents/`, all visibly marked as synthetic demo documents.

### Verification
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-link`
  - First run: 1 failed, 4 passed.
  - Cause: mobile placeholder derived as `9000000001` instead of `9000005001`.
  - Fixed by reading the placeholder from whitelisted asset metadata.
  - Rerun: 5 passed in 0.62s.
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py tests\test_upload.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-upload`
  - 25 passed in 2.03s.
- `cd backend; .\venv311\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .test-tmp\pytest-full-aadhaar`
  - First run: 312 passed, 1 deselected, 1 pytest setup error because the `.test-tmp` parent directory did not exist.
  - After creating the temp parent: 313 passed, 1 deselected in 17.39s.
- Live read-only backend service lookup:
  - `AAD-10001`: `CIT-10001`, 6 records.
  - `AAD-10002`: `CIT-10002`, 3 records.
- `cd frontend; npm test -- AadhaarLinkPage.test.tsx`
  - First sandbox run failed with `spawn EPERM`.
  - Approved rerun: 1 file / 5 tests passed.
- `cd frontend; npm test -- wording.test.tsx`
  - 1 file / 9 tests passed.
- `cd frontend; npm run typecheck`
  - exit 0.
- `cd frontend; npm run lint`
  - exit 0 with the existing `SplashPage.tsx` exhaustive-deps warning.
- `cd frontend; npm test`
  - 22 files / 131 tests passed.
- `cd frontend; npm run build`
  - First sandbox run failed with `spawn EPERM`.
  - Approved rerun built successfully in 1.23s with the existing Vite large-chunk warning.

### Notes
- No commits, pushes, merges, schema changes, dependency additions, or environment variable additions were made.
- `screen.png` remains an untracked user-provided file and was not modified.

## 2026-10-10 Fix Pass

### Changes made
- Removed mobile linked-record sample assets from the whitelisted asset map.
- Removed old generated mobile preview files:
  - `aadhaar_link_mob_50001.png`
  - `aadhaar_link_mob_50002.jpg`
- Added two uploadable synthetic Aadhaar demo cards:
  - `aadhaar_demo_card_aad_10001.png`
  - `aadhaar_demo_card_aad_10002.png`
- Tightened upload validation so `POST /api/v1/aadhaar-link` accepts only DocuTrust synthetic Aadhaar demo cards carrying the embedded demo marker and an `AAD-10001`/`AAD-10002` reference.
- Removed the first-citizen fallback path. Missing Aadhaar references now return a clear `422`.
- Changed mobile rows to non-preview records in the frontend.
- Changed mobile display to extract a 10-digit value from the matching Supabase `display_value` only; if none exists, the UI shows the fallback `No fictional demo mobile number stored in Supabase`.
- Removed the Reference Level / Synthetic Level 3 summary card.

### Verification
- Live read-only Supabase check through the updated backend service:
  - `AAD-10001`: `CIT-10001`, 6 records, mobile fallback shown because the seeded row has no 10-digit number.
  - `AAD-10002`: `CIT-10002`, 3 records, mobile fallback shown because the seeded row has no 10-digit number.
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-link-fix`
  - 5 passed in 0.58s.
- `cd frontend; npm test -- AadhaarLinkPage.test.tsx`
  - 1 file / 5 tests passed.
- `cd frontend; npm run typecheck`
  - exit 0.
- `cd frontend; npm test -- wording.test.tsx`
  - 1 file / 9 tests passed.
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py tests\test_upload.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-upload-fix`
  - 25 passed in 1.88s.
- `cd frontend; npm run lint`
  - exit 0 with the existing `SplashPage.tsx` exhaustive-deps warning.
- `cd frontend; npm test`
  - 22 files / 131 tests passed.
- `cd backend; .\venv311\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .test-tmp\pytest-full-aadhaar-fix`
  - First run: 312 passed, 1 deselected, 1 pytest setup error because `.test-tmp` parent was missing.
  - Rerun after creating `.test-tmp`: 313 passed, 1 deselected in 17.03s.
- `cd frontend; npm run build`
  - built successfully in 423ms with the existing Vite large-chunk warning.

## 2026-10-10 Mobile Column Follow-Up

### Changes made
- Updated Aadhaar Link backend response to include `demo_citizens.mobile_number` as the citizen-level synthetic demo mobile placeholder.
- Updated the page summary chip to display that citizen-level value instead of depending on a `MOBILE` linked-document row.
- Kept the previous fallback behavior for any mobile linked-document row that lacks a citizen-level number.

### Verification
- Live read-only Supabase lookup through the backend service:
  - `AAD-10001`: `CIT-10001`, mobile `9000005001`.
  - `AAD-10002`: `CIT-10002`, mobile `9000005002`.
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-mobile2`
  - 5 passed in 0.76s.
- `cd frontend; npm test -- AadhaarLinkPage.test.tsx`
  - 1 file / 5 tests passed.
- `cd frontend; npm run typecheck`
  - exit 0.
- `cd frontend; npm run lint`
  - exit 0 with the existing `SplashPage.tsx` exhaustive-deps warning.
