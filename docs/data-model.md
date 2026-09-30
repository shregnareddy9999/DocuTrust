# Data Model

Storage: SQLite at `data/app.db` via SQLAlchemy. Files live under `UPLOAD_DIR`, never as DB blobs.
All primary keys are UUID strings (`uuid4().hex`). Synthetic fixture rows use a human-readable key
prefixed `DEMO-` (e.g., `DEMO-STU-001`) so they are visibly not real records.

## `documents`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `category` | str, enum (`academic_certificate`, `institutional_id`, `pan_like_demo`, `government_certificate`) | matches `category-schemas.md` |
| `original_filename` | str | for display only; never used to build a filesystem path |
| `storage_key` | str | server-generated filename actually written under `UPLOAD_DIR` |
| `sha256` | str | over the original uploaded bytes |
| `mime_type` | str | from content sniffing, not the client-supplied header alone |
| `byte_size` | int | |
| `page_count` | int | 1 for images |
| `processing_state` | str, enum (`UPLOADED`, `OCR_IN_PROGRESS`, `OCR_DONE`, `OCR_FAILED`) | |
| `uploaded_at` | datetime | |

## `extraction_results`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `document_id` | UUID FK → documents | |
| `engine_name` | str | `"paddleocr"` |
| `engine_version` | str | recorded at run time from the installed package |
| `raw_ocr_json` | text (JSON) | full raw OCR output, retention-controlled (`RETENTION_DAYS`) |
| `extracted_fields_json` | text (JSON) | `{field_name: {value, confidence, source: "ocr"|"corrected"}}` |
| `warnings_json` | text (JSON) | list of warning strings |
| `status` | str, enum (`SUCCEEDED`, `FAILED`) | |
| `created_at` | datetime | |

## `registry_records`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `category` | str | same enum as `documents.category` |
| `synthetic_record_key` | str | e.g., `DEMO-STU-001`; unique per category |
| `fields_json` | text (JSON) | the trusted field values for this fixture, per `category-schemas.md` |
| `source_label` | str | always `"synthetic-demo"` — never changed |
| `active` | bool | inactive records are excluded from matching |
| `created_at` / `updated_at` | datetime | |

## `verification_results`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `document_id` | UUID FK → documents | |
| `registry_record_id` | UUID FK → registry_records, nullable | null when `NO_TRUSTED_RECORD` |
| `status` | str, enum — see `verification-rules.md` (`PENDING`, `VERIFIED_MATCH`, `REVIEW_REQUIRED`, `NO_TRUSTED_RECORD`, `INTEGRITY_MISMATCH`, `PROCESSING_FAILED`) | |
| `field_comparisons_json` | text (JSON) | list of `{field, extracted_value, registry_value, matched: bool}` |
| `rule_results_json` | text (JSON) | list of `{rule_id, passed: bool, reason}` |
| `reason_codes_json` | text (JSON) | short machine-readable codes summarizing why the status was assigned |
| `supersedes_verification_id` | UUID FK → verification_results, nullable | set when this row was produced by re-evaluating a prior verification (a `CORRECT` review); null for a first verification. Makes the chain explicit rather than inferred from timestamps |
| `created_at` | datetime | a new row is written on every re-run; see "Which verification is current" below |

### Which verification is current (resolves D-23)

**The current verification for a document is the row with the greatest `created_at` for that
`document_id`.** Ties are broken by insert order. Nothing is ever mutated or deleted to make this
true — superseded rows keep their original status, comparisons, and reason codes forever
(`decisions.md` D-18).

Two rules follow, and both are binding:

- Every consumer uses the **same** definition. `verification_repo.get_latest_for_document()` is the
  single implementation; no service, router, or frontend hook may compute "latest" its own way.
  Contributors independently reinventing this is exactly how two parts of the app end up disagreeing
  about which result is real.
- `supersedes_verification_id` records *why* a row exists, and `GET /documents/{id}/verifications`
  (`api.md`) exposes the full chain newest-first with `is_current` marked. The UI never infers the
  prior result by re-sorting timestamps client-side.

Review actions attach to the verification row that was **reviewed** — that is, the superseded one,
not the row the correction produced. So the history a user reads is: verification A
(`REVIEW_REQUIRED`) → review action on A → verification B (`VERIFIED_MATCH`,
`supersedes_verification_id = A`).

