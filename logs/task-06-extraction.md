# Task 06 — Category-specific field extraction

## Date
2026-09-21

## Status
Core implementation complete; integration blocked by prerequisite task stubs.

## Completed

- Added deterministic schema registry for:
  - academic_certificate
  - institutional_id
  - pan_like_demo
  - government_certificate
- Added category-specific field definitions.
- Implemented OCR-to-schema field mapping.
- Every schema field is always present in extracted output.
- Missing required fields produce `missing_field:<name>` warnings.
- Existing OCR warnings are preserved.
- OCR confidence is preserved unchanged.
- Extraction source is `ocr`.
- Date validation accepts `YYYY-MM-DD` and preserves invalid OCR values with warnings.
- Synthetic demo PAN validation rejects the real PAN shape and accepts six-character demo codes.
- Extraction does not invent values.
- Added `GET /document-types` router using the schema registry.
- Added Task 06 unit tests.

## Verification

Command:

    python -m pytest tests/test_extraction.py -v

Result:

    16 passed

Schema package and extraction service also compile successfully.

## Integration blockers

The current checkout still contains prerequisite task stubs:

- Task 01: `backend/app/main.py`
- Task 02: extraction model/repository
- Task 04: document API/model integration
- Task 05: OCR adapter contract

Task 06 did not modify files owned by those tasks.

`GET /document-types` is implemented in:

    backend/app/api/document_types.py

Router registration in `main.py` is intentionally deferred until the Task 01 application is implemented.

Database-backed `extract_fields(document_id, session)` integration is intentionally deferred until the Task 02 extraction repository/model contract is available.

## Scope

Modified only Task 06-owned implementation/test files.

No commit or push performed.
