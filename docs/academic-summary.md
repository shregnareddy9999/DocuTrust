# AI Academic Summary Feature

## Overview

The AI Academic Summary feature allows students to generate a concise academic summary from their uploaded academic marksheets and certificates. It uses a locally running Ollama LLM (llama3.2:latest) to process the OCR-extracted text from selected academic documents and produce a student-friendly summary.

This is a **demo feature using synthetic documents only**. It never uses real personal data, never claims document authenticity, and never creates fraud scores.

## Architecture

### Backend Components

```
backend/app/adapters/ai/
├── base.py              # AiAdapter interface & AcademicSummaryResult
├── ollama_adapter.py    # Real Ollama implementation
├── fake_adapter.py      # Deterministic fake for testing
└── __init__.py          # Factory function (get_ai_adapter)

backend/app/services/
└── academic_summary_service.py  # Business logic

backend/app/api/
└── academic_summary.py          # POST /api/v1/academic-summary
```

### Frontend Components

```
frontend/src/
├── api/academicSummary.ts       # API client
├── pages/AcademicSummaryPage.tsx # Main UI page
└── types/api.ts                 # TypeScript types (updated)
```

### Data Flow

1. User selects one or more academic documents on the Academic Summary page
2. Frontend calls `POST /api/v1/academic-summary` with document IDs
3. Backend validates:
   - All documents exist
   - All documents are `academic_certificate` category
   - All documents have successful OCR extractions
4. Backend retrieves OCR text from extraction results
5. Texts are combined with document separators
6. Combined text sent to AI adapter (Ollama or fake)
7. AI returns structured summary
8. Response returned to frontend for display

## API Contract

### POST /api/v1/academic-summary

**Request:**
```json
{
  "document_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response (200):**
```json
{
  "summary": "AI Academic Summary text...",
  "documents_analyzed": 3,
  "model": "llama3.2:latest"
}
```

**Error Responses:**
- `400 INVALID_REQUEST` - Empty document_ids array
- `404 DOCUMENT_NOT_FOUND` - Document doesn't exist
- `400 INVALID_DOCUMENT_TYPE` - Document is not academic_certificate
- `409 EXTRACTION_NOT_READY` - Document lacks successful extraction
- `422 NO_TEXT_AVAILABLE` - No OCR text in any selected document

## Configuration

### Environment Variables (backend/.env)

```bash
# AI Academic Summary
AI_ENGINE=ollama              # ollama | fake
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
AI_TIMEOUT_SECONDS=60
```

### Settings (backend/app/config.py)

The settings are validated at startup via Pydantic Settings. All variables are required when using `ollama` engine.

## AI Prompt

The internal prompt explicitly instructs the LLM:

- Use ONLY the supplied OCR text
- Do not invent or estimate missing information
- Do not infer grades, marks, CGPA, percentage, rank, attendance, achievements
- If information is unclear, say it is not available
- Produce a concise student-friendly academic summary
- Mention subjects/marks/grades only when actually present
- Summarize across multiple documents when provided
- Do not make authenticity or fraud claims
- Do not say documents are genuine, verified, fraudulent, or government-authenticated

## Testing

### Backend Tests

Run with pytest (uses fake adapter by default):

```bash
cd backend
python -m pytest tests/test_academic_summary.py -v
```

Tests cover:
- Successful summary generation (single & multiple documents)
- Document not found
- Non-academic document rejection
- Missing extraction
- Empty OCR text
- Empty request
- AI connection errors
- API endpoint contract tests

### Frontend Tests

```bash
cd frontend
npm test
```

## Demo Documents

The feature works with existing academic certificate fixtures. For demo purposes, the following synthetic documents can be used:

- `backend/app/fixtures/sample_documents/academic_certificate_match.png`
- `backend/app/fixtures/sample_documents/academic_certificate_mismatch.png`
- `backend/app/fixtures/sample_documents/academic_certificate_degraded.png`

These contain the demo student:
- **Name:** Aarav Demo
- **Student ID:** DEMO-2026-001
- **Institution:** Oriental University
- **Course:** B.Tech Computer Science and Engineering

All documents are clearly marked as `DOCUTRUST DEMO / SYNTHETIC DOCUMENT`.

## Security & Privacy

- No personal data ever sent to external services (Ollama runs locally)
- No document digests or raw OCR text stored on-chain
- Only synthetic demo data used
- Follows existing project rules (AGENTS.md Rules 2, 4, 6, 7)

## Integration Notes

- Minimal changes to existing codebase
- New isolated adapter pattern (follows OCR/blockchain pattern)
- No database schema changes
- No modifications to existing OCR, verification, or blockchain flows
- Frontend reuses existing `useRecentDocuments` hook and `SyntheticDataBanner`
- Route added at `/academic-summary` without breaking existing routes

## Future Considerations

- Add support for PDF multi-page documents
- Add streaming response for large documents
- Add summary history/cache
- Add export to PDF functionality