# Decision Log

Status values: **Accepted** (build to this), **Accepted — verify environment** (build to this, but
confirm a specific compatibility fact first), **Deferred** (explicitly post-MVP, not silently
dropped).

| ID | Decision | Status | Notes |
|---|---|---|---|
| D-01 | Four document categories in MVP | Accepted | Exact schemas frozen in `category-schemas.md` |
| D-02 | *(provisional until Task 01 smoke tests — see D-24)* PaddleOCR is the OCR engine | Accepted — verify environment | Confirm Windows + macOS/Linux wheel availability for the team's actual Python versions in Task 01/05 before pinning |
| D-03 | Synthetic registry only, no real government/issuer access | Accepted | `problem-statement-mapping.md` documents why |
| D-04 | Deterministic rules, not an ML fraud classifier, for the MVP | Accepted | `problem-statement-mapping.md`; revisit only as a clearly-labeled optional add-on (see D-06) |
| D-05 | *(provisional until Task 01 smoke tests — see D-24)* Local Hardhat network + Solidity ^0.8.24 + Web3.py | Accepted — verify environment | Confirm Node.js/Hardhat compatibility on Windows dev machines in Task 01/09 |
| D-06 | No mandatory ML/LLM component | Accepted | An optional, clearly-labeled anomaly-detection add-on may be proposed post-MVP; it must never issue a final verdict, only surface something for human review |
| D-07 | Internet available during setup/demo; no offline requirement | Accepted | No third-party paid API keys anywhere in the stack |
| D-08 | SQLite for persistence | Accepted | No concurrent multi-user demo load; revisit only if a real multi-user deployment is ever planned |
| D-09 | *(provisional until Task 01 smoke tests — see D-24)* React + Vite (TypeScript) frontend, FastAPI backend | Accepted — verify environment | Folder structures frozen in `frontend.md` / `backend.md`; confirm `npm run build` succeeds on every machine before relying on it |
| D-10 | Exact API request/response schemas | **Resolved** | Frozen in `api.md`; any change needs a project-lead-approved doc update in the same PR as the code |
| D-11 | Authentication and reviewer authorization | **Resolved for MVP** | No auth system for the demo; reviewer identity is free-text `reviewer_ref`; documented explicitly as not production-acceptable in `security-privacy.md` |
| D-12 | Raw OCR/file retention and deletion | **Resolved for MVP** | `RETENTION_DAYS=7` default; cleanup script deletes raw bytes/OCR text but keeps verification/review/blockchain audit rows — see `data-model.md` "Retention" |
| D-13 | On-chain event digest construction | **Resolved** | `SHA256(verification_id + ":" + outcome_code + ":" + CHAIN_EVENT_SALT)` — full threat model in `blockchain.md` |
| D-14 | Upload size/page limits and supported OCR language | **Resolved for MVP** | `MAX_UPLOAD_MB=10`, `MAX_PDF_PAGES=5`, English-only OCR — see `configuration.md` / `document-processing.md` |

## New decisions added during this review

| ID | Decision | Status | Notes |
|---|---|---|---|
| D-15 | Status precedence order when multiple conditions could apply | Accepted | Exact ordered list in `verification-rules.md` — resolves what was previously an unstated ambiguity |
| D-16 | OCR pipeline runs synchronously in the request path for MVP, not via a background job queue | Accepted | Simpler for demo reliability; revisit only if OCR latency causes a demo problem during rehearsal (`architecture.md`) |
| D-17 | `outcomeCode` enum values for the on-chain event | Accepted | `blockchain.md` — fixed 0–4 mapping to the 5 terminal verification statuses |
| D-18 | A `CORRECT` review action always creates a new `verification_results` row rather than mutating the existing one | Accepted | Preserves full history; `data-model.md`, `api.md` |

## Open decisions — must be resolved by Task 10

These three sequencing questions were deliberately deferred, because they can only be answered once
the components exist. **Task 10 resolves all three, implements them, and replaces the "Open" status
below with the decision taken**, in the same pull request as the code.

| ID | Decision | Status | Recommendation |
|---|---|---|---|
| D-19 | When the OCR/extraction pipeline is triggered relative to upload | **Resolved** | `POST /documents` stores and returns `UPLOADED`; `POST .../verify` runs OCR on demand if no extraction exists, synchronously per D-16. Full state table and observability rules in `document-processing.md` §"Processing-state contract". Task 10 implements it as written — this is no longer open |
| D-20 | When blockchain submission is triggered | **Open — Task 10** | Automatically after a verification reaches a terminal status, inside `POST .../verify`, wrapped so a chain failure can never fail the verify call |
| D-21 | Whether a reviewer-corrected verification submits a second on-chain event | **Open — Task 10** | Yes. A new verification ID yields a different `verificationRef` and digest, so both events coexist and the correction becomes part of the permanent record |

Leaving any of these implicit in code is a defect. An undocumented sequencing decision is exactly the
kind of thing that changes silently three commits later.

## Further resolved decisions

| ID | Decision | Status | Notes |
|---|---|---|---|
| D-22 | Document integrity is **out of scope** and is never claimed on-chain | **Resolved** | `documents.sha256` covers our stored copy locally only. The `eventDigest` binds outcome, not document. Putting a document hash on-chain would create a confirmation oracle while proving nothing — full reasoning and what real document integrity would require in `blockchain.md` §"Two different goals" |
| D-23 | "Current" verification is the greatest `created_at` per document, via `verification_repo.get_latest_for_document()` only | **Resolved** | Plus a `supersedes_verification_id` column and `GET /documents/{id}/verifications`. Prevents contributors implementing divergent "latest result" logic — `data-model.md`, `api.md` |
| D-24 | The technology stack is **provisional until Task 01's smoke tests pass on every machine**, Windows included | **Resolved (process)** | D-02, D-05, and D-09 are proposals until `ENVIRONMENT-REPORT.md` records working pinned versions. See `tasks/01-foundation.md` §7 Requirement 7 |
| D-25 | PDF library for page counting and rendering | Accepted | pypdfium2 for both Task 04 (page counting) and Task 05 (rendering); pypdf not used. See `configuration.md`, `document-processing.md` |

## Superseded documents

| Document | Superseded by | Why |
|---|---|---|
| `document-verification-workflow.md` (early draft) | `workflow.md` | The draft left the API contract, format limits, status set, retention, and on-chain payload undecided. All are now locked. `workflow.md` ends with a table of exactly what changed |

## How to add a new decision

Append a row with the next `D-NN` ID, a status, and a one-line note pointing to the doc section
where the full detail lives. Never resolve a decision by editing code first and updating this file
later — the doc update and the code change ship in the same PR.
