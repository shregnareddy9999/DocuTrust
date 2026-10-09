# AI Academic Summary

This is an isolated demo feature for synthetic academic documents. It summarizes OCR/extraction
data that DocuTrust has already produced for selected `academic_certificate` documents.

It does not change the verification pipeline, registry matching, review history, blockchain
recording, or database schema.

## Flow

1. The frontend sends selected document IDs to `POST /api/v1/academic-summary`.
2. The backend validates that every document exists and has category `academic_certificate`.
3. The backend reads the latest successful `extraction_results` row for each document, or runs the
   existing OCR/extraction path once if the uploaded academic document has not been processed yet.
4. The service combines only OCR text or extracted field values.
5. The Ollama adapter sends that text to local Ollama at `AI_SUMMARY_OLLAMA_URL`.
6. The response returns `{ summary, documents_analyzed, model }`.

No summary row is stored. Re-running the endpoint generates a fresh summary from current persisted
extraction data.

## Preview and deletion

The Academic Summary page can preview the original uploaded file through
`GET /api/v1/documents/{document_id}/file`. The endpoint returns file bytes for the selected
document and does not expose local storage paths.

The page can delete a document through `DELETE /api/v1/documents/{document_id}` only when the
document has no verification history. Documents with verification/review/blockchain history are
rejected with `DOCUMENT_HAS_HISTORY` to preserve the audit trail.

## Local model

Default model: `llama3.2:latest`

Default local URL: `http://localhost:11434`

The default test suite uses `FakeAcademicSummaryAdapter`; tests must not require a running Ollama
server.

## Prompt boundaries

The internal prompt instructs the model to:

- use only the supplied OCR text and extracted document information;
- not invent or estimate missing information;
- not infer grades, marks, CGPA, percentages, ranks, attendance, achievements, or academic
  performance unless explicitly present;
- say when information is unclear or unavailable in the submitted documents;
- avoid authenticity, fraud, government-authentication, or verdict claims.

## Fixture data

The academic summary demo fixtures are synthetic marksheet images:

- `backend/app/fixtures/sample_documents/academic_summary_semester_1.png`
- `backend/app/fixtures/sample_documents/academic_summary_semester_2.png`
- `backend/app/fixtures/sample_documents/academic_summary_semester_3.png`

They use fictional demo data:

- Name: `Aarav Demo`
- Student ID: `DEMO-2026-001`
- Institution: `Oriental University`
- Course: `B.Tech Computer Science and Engineering`

Each image is clearly marked `DOCUTRUST DEMO / SYNTHETIC DOCUMENT`.
