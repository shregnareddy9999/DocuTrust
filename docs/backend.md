# Backend Structure (FastAPI)

This is the locked folder layout. Any new file goes in one of these locations; a genuinely new
top-level folder requires project-lead approval (it's a shared-contract change).

```text
backend/
  app/
    main.py                     # FastAPI() app, router registration, startup/shutdown hooks
    config.py                   # loads/validates environment variables into a Settings object
    db.py                       # SQLAlchemy engine/session, Base
    api/
      health.py                 # GET /health
      document_types.py         # GET /document-types
      documents.py               # POST /documents, GET /documents/{id}, GET /documents/{id}/extraction
      verifications.py           # POST /documents/{id}/verify, GET /verifications/{id},
                                  # POST /verifications/{id}/review, GET /verifications/{id}/blockchain
    services/
      upload_service.py          # validate + store file, create Document row
      ocr_service.py              # preprocessing + OCR orchestration, writes ExtractionResult
      extraction_service.py       # maps OCR output to category schema (calls domain/schemas)
      verification_service.py     # orchestrates matching + rules, writes VerificationResult
      review_service.py           # applies a reviewer action, writes ReviewAction, re-triggers rules
      blockchain_service.py       # builds the event payload, calls the blockchain adapter
    domain/
      schemas/
        __init__.py
        academic_certificate.py   # field list + validators for this category
        institutional_id.py
        pan_like_demo.py
        government_certificate.py
      normalization.py            # whitespace/case/date normalization rules (verification-rules.md)
      matching.py                 # field-by-field comparison against a registry record
      rules.py                    # deterministic rule engine + status precedence
      status.py                   # the fixed status enums (never redefined elsewhere)
    adapters/
      ocr/
        base.py                   # OcrAdapter interface (run(image) -> OcrResult)
        paddleocr_adapter.py       # real implementation
        fake_adapter.py            # deterministic canned responses, used in tests
      blockchain/
        base.py                   # BlockchainAdapter interface (submit_event, get_receipt)
        web3_adapter.py             # real implementation (Web3.py + Hardhat local network)
        fake_adapter.py             # deterministic canned responses, used in tests
    repositories/
      documents_repo.py
      extraction_repo.py
      registry_repo.py
      verification_repo.py
      review_repo.py
      blockchain_repo.py
    models/
      __init__.py
      document.py                 # SQLAlchemy model: documents
      extraction.py                 # extraction_results
      registry.py                    # registry_records
      verification.py                 # verification_results
      review.py                        # review_actions
      blockchain.py                     # blockchain_records
    fixtures/
      seed_registry.py             # populates registry_records with the synthetic demo data
      sample_documents/            # synthetic PDFs/images used by the seed script and tests
  tests/
    conftest.py                    # fixtures: temp DB, fake OCR adapter, fake blockchain adapter
    test_upload.py
    test_ocr_pipeline.py
    test_extraction.py
    test_matching_rules.py
    test_review.py
    test_blockchain_adapter.py
    test_api_documents.py
    test_api_verifications.py
  requirements.txt
  .env.example
  pytest.ini
```

## Module responsibilities (one-line contract each)

- **`api/*`** — HTTP concerns only: parse request, call exactly one service method, map the result to
  the response schema in `api.md`, map exceptions to the error envelope. No business logic here.
- **`services/*`** — one method per use case; coordinates domain + repositories + adapters; the only
  layer allowed to call more than one repository or an adapter.
- **`domain/*`** — pure functions/classes; given plain data in, returns plain data out; fully
  unit-testable with no DB, no FastAPI, no PaddleOCR, no Web3 import.
- **`adapters/*`** — the *only* place PaddleOCR or Web3.py is imported. Both have a `fake_*` sibling
  used by default in tests (`NFR-05`).
- **`repositories/*`** — SQLAlchemy query functions only, one file per entity; no cross-entity
  business rules here (that's a service's job).
- **`models/*`** — SQLAlchemy ORM classes matching `data-model.md` exactly, field-for-field.

## Startup sequence (`main.py`)

1. Load and validate `Settings` from environment (`config.py`) — fail fast with a clear message on
   any missing/invalid required variable.
2. Create the SQLAlchemy engine/session factory.
3. Run `Base.metadata.create_all()` for MVP (no migration tool required at this scale; revisit if the
   schema needs versioned migrations later).
4. Register all routers under the `/api/v1` prefix. This is fixed by `api.md` — there is no
   alternative base path and no decision left open here.
5. Expose `GET /health`, which checks DB connectivity and reports OCR/blockchain adapter
   configuration state (not full liveness — see `api.md`).

## Error handling convention

Every raised domain/service exception maps to exactly one HTTP status + error code via a single
FastAPI exception handler registered in `main.py`. Do not `try/except` and format errors ad hoc
inside individual route handlers — this keeps the error envelope in `api.md` consistent everywhere.
