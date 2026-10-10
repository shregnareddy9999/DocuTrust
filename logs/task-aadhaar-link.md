# Aadhaar Link Demo Feature - Development Log

**Status:** Implemented locally, not committed or pushed.
**Scope:** Separate synthetic Aadhaar Link demo feature. No database schema changes, no new environment variables, no new dependencies, no changes to existing verification categories.

## 2026-10-10 CIT-10005 Sample Asset Generation

### Changes made
- Generated six fictional local sample assets for `CIT-10005` using the existing Aadhaar Link
  fixture rendering functions and the existing `backend/app/fixtures/sample_documents/` convention:
  - `aadhaar_demo_card_aad_10005.png` (`AAD-10005`)
  - `aadhaar_link_pan_20005.png` (`PAN-20005`)
  - `aadhaar_link_dl_30005.pdf` (`DL-30005`)
  - `aadhaar_link_brc_40005.pdf` (`BRC-40005`)
  - `aadhaar_link_bnk_60005.pdf` (`BNK-60005`)
  - `aadhaar_link_vtr_70005.png` (`VTR-70005`)
- No backend API, schema, dependency, environment, or frontend workflow changes were made.

### Verification
- Confirmed all six files exist under `backend/app/fixtures/sample_documents/`.
- Confirmed the Aadhaar demo card PNG metadata includes:
  - `DocuTrustDemoMarker: DOCUTRUST SYNTHETIC AADHAAR DEMO CARD`
  - `AadhaarDemoReference: AAD-10005`
  - `CitizenDemoReference: CIT-10005`

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

## 2026-10-10 Scalability Review Pass

### Changes made
- Removed the production upload recognition limit that only accepted `AAD-10001` and `AAD-10002`; synthetic Aadhaar demo cards now accept the `AAD-<5 to 12 digits>` reference shape and still require the DocuTrust demo marker.
- Removed hardcoded linked-record ordering from the backend response so Supabase result rows drive the linked-document list.
- Kept local sample previews as optional whitelisted demo assets only; Supabase rows without a matching local asset now remain listed with `asset_ref: null`.
- Added a frontend empty state for existing synthetic citizens with no linked records.
- Added backend tests for a Supabase-only third citizen/reference, unknown Aadhaar references, and citizens with no linked records.
- Added frontend coverage for the no-linked-records empty state.

### Verification
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-scalability`
  - First run: 1 failed, 7 passed.
  - Cause: PNG metadata binary bytes made the generalized word-boundary regex miss `AAD-10001`.
  - Fixed by using the documented synthetic numeric reference shape.
  - Rerun: 8 passed in 0.95s.
- `cd frontend; npm test -- AadhaarLinkPage.test.tsx`
  - First sandbox run failed with `spawn EPERM`.
  - Approved rerun: 1 file / 6 tests passed.
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py tests\test_upload.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-upload-scalability`
  - 28 passed in 3.07s.
- `cd frontend; npm run typecheck`
  - exit 0.
- `cd frontend; npm run lint`
  - exit 0 with the existing `SplashPage.tsx` exhaustive-deps warning.
- `cd backend; .\venv311\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .test-tmp\pytest-backend-aadhaar-scalability`
  - First run: 315 passed, 1 deselected, 1 pytest setup error because the `.test-tmp` parent directory did not exist.
  - Rerun after creating `.test-tmp`: 316 passed, 1 deselected in 21.60s.
- `cd frontend; npm test`
  - First sandbox run failed with `spawn EPERM`.
  - Approved rerun: 22 files / 132 tests passed.

### Remaining limitation
- Adding citizens and linked records in Supabase no longer requires production code changes, but uploadable sample Aadhaar cards are still generated by `backend/app/fixtures/generate_aadhaar_link_samples.py` as local demo assets. A new citizen must have a synthetic card generated with the DocuTrust marker and an `AAD-<digits>` reference that matches `demo_citizens.demo_aadhaar_ref`; otherwise the upload page cannot read the reference. Linked-record previews are optional and still require adding a whitelisted local asset if the demo should show an actual sample document preview.

## 2026-10-10 Dynamic Preview Asset Follow-Up

### Changes made
- Added convention-based preview discovery for Aadhaar Link linked records. A Supabase row with `demo_document_ref: "PAN-20004"` now resolves `backend/app/fixtures/sample_documents/aadhaar_link_pan_20004.png` without adding that ref to production code.
- Kept path safety by resolving only files under `backend/app/fixtures/sample_documents/` and only serving `.png`, `.jpg`, `.jpeg`, or `.pdf`.
- Updated the sample generator to read backend-only Supabase demo rows from `.env` and generate Aadhaar cards for all demo citizens plus PAN previews for all `PAN` linked rows.
- Generated current Supabase-driven assets:
  - `aadhaar_demo_card_aad_10003.png`
  - `aadhaar_demo_card_aad_10004.png`
  - `aadhaar_link_pan_20004.png`
- Restored pre-existing tracked sample assets that were refreshed by the generator but were unrelated to this request.

