# Testing Strategy

## Layers

1. **Domain unit tests** (`backend/tests/test_matching_rules.py` etc.) — normalization, matching,
   rule precedence, status assignment. No DB, no OCR, no chain — pure function tests, the fastest and
   most important layer.
2. **Adapter tests** — OCR adapter and blockchain adapter, using `fake_adapter.py` for the default
   suite, plus one clearly-marked optional local-integration test per adapter (real PaddleOCR /
   real Hardhat node) that is **not** part of the default `pytest` run (see markers below).
3. **API tests** (`test_api_documents.py`, `test_api_verifications.py`) — FastAPI `TestClient`
   against a temp SQLite DB with fake adapters injected; covers request validation, response
   schemas (matching `api.md` exactly), and error envelopes.
4. **Persistence tests** — repository query correctness, FK relationships, that a `CORRECT` review
   action creates a new `verification_results` row rather than mutating the old one.
5. **Frontend tests** (`vitest`) — `StatusBadge` renders the exact locked labels, upload
   loading/error/empty states, `SyntheticDataBanner` renders on every result view.
6. **End-to-end** (manual, per `api-manual-testing-guide.md` + `deployment-demo.md`, automated via
   Playwright is a post-MVP nice-to-have, not required for the hackathon).

## Required scenarios (must exist, across the layers above)

- Matching fixture → `VERIFIED_MATCH`, all `field_comparisons` show `matched: true`.
- Fixture with no registry entry for its category+key → `NO_TRUSTED_RECORD`.
- Required field missing/low-confidence → `REVIEW_REQUIRED`.
- Known field mismatch → `INTEGRITY_MISMATCH` naming the exact field.
- Corrupt/unsupported/oversized upload → rejected at the API boundary, never reaches OCR.
- OCR raises/times out → `PROCESSING_FAILED`, never a mismatch/no-record status.
- OCR returns empty text → `SUCCEEDED` with `no_text_detected` warning, leads to `REVIEW_REQUIRED`.
- Reviewer `CORRECT` action → new verification row, original OCR value still visible, status
  re-evaluated against corrected values.
- Blockchain disabled → `NOT_REQUESTED` immediately, no submission attempted.
- Blockchain RPC unreachable / tx reverts / receipt-wait timeout → `FAILED`, verification status
  unaffected.
- Duplicate blockchain submission for the same `verification_id` is not created when a non-`FAILED`
  record already exists.
- Status precedence order (`verification-rules.md`) is tested explicitly at its boundaries — e.g., a
  document that is both missing a required field **and** would otherwise mismatch must resolve to
  `REVIEW_REQUIRED`, not `INTEGRITY_MISMATCH`.

## Test principles

- No test requires a live third-party paid API.
- No test requires a live PaddleOCR model run or a live Hardhat node by default — use
  `fake_adapter.py` for both; real-adapter tests are separately marked and run manually
  (`pytest -m integration`).
- Only synthetic fixtures are used — no real personal documents, ever, in the test suite or fixtures
  directory.
- Rule/precedence tests are boundary tests (exact threshold values), not just "happy path" checks.

## Running the suites

```bash
cd backend && pytest                     # default suite, all fakes
cd backend && pytest -m integration      # optional, requires real PaddleOCR + running Hardhat node
cd frontend && npm test
```

## Reporting

Every task's handoff (`AI-CONTEXT.md`, task files) must include the exact command run and the
observed pass/fail output — never a claim of "tests pass" without having actually run them in that
session.