## `review_actions`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `verification_id` | UUID FK → verification_results | the verification row being reviewed |
| `reviewer_ref` | str | free-text name for MVP (`security-privacy.md` D-11) |
| `action` | str, enum (`ACCEPT`, `CORRECT`, `UNRESOLVED`) | |
| `corrections_json` | text (JSON), nullable | `{field_name: new_value}`; only set when `action = CORRECT` |
| `comment` | str, nullable | |
| `created_at` | datetime | |

A `CORRECT` action never overwrites `extraction_results.extracted_fields_json`'s original OCR
values — it adds a new field entry with `source: "corrected"` and triggers
`verification_service` to write a **new** `verification_results` row referencing the same document,
so the OCR-only outcome remains in history.

## `blockchain_records`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `verification_id` | UUID FK → verification_results | |
| `chain_id` | int | from the local Hardhat network config |
| `contract_address` | str | |
| `transaction_hash` | str, nullable | set once submitted |
| `event_digest` | str | see `blockchain.md` for exact construction |
| `recording_status` | str, enum (`NOT_REQUESTED`, `PENDING`, `CONFIRMED`, `FAILED`) | |
| `submitted_at` / `confirmed_at` | datetime, nullable | |
| `error_code` | str, nullable | set when `recording_status = FAILED`; one of `RPC_UNAVAILABLE`, `TX_REVERTED`, `RECEIPT_TIMEOUT`, `EVENT_MISMATCH` (`blockchain.md`); exposed via `GET /verifications/{id}/blockchain` (`api.md`) |

## Relationships

- `documents` 1—many `extraction_results` (normally one, but re-OCR is not disallowed).
- `documents` 1—many `verification_results` (one per verify/re-verify run).
- `verification_results` 0/1—1 `registry_records` (nullable FK).
- `verification_results` 1—many `review_actions`.
- `verification_results` 1—0/1 `blockchain_records` — "current" is the latest row; retries create a
  new row rather than overwriting, so a failed-then-retried submission stays traceable.

## Retention (resolves D-12)

- `extraction_results.raw_ocr_json` and uploaded files under `UPLOAD_DIR` are retained for
  `RETENTION_DAYS` (default `7`, see `configuration.md`), after which a provided cleanup script
  (`backend/app/fixtures/cleanup_expired.py` — see Task 12) deletes the file and blanks
  `raw_ocr_json` while leaving `extracted_fields_json` and all verification/review/blockchain rows
  intact for audit purposes.
- Synthetic registry rows and demo fixtures are exempt from retention deletion.
- This applies to the MVP demo environment only; a production deployment needs a real data-retention
  and deletion policy signed off by whoever owns compliance for that deployment — explicitly out of
  scope here.

## Important rule

No column on `blockchain_records`, nor the on-chain event itself, may ever contain a document byte,
raw OCR text, or a value from `extracted_fields_json` / `fields_json`. See `blockchain.md` for the
exact allowed payload.

---

## Core extension: students, government records, marksheet history (PROPOSED — needs project-lead approval)

Additive only: no existing table or column is changed. All rows are synthetic demo data
(`source_label = "synthetic-demo"`, `DEMO-` identifiers).

### `students`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `student_ref` | str, unique | e.g. `DEMO-STU-101` |
| `display_name` | str | obviously fictional (e.g. `Aarav Demo`) |
| `aadhaar_hash` | str, nullable | one-way hash; the raw number is never stored |
| `aadhaar_last4` | str(4), nullable | used only to display `XXXX XXXX 1234` |
| `source_label` | str | always `"synthetic-demo"` |
| `created_at` | datetime | |

### `student_documents` (link table — `documents` is not modified)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `student_id` | FK → students | |
| `document_id` | FK → documents | unique together with `student_id` |
| `version` | int | 1, 2, 3… per student + document category; older links are never removed |
| `linked_at` | datetime | |

### `government_records`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `student_id` | FK → students | |
| `record_type` | str | e.g. `Caste Certificate (demo)` |
| `fields_json` | text (JSON) | structured data, not a raw file |
| `is_synthetic` | bool | always true in the MVP |
| `source_label` | str | `"synthetic-demo"` |
| `created_at` | datetime | |

### `marksheets`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | one row per marksheet; a new marksheet never overwrites an old one |
| `student_id` | FK → students | |
| `semester` | int | |
| `subjects_json` | text (JSON) | `{subject: marks}` |
| `total` / `cgpa` | float, nullable | |
| `source_label` | str | `"synthetic-demo"` |
| `uploaded_at` | datetime | |

Reviewer corrections continue to use the existing `review_actions` flow; no separate corrections
table is introduced. Nothing in these tables is ever written on-chain.
