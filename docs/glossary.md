# Glossary

Shared vocabulary for PS21. When two people use the same word for different things, the integration
breaks quietly. Use these terms exactly.

## Project terms

| Term | Means |
|---|---|
| **Category** | One of the four locked document types: `academic_certificate`, `institutional_id`, `pan_like_demo`, `government_certificate`. Never called "document type" in code — that phrase is reserved for the `GET /document-types` endpoint's payload. |
| **Synthetic registry** | The seeded `registry_records` table of fictional reference records. The **only** reference data this project has. Never a government or institutional database. |
| **Fixture** | A synthetic registry record *or* a synthetic sample document shipped in `backend/app/fixtures/`. |
| **Match field** | A field with `match_field: true` in `category-schemas.md`. Only these participate in registry comparison. A field can be extracted and displayed without being a match field. |
| **Identifying key** | The one field per category used to locate the *applicable* registry record before comparing the rest: `student_id`, `id_number`, `demo_pan_code`, `certificate_number`. |
| **Applicable reference** | A registry record that shares the document's identifying key. Its existence is what separates `INTEGRITY_MISMATCH` (a reference exists, fields disagree) from `NO_TRUSTED_RECORD` (no reference at all). |
| **Verification status** | One of the six locked values. Owned by `verification-rules.md`. |
| **Blockchain recording status** | One of `NOT_REQUESTED`, `PENDING`, `CONFIRMED`, `FAILED`. Always tracked separately from verification status. |
| **Terminal status** | Any verification status other than `PENDING`. Only a terminal status triggers a chain submission. |
| **Reason code** | A short machine-readable string summarising why a status was assigned, e.g. `FIELD_MISMATCH:semester_or_year`. Paired with a human-readable reason. |
| **Event digest** | The opaque `bytes32` written on-chain, built per the formula in `blockchain.md`. Binds outcome only. **Not a document hash** — see `blockchain.md` §"Two different goals". |
| **Outcome integrity** | "Did our system really reach this outcome, unaltered since?" Answered by the on-chain event. |
| **Document integrity** | "Is this file byte-identical to what was uploaded?" Answered locally by `documents.sha256`, never on-chain (D-22). |
| **Current verification** | The verification row with the greatest `created_at` for a document, resolved only via `verification_repo.get_latest_for_document()` (D-23). |
| **Verification reference** | The `bytes32` on-chain identifier, `keccak256` of the internal verification UUID string. Never the raw UUID. |

## Layer terms

| Term | Means |
|---|---|
| **Adapter** | The only module allowed to import an external runtime library (PaddleOCR, Web3.py). Always has a `fake_adapter.py` sibling. |
| **Domain** | Pure Python under `backend/app/domain/`. Plain data in, plain data out. No FastAPI, no PaddleOCR, no Web3, no database session. |
| **Service** | Use-case orchestration. The only layer permitted to call more than one repository, or to call an adapter. |
| **Repository** | SQLAlchemy queries for one entity. No cross-entity business rules. |
| **Locked contract** | Anything in `api.md`, `data-model.md`, `category-schemas.md`, `verification-rules.md`, `blockchain.md`, or `configuration.md`. Changing one requires project-lead approval and a same-PR doc update. |

## Words we deliberately do not use

| Banned | Why | Say instead |
|---|---|---|
| "Authentic", "genuine", "valid document" | We cannot establish this and never claim to | "Matched our synthetic demo reference" |
| "Government verified", "officially verified" | We have no government integration | "Matched our synthetic demo reference" |
| "Forged", "fake", "tampered" (as a system verdict) | The system never concludes this | "Mismatch found in field X" / "No matching reference found" |
| "Fraud score", "authenticity score", "risk %" | No rule produces a number (`AGENTS.md` Rule 8) | The specific rule that failed, and why |
| "Blockchain-verified document" | The chain records our outcome, not the document | "Verification outcome recorded on-chain" |
| "The document is hashed on the blockchain", "tamper-proof document" | Claims document integrity, which nothing here provides (`decisions.md` D-22) | "The verification outcome is recorded on-chain and cannot be silently altered" |
| "AI detected" | There is no classifier; rules are deterministic | "Rule `field_match` failed because…" |
