# Architecture

## Locked stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | React + Vite + TypeScript | Plain fetch/axios, no state-management library required for MVP scope |
| Backend | Python 3.11+ + FastAPI + Uvicorn | |
| ORM/DB | SQLAlchemy + SQLite (file `data/app.db`) | See `decisions.md` D-08 |
| OCR | PaddleOCR (PP-OCRv4 or later available in the pinned version), English only for MVP | CPU inference |
| Image/PDF handling | Pillow, OpenCV (preprocessing), `pypdfium2` or `pdf2image` for page rendering | Pin exact library during Task 01 environment check |
| Hashing | Python `hashlib` (SHA-256) | |
| Blockchain | Solidity ^0.8.24 contract, Hardhat local network, Web3.py backend client | See `decisions.md` D-05 |
| Tests | `pytest` + FastAPI `TestClient` (backend), `vitest` + React Testing Library (frontend) | |

Exact package versions are pinned in `backend/requirements.txt` and `frontend/package.json` only
after the Task 01 compatibility check (`setup.md`) — do not hardcode versions in prose docs.

## Logical components

1. **Frontend (`frontend/`)** — upload flow, document detail view, verification result view, review
   console, blockchain receipt view. See `frontend.md`.
2. **API layer (`backend/app/api/`)** — FastAPI routers; validates requests, calls services, returns
   the schemas frozen in `api.md`. Never contains business logic.
3. **Service layer (`backend/app/services/`)** — orchestrates a use case (e.g., "process an upload")
   by calling domain logic and repositories. See `backend.md`.
4. **Domain layer (`backend/app/domain/`)** — category schemas, normalization, matching, rule
   evaluation. Pure Python; no FastAPI, PaddleOCR, or Web3 imports.
5. **Adapters (`backend/app/adapters/`)** — OCR adapter (PaddleOCR) and blockchain adapter (Web3.py),
   each behind a small interface so tests can substitute a fake.
6. **Repositories (`backend/app/repositories/`)** — SQLAlchemy queries only; no business logic.
7. **Database (`data/app.db`)** — metadata, extraction results, registry fixtures, verification
   results, review actions, blockchain records. See `data-model.md`.
8. **Chain (`chain/`)** — Solidity contract + Hardhat project, run as a separate local process.

## Dependency direction (enforced)

```
frontend  →  API routers  →  services  →  domain logic (pure)
                                  ↓
                            repositories  →  SQLite
                                  ↓
                              adapters  →  PaddleOCR / local chain (external processes)
```

Domain logic (`backend/app/domain/`) must never import FastAPI, PaddleOCR, or Web3 directly — it
receives plain Python data and returns plain Python data, which is what makes it unit-testable
without any of those dependencies running. This is checked in code review, not by tooling, for the
MVP.

## Trust boundaries

| Boundary | Trust level | Handling |
|---|---|---|
| Uploaded file bytes | Untrusted | Validated at the API boundary (`security-privacy.md`) before anything reads it |
| OCR output | Untrusted (may be wrong) | Never used to "prove" anything by itself; always paired with confidence/warnings |
| Synthetic registry | Trusted, but only as a demo fixture | Never described as an external/government source in the UI |
| Local chain RPC | External local process, may be down | Failure is a chain-status value, never a verification-status value |
| Reviewer input | Semi-trusted (a human, but not authenticated in MVP) | Recorded with a name/timestamp; original OCR is never overwritten |

## Failure isolation table

| Failure | Resulting state |
|---|---|
| Upload rejected (validation) | No document record created; `4xx` at the API boundary |
| OCR raises / times out | `extraction_results.status = FAILED`; verification is not attempted; `PROCESSING_FAILED` |
| OCR returns text but confidence is low / fields ambiguous | Extraction succeeds; verification proceeds and lands on `REVIEW_REQUIRED` |
| No registry record for the category+key fields | `NO_TRUSTED_RECORD` — never treated as evidence of anything wrong |
| Registry lookup itself errors (e.g., DB error) | `PROCESSING_FAILED`, distinct from "no record found" |
| A documented rule finds a mismatch | `INTEGRITY_MISMATCH` with the specific reason |
| Chain RPC unreachable / tx reverts / timeout | `blockchain_records.recording_status = FAILED`; `verification_results.status` is unchanged |

## Request lifecycle (upload → result)

1. `POST /documents` — API validates file, creates `documents` row, stores file, returns `document_id`.
2. Background task (or synchronous call for MVP simplicity — see Task 04/05) runs preprocessing + OCR
   → writes `extraction_results` row.
3. `POST /documents/{id}/verify` — service loads the extraction, maps to the category schema, queries
   the registry, runs rule evaluation, writes `verification_results`, and (if `BLOCKCHAIN_ENABLED`)
   submits a chain event via the blockchain adapter, writing a `blockchain_records` row.
4. Frontend re-fetches `GET /verifications/{id}` and `GET /verifications/{id}/blockchain`
   (no polling — verify is synchronous and returns a terminal status;
   `document-processing.md` §"Processing-state contract")
   to render the final dashboard.

## Explicit tradeoffs

- **Synchronous vs. background processing for OCR:** MVP runs OCR synchronously inside the upload/verify
  call path for simplicity and demo predictability; a background task queue (Celery/RQ) is a
  post-MVP improvement if OCR latency becomes a problem during rehearsal.
- **SQLite vs. Postgres:** SQLite is sufficient because there is no real concurrent multi-user load in
  a demo; see `decisions.md` D-08.
- **Local dev chain vs. testnet:** a local Hardhat network keeps the demo self-contained (no internet
  dependency, no faucet, instant confirmations) at the cost of not being a "real" chain; this is
  documented, not hidden (`problem-statement-mapping.md`).
