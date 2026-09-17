# Security and Privacy

## Threat model

Untrusted inputs: uploaded PDFs/images, HTTP request payloads, OCR output (may contain adversarial
or malformed text), the free-text reviewer name/comment field. Semi-trusted: synthetic registry data
(trusted only within this demo's fixture set). External local process: the Hardhat chain RPC, which
may be unavailable or slow.

Risks considered: malicious/oversized/corrupt uploads, path traversal via filenames, accidental PII
persistence or logging, a status label implying more certainty than was actually checked,
unauthenticated review actions, and blockchain submission failures leaking into the verification
result.

## Required safeguards

- **Filenames:** server-generates `storage_key` for every upload; the client's `original_filename`
  is stored for display only and is never used to build a filesystem path (`upload_service.py`).
- **Upload limits:** MIME allowlist (JPEG/PNG/PDF) + `MAX_UPLOAD_MB` + `MAX_PDF_PAGES` enforced at
  the API boundary before any parsing library touches the bytes.
- **Storage location:** `UPLOAD_DIR` is outside any directory served statically by the frontend or
  backend; there is no "download original file" endpoint in the MVP API surface (`api.md`) — only
  extracted/derived data is ever returned over HTTP.
- **Logging:** never log file contents, raw OCR text, `extracted_fields_json` values, or the
  contents of `.env`. Application logs may include `document_id`, `verification_id`, status
  transitions, and error codes only.
- **Blockchain payload:** minimal and non-identifying, per `blockchain.md` — enforced at the single
  `blockchain_service.py` payload-building function.
- **Synthetic-data labeling:** every UI surface showing a registry comparison or match renders
  `SyntheticDataBanner` (`frontend.md`) — this is checked in a frontend test, not left to
  convention.
- **Verification/chain separation:** verification status and blockchain status are always rendered
  and stored as two independent fields — never merged (`data-model.md`, `api.md`).
- **Input validation:** every request body is validated by a Pydantic schema at the API boundary;
  every DB query goes through SQLAlchemy's parameterized query building — no raw SQL string
  concatenation anywhere in the codebase.
- **Error responses:** generic message + `correlation_id` for `500`s; detailed diagnostics stay in
  server-side logs only (`api.md` error envelope).

## Authentication and roles (resolves D-11)

**MVP decision:** no authentication system is built. Every endpoint is open on `localhost`/the local
network the demo runs on. This is deliberate and documented, not an oversight:

- The "reviewer" role is represented only by the free-text `reviewer_ref` field on a review action —
  anyone with API/UI access can act as any reviewer name. This is acceptable for a single-operator
  hackathon demo and is explicitly **not** acceptable for any real deployment.
- If a judge or teammate asks "what stops anyone from reviewing/approving," the honest answer is:
  "nothing, in this demo — production would need real authentication and role-based access before
  handling non-synthetic data," and this is exactly what this section says.
- Should time allow, a minimal API-key-per-role header (`X-Demo-Role: operator|reviewer|admin`,
  checked against a static config value) is an acceptable **optional** MVP hardening step — track it
  as a candidate post-MVP task, not a blocker.

## Retention and deletion (resolves D-12)

See `data-model.md` "Retention" — `RETENTION_DAYS` (default 7) governs deletion of raw file bytes
and raw OCR text; verification/review/blockchain records persist for audit purposes. This is a demo-
scale policy; a real deployment needs a reviewed data-retention policy before accepting real
documents.

## Privacy boundary

Do not use real personal documents for development, testing, or the demo — this includes team
members' own marksheets, ID cards, or PAN cards. If a real document is ever used for a one-off
compatibility check, it requires the document owner's informed consent, must stay on a single local
machine, must never be committed to the repository or uploaded to any external tool (including an
AI chat), and must be deleted immediately after the check. Prefer synthetic fixtures in all cases.

## Open items still requiring a decision before any non-demo use

- Encryption at rest for `UPLOAD_DIR` and `data/app.db`.
- Antivirus/malware scanning of uploaded files.
- Production authentication/RBAC (see above).
- Any network exposure beyond localhost/local-network demo use.

MVP is explicitly not production-ready; do not remove this section as the project matures — update
it to reflect what has actually been decided.