### Verification
- Live read-only Supabase lookup through the updated backend service:
  - `AAD-10004`: `CIT-10004`
  - `PAN-20004`: `asset_ref` is `PAN-20004`, `asset_mime_type` is `image/png`
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-dynamic-assets`
  - 10 passed in 1.27s.
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py tests\test_upload.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-dynamic-upload`
  - 30 passed in 3.09s.

### Remaining limitation
- Supabase can add citizens and linked PAN rows without code changes, and the generator can create matching local demo samples for them. Non-PAN linked record previews still need either a local file following the `aadhaar_link_<lowercase_ref_with_underscores>.<png|jpg|jpeg|pdf>` convention or a future generator template for that document type.

## 2026-10-10 Mocked SMS and Voice Reminder Workflow

### Changes made
- Added a fake-provider-only Aadhaar Link messaging workflow behind `AADHAAR_MESSAGING_ENABLED=false` and `AADHAAR_MESSAGING_PROVIDER=fake`.
- Added Supabase bearer authentication for `POST /api/v1/aadhaar-link/{citizen_ref}/message`.
- Added backend server-side recipient resolution from the synthetic `demo_citizens` record; the frontend never supplies a trusted phone number.
- Added in-memory duplicate/rate protection keyed by authenticated user, citizen, and request idempotency key.
- Added the SMS-first flow: the fake voice reminder is attempted only when the fake SMS provider returns `accepted`.
- Added safe API responses with separate `sms_status` and `voice_status` values and only masked mobile numbers.
- Added an Aadhaar Link SMS icon button, accessible composer dialog, masked recipient display, custom-message textarea, character count, confirmation step, loading state, and safe success/error messages.
- Updated `docs/api.md`, `docs/configuration.md`, `docs/security-privacy.md`, and `backend/.env.example` for the new mocked-only contract and configuration.

### Verification
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py tests\test_config.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-message`
  - First complete run: 27 passed in 1.41s.
  - Rerun after adding invalid-token coverage: 28 passed in 1.19s.
- `cd frontend; npm test -- AadhaarLinkPage.test.tsx`
  - First sandbox run failed with `spawn EPERM`.
  - Approved rerun after test assertion fixes: 1 file / 10 tests passed.
- `cd frontend; npm run typecheck`
  - exit 0.

### Remaining limitation
- Messaging remains mocked only. No real SMS messages or voice calls are sent.
- Duplicate/rate safeguards are in memory for the demo and reset on backend restart or across separate worker processes.
- The endpoint authorizes only valid Supabase-authenticated users because the MVP has no approved role table or employee-permission schema.

## 2026-10-10 Twilio Real Provider Integration

### Changes made
- Added a real Twilio provider for the existing Aadhaar Link messaging workflow using backend-only credentials and existing `httpx`; no dependency was added.
- Kept the existing API request/response shape while changing runtime provider selection to `AADHAAR_MESSAGING_PROVIDER=twilio|fake`.
- Kept `AADHAAR_MESSAGING_ENABLED=false` as the default opt-in guard.
- Reused existing backend-only `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_PHONE_NUMBER` settings.
- Added fail-fast settings validation when Twilio messaging is enabled without required Twilio credentials.
- SMS is submitted first through Twilio Messages; the voice call request is submitted through Twilio Calls with inline TwiML only after SMS request acceptance.
- Updated response wording to distinguish provider request acceptance from delivery or call completion.
- Kept automated tests on fake/mocked providers; no test sends a real SMS or places a real call.
- Updated `docs/api.md`, `docs/configuration.md`, `docs/security-privacy.md`, and `backend/.env.example`.

### Verification
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py tests\test_config.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-twilio`
  - 32 passed in 1.37s.
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py tests\test_config.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-twilio-env`
  - First run after enabling local `.env` messaging flags: 1 failed, 31 passed.
  - Cause: test settings were inheriting real local `.env` messaging flags.
  - Fixed by explicitly disabling messaging in the backend test settings fixture unless a test opts in.
  - Rerun: 32 passed in 1.15s.
- `cd frontend; npm test -- AadhaarLinkPage.test.tsx`
  - First sandbox run failed with `spawn EPERM`.
  - Approved rerun: 1 file / 10 tests passed.
- `cd frontend; npm run typecheck`
  - exit 0.

### Remaining limitation
- Real SMS/call delivery depends on Twilio account state, sender/caller capabilities, recipient eligibility, geographic permissions, and India SMS/voice compliance. The endpoint reports Twilio request acceptance only.
- Duplicate/rate safeguards remain in memory for the demo and reset on backend restart or across separate worker processes.

## 2026-10-10 Voice Prompt Text Update

### Changes made
- Updated the Aadhaar Link voice reminder prompt only:
  - `namashkar, ap please apka sms dekhiye. namaste, please check your sms.`
- Kept the existing SMS-first Twilio workflow, API shape, authentication, and server-side recipient lookup unchanged.

### Verification
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_aadhaar_link.py tests\test_config.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-aadhaar-voice-text`
  - 32 passed in 1.22s.
