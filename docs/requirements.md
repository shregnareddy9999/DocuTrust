# Requirements

Source: `project-context.md`, `problem-statement-mapping.md`. Status column: **Locked** (build to
this exactly) or **Locked-MVP** (locked for this hackathon; explicitly revisit for production).

## Functional requirements

| ID | Requirement | Status |
|---|---|---|
| FR-01 | Accept PDF/JPEG/PNG uploads up to the configured limits; reject unsupported, oversized, empty, or corrupt files with a specific error code (`api.md`) | Locked |
| FR-02 | Assign an internal UUID per document; store the file under a server-generated filename in `UPLOAD_DIR`, never in the database | Locked |
| FR-03 | Run PaddleOCR on every accepted page image; preserve raw OCR output, per-region confidence, and engine/model version | Locked |
| FR-04 | Map OCR text to the selected category's schema (`category-schemas.md`) without inventing any value not present in the OCR output | Locked |
| FR-05 | Represent missing/ambiguous fields explicitly (`null` + a warning); an uncertain field must never silently become a "matched" field | Locked |
| FR-06 | Compare only the documented required fields for a category against the synthetic registry, using the normalization rules in `verification-rules.md` | Locked |
| FR-07 | Every rule outcome carries a reason code and a human-readable explanation (`verification-rules.md`) | Locked |
| FR-08 | Distinguish, as separate statuses: no reference record, field mismatch, review-needed, processing failure, and match (`verification-rules.md`) | Locked |
| FR-09 | Allow a named reviewer to accept, correct, or flag-unresolved an extraction; preserve the original OCR value and the correction as separate, timestamped records | Locked |
| FR-10 | When blockchain recording is enabled, submit a minimal event per completed verification; track chain status (`NOT_REQUESTED`/`PENDING`/`CONFIRMED`/`FAILED`) independently of verification status | Locked |
| FR-11 | The dashboard shows: extracted fields with confidence/warnings, registry comparison, rule outcomes with reasons, review history, and blockchain status/tx reference, in one view per document | Locked |
| FR-12 | A seed script creates a reproducible synthetic registry and at least one demo document fixture per category (matching and mismatching examples) | Locked |
| FR-13 | `GET /document-types` returns the exact field schema (required/optional, type, format) for each of the 4 categories, sourced from `category-schemas.md` — the frontend must never hardcode field lists | Locked |

## Non-functional requirements

| ID | Requirement | Status |
|---|---|---|
| NFR-01 | No third-party paid API keys required to run the MVP end-to-end | Locked |
| NFR-02 | No document bytes, raw OCR text, or direct identity field values ever leave the database/filesystem boundary onto the blockchain | Locked |
| NFR-03 | A technical failure (OCR crash, chain RPC down, DB error) must never be represented as a fraud/mismatch verdict | Locked |
| NFR-04 | Given identical normalized inputs and configuration, rule evaluation is deterministic and reproducible | Locked |
| NFR-05 | OCR and blockchain adapters are behind an interface and mockable in tests; no test requires a live PaddleOCR run or a live chain node | Locked |
| NFR-06 | Setup, limits, and demo-reset steps are documented well enough that a new teammate reproduces the demo unaided (`setup.md`, `deployment-demo.md`) | Locked |
| NFR-07 | Every upload is validated (extension + content signature + size + page count) and stored under a generated filename outside any public web root | Locked |
| NFR-08 | Every UI element showing a registry match visibly labels it as demo/synthetic data | Locked |
| NFR-09 | P95 latency for OCR + extraction + matching on a single-page fixture is under 15 seconds on a typical development laptop (CPU-only PaddleOCR) | Locked-MVP |
| NFR-10 | The backend has no authentication for the MVP demo; this is explicit and documented, not silent (`security-privacy.md` D-11) | Locked-MVP |

## Acceptance criteria (system-level)

- A known-matching fixture, uploaded end-to-end, yields `VERIFIED_MATCH` with all required fields
  shown as matched.
- An unsupported or corrupt file is rejected before any OCR/verification step runs.
- A fixture with no corresponding registry record yields `NO_TRUSTED_RECORD`, and the UI never
  implies this means forgery.
- A fixture with a deliberately wrong field yields `INTEGRITY_MISMATCH` naming the exact field and
  expected vs. observed value.
- A deliberately degraded/ambiguous scan yields `REVIEW_REQUIRED`; a reviewer correction is saved
  separately from the original OCR value, and re-running verification after correction updates the
  status while preserving history.
- Stopping the local blockchain node does not change any verification's status; the corresponding
  blockchain record shows `FAILED` or `PENDING` independently.
- No blockchain transaction payload, inspected directly on-chain, contains a document, raw OCR text,
  or an identity field value (see `blockchain.md` for the exact payload).
- The automated test suite covers, at minimum, the "Required scenarios" in `testing.md` and passes
  without any live external dependency.
