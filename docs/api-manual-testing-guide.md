# API Manual Testing Guide (curl / Postman)

Use this to exercise the backend before the frontend is ready, or to debug a failing integration.
All examples assume `API_HOST=127.0.0.1`, `API_PORT=8000`.

## 1. Health

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## 2. Document types (should match `category-schemas.md` exactly)

```bash
curl http://127.0.0.1:8000/api/v1/document-types
```

## 3. Upload a fixture

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents \
  -F "file=@backend/app/fixtures/sample_documents/academic_certificate_match.png" \
  -F "category=academic_certificate"
```
Save the returned `document_id` for the next calls.

## 4. Check extraction (read-only — no polling needed)

> Processing is synchronous. `POST .../verify` in the next step runs OCR if it has not run yet, and
> returns a terminal status directly. This step is just for inspecting what OCR read.


```bash
curl http://127.0.0.1:8000/api/v1/documents/<document_id>
curl http://127.0.0.1:8000/api/v1/documents/<document_id>/extraction
```

## 5. Run verification

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents/<document_id>/verify
```
Save `verification_id`.

## 6. Read the verification result

```bash
curl http://127.0.0.1:8000/api/v1/verifications/<verification_id>
```
Expected for the `_match` fixture: `status: "VERIFIED_MATCH"`.
Expected for the `_mismatch` fixture: `status: "INTEGRITY_MISMATCH"` with a populated
`field_comparisons` entry showing `matched: false`.

## 7. Submit a review correction

```bash
curl -X POST http://127.0.0.1:8000/api/v1/verifications/<verification_id>/review \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_ref": "Test Reviewer",
    "action": "CORRECT",
    "corrections": { "semester_or_year": "5" },
    "comment": "manual test correction"
  }'
```
Follow up with:
```bash
curl http://127.0.0.1:8000/api/v1/verifications/<new_verification_id>
```

## 8. Check blockchain status

```bash
curl http://127.0.0.1:8000/api/v1/verifications/<verification_id>/blockchain
```
With `BLOCKCHAIN_ENABLED=false` this should return `recording_status: "NOT_REQUESTED"` immediately —
useful for testing the backend without starting the Hardhat node.

## 9. Negative-path checks worth running by hand

- Upload a `.txt` file → expect `415 UNSUPPORTED_MEDIA_TYPE`.
- Upload a file over `MAX_UPLOAD_MB` → expect `413 FILE_TOO_LARGE`.
- Verify a `document_id` with no successful extraction yet → expect `409 EXTRACTION_NOT_READY`.
- Fetch a verification with a random UUID → expect `404 VERIFICATION_NOT_FOUND`.
- Stop the local Hardhat node, then run step 5 on a new document with `BLOCKCHAIN_ENABLED=true` →
  verification status should still resolve normally; `blockchain` endpoint should show
  `recording_status: "FAILED"`.

## Suggested Postman collection layout

One folder per resource (`Health`, `Document Types`, `Documents`, `Verifications`, `Blockchain`),
mirroring the section order above, with the fixture files in step 3 attached as pre-saved form-data
examples so any teammate can replay the whole flow without re-typing paths.

## Known gaps to flag if you hit them

- If `POST /documents/{id}/verify` ever returns before extraction has actually finished (a race
  between the synchronous OCR call and the verify call), that's a bug against `architecture.md`'s
  request lifecycle — report it, don't work around it by adding a client-side sleep.
