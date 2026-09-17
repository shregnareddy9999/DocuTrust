# API Contract

Base path: `/api/v1`. All bodies are JSON except `POST /documents` (multipart). This contract is
**locked** — resolves former decision D-10. Any change requires a project-lead-approved doc update
in the same PR as the code change.

## Conventions

- IDs are opaque UUID strings. Clients never construct them.
- All timestamps are ISO-8601 UTC (`2026-09-16T10:00:00Z`).
- Every response that represents "no trusted record" or "review required" is a normal `200`, not an
  error — these are valid business outcomes (`requirements.md` FR-08).

## Error envelope (every non-2xx response)

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```
Never include a stack trace, file path, or raw exception text in `message`. `code` is one of a
closed set defined per-endpoint below plus the generic `INTERNAL_ERROR` (500, includes a
`correlation_id` in `details`).

---

## `GET /health`

`200`
```json
{ "status": "ok", "database": "ok", "ocr_adapter": "configured", "blockchain": "enabled|disabled" }
```
Never leaks secrets, connection strings, or file paths.

## `GET /document-types`

`200` — array sourced exactly from `category-schemas.md`:
```json
[
  {
    "category": "academic_certificate",
    "label": "Academic Certificate",
    "fields": [
      { "name": "student_name", "label": "Student Name", "type": "text", "required": true, "match_field": true }
    ]
  }
]
```

## `POST /documents`

Multipart form: `file` (binary), `category` (string, must be one of the 4 locked categories).

`201`
```json
{ "document_id": "uuid", "category": "academic_certificate", "processing_state": "UPLOADED" }
```

Errors: `400 INVALID_CATEGORY`, `413 FILE_TOO_LARGE`, `415 UNSUPPORTED_MEDIA_TYPE`,
`422 EMPTY_OR_CORRUPT_FILE`.

## `GET /documents/{document_id}`

`200`
```json
{
  "document_id": "uuid",
  "category": "academic_certificate",
  "original_filename": "marksheet.pdf",
  "processing_state": "OCR_DONE",
  "uploaded_at": "2026-09-16T10:00:00Z"
}
```
`404 DOCUMENT_NOT_FOUND` if unknown.

## `GET /documents/{document_id}/extraction`

`200`
```json
{
  "document_id": "uuid",
  "engine_name": "paddleocr",
  "engine_version": "2.8.1",
  "extracted_fields": {
    "student_name": { "value": "Aarav Demo", "confidence": 0.94, "source": "ocr" }
  },
  "warnings": ["low_confidence:certificate_or_marksheet_id"],
  "status": "SUCCEEDED"
}
```
`404 DOCUMENT_NOT_FOUND`; `409 EXTRACTION_NOT_READY` if `processing_state` is still `OCR_IN_PROGRESS`
(only reachable when a concurrent request is mid-run — see `document-processing.md` §"Processing-state contract");
`200` with `status: "FAILED"` and `warnings` describing the failure if OCR failed (this is not a 4xx —
see `architecture.md` failure isolation table).

## `POST /documents/{document_id}/verify`

No body required. If no successful extraction exists yet, this call runs OCR and extraction first —
see `document-processing.md` §"Processing-state contract" for the full sequence. The response always
carries a **terminal** status; `PENDING` is never returned. Runs matching + rules synchronously for
MVP and returns the result directly.

`200`
```json
{
  "verification_id": "uuid",
  "status": "VERIFIED_MATCH",
  "document_id": "uuid"
}
```
`404 DOCUMENT_NOT_FOUND`; `409 EXTRACTION_NOT_READY` if there is no successful extraction to verify.

## `GET /verifications/{verification_id}`

`200`
```json
{
  "verification_id": "uuid",
  "document_id": "uuid",
  "status": "INTEGRITY_MISMATCH",
  "registry_record_key": "DEMO-STU-001",
  "field_comparisons": [
    { "field": "semester_or_year", "extracted_value": "6", "registry_value": "5", "matched": false }
  ],
  "rule_results": [
    { "rule_id": "required_field_presence", "passed": true, "reason": "" },
    { "rule_id": "field_match", "passed": false, "reason": "semester_or_year does not match registry record DEMO-STU-001" }
  ],
  "reason_codes": ["FIELD_MISMATCH:semester_or_year"],
  "is_current": true,
  "supersedes_verification_id": null,
  "review_actions": [
    {
      "review_action_id": "uuid",
      "reviewer_ref": "demo-reviewer",
      "action": "CORRECT",
      "corrections": { "student_id": "DEMO-STU-001" },
      "comment": "OCR read O instead of 0",
      "created_at": "2026-09-16T10:02:00Z"
    }
  ],
  "created_at": "2026-09-16T10:01:00Z"
}
```
`404 VERIFICATION_NOT_FOUND`.

`review_actions` is always present and is `[]` when none exist. It lists the actions taken **on this
verification** — so on a superseded row, not on the row a correction produced
(`data-model.md` §"Which verification is current").

## `GET /documents/{document_id}/verifications`

Returns every verification for a document, **newest first**, so the UI can show the current result
and the history behind it without re-deriving "latest" itself.

`200`
```json
{
  "document_id": "uuid",
  "verifications": [
    {
      "verification_id": "uuid-B",
      "status": "VERIFIED_MATCH",
      "is_current": true,
      "supersedes_verification_id": "uuid-A",
      "review_action_count": 0,
      "created_at": "2026-09-16T10:03:00Z"
    },
    {
      "verification_id": "uuid-A",
      "status": "REVIEW_REQUIRED",
      "is_current": false,
      "supersedes_verification_id": null,
      "review_action_count": 1,
      "created_at": "2026-09-16T10:01:00Z"
    }
  ]
}
```
`404 DOCUMENT_NOT_FOUND`.

Exactly one entry has `is_current: true`. It is the greatest `created_at`, per
`data-model.md` §"Which verification is current" — which is the **only** definition of current in
this project.

## `POST /verifications/{verification_id}/review`

```json
{
  "reviewer_ref": "Priya (Reviewer)",
  "action": "CORRECT",
  "corrections": { "semester_or_year": "5" },
  "comment": "OCR misread 6-column table; source clearly shows 5"
}
```
`action` ∈ `{"ACCEPT", "CORRECT", "UNRESOLVED"}`. `corrections` required only when `action = CORRECT`.

`201`
```json
{
  "review_action_id": "uuid",
  "new_verification_id": "uuid",
  "new_status": "VERIFIED_MATCH"
}
```
A `CORRECT` action always creates a **new** `verification_results` row (re-run with corrected
values) rather than mutating the existing one — `data-model.md`. `400 INVALID_ACTION`,
`404 VERIFICATION_NOT_FOUND`, `422 MISSING_CORRECTIONS`.

## `GET /verifications/{verification_id}/blockchain`

`200`
```json
{
  "verification_id": "uuid",
  "recording_status": "CONFIRMED",
  "chain_id": 31337,
  "contract_address": "0x...",
  "transaction_hash": "0x...",
  "event_digest": "0x...",
  "submitted_at": "2026-09-16T10:02:00Z",
  "confirmed_at": "2026-09-16T10:02:03Z",
  "error_code": null
}
```

When `recording_status: "FAILED"`, `error_code` is one of `RPC_UNAVAILABLE`, `TX_REVERTED`,
`RECEIPT_TIMEOUT`, `EVENT_MISMATCH` (`blockchain.md`), `confirmed_at` is `null`, and
`transaction_hash` is present only if a transaction was actually submitted before failing (null for
`RPC_UNAVAILABLE`, present for the other three). This field exists specifically so a failure is
diagnosable from the API alone, without reading server logs.

If `BLOCKCHAIN_ENABLED=false`: `200` with `recording_status: "NOT_REQUESTED"` and every other field
`null`, including `error_code`. `404 VERIFICATION_NOT_FOUND` only if the verification itself doesn't
exist.

---

## HTTP status summary

`200` read/verify success · `201` resource created (upload, review action) · `400` malformed
request/category/action · `404` unknown resource · `409` operation not valid in current state ·
`413` upload exceeds limit · `415` unsupported file type · `422` semantically invalid payload ·
`500` unexpected internal error (generic message + `correlation_id`).

## Contract rules

- `NO_TRUSTED_RECORD` and `REVIEW_REQUIRED` are `200` responses, never errors.
- Blockchain failure is visible only via `blockchain_records`/the blockchain endpoint — it never
  changes the HTTP status or body of any verification endpoint.
- The frontend must render every field list from `GET /document-types`, never a hardcoded copy.
