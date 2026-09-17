# Problem Statement Mapping

Purpose: make it impossible to mistake a deliberate hackathon simplification for a missed
requirement. Every clause of the problem statement is addressed below with what we built, what we
deferred, and why. Use this file when writing the pitch deck and when answering judge questions.

| Problem statement clause | What PS21 does | What is deferred | Why |
|---|---|---|---|
| "uses AI/ML and OCR to extract... information" | OCR (PaddleOCR) extracts text; deterministic rules (not ML) do the reasoning | No trained ML/classifier model | See "On the AI/ML clause" below |
| "validate information from uploaded documents" | Extracted fields are validated against a schema (required fields, format checks) per `category-schemas.md` | — | Fully in scope |
| "cross-check records with authorized databases" | Cross-checks against a clearly labeled **synthetic** registry (`registry_records` table) | Real government/institutional database or API integration | No real API access exists for a hackathon; using one would also require real PII, which is explicitly avoided. Documented in `project-context.md` as a hard boundary. |
| "detect forged or tampered documents" | Deterministic **consistency checks**: required-field presence, cross-field date/logic consistency, known-fixture duplicate/fingerprint checks (`verification-rules.md`) | Image forensics (error-level analysis, copy-move detection, font/kerning analysis, PDF edit-history/metadata inspection) | See "On the forgery-detection clause" below |
| "store verification records on a tamper-resistant blockchain ledger" | Every verification result triggers a minimal on-chain event (`blockchain.md`) on a local Ethereum-compatible chain | A public/permissioned production chain (e.g., a testnet or Hyperledger Fabric deployment) | Local dev chain is standard for hackathon demos and keeps the demo self-contained and reproducible without external dependencies |
| "ensuring data security and privacy" | No PII on-chain, controlled file storage, no real documents in fixtures, generic error responses, safe filenames (`security-privacy.md`) | Encryption at rest, production authentication/RBAC, antivirus scanning of uploads | MVP demo scope; explicitly listed as required before any non-demo use |

## On the AI/ML clause

The MVP's "intelligence" is OCR (a mature ML technology) plus deterministic, explainable rules — not
a trained classifier producing a fraud score. This is intentional, not an oversight:

- A rule that says "this field is missing" or "this date is inconsistent" is falsifiable and
  demoable live, in front of judges, with zero risk of an embarrassing misclassification.
- An untrained or lightly-trained fraud classifier over a handful of synthetic examples would be
  **worse than useless** — it would produce a confident-looking but meaningless probability, which
  directly contradicts the project's own non-negotiable rule against inventing scores (see
  `AI-CONTEXT.md`).
- If time remains after the MVP is stable, an optional, clearly-labeled anomaly-detection add-on
  (e.g., flagging OCR confidence outliers or unusual field-length distributions across processed
  documents) can be proposed to the project lead — see `decisions.md` D-06. It stays an *input to
  human review*, never an automatic verdict.

## On the forgery-detection clause

"Field mismatch against a reference" and "document was altered after creation" are different
problems. The MVP only does the first. A genuine tamper-detection module would need image forensics
(ELA, copy-move detection), font/layout consistency analysis, or PDF revision/metadata inspection —
none of which are implemented. This is called out explicitly, rather than left implicit, so that:

- The dashboard never implies more than it checked (`verification-rules.md`'s status vocabulary is
  deliberately narrow: `INTEGRITY_MISMATCH` means "a specific documented check failed," not
  "forged").
- If time allows post-MVP, a **basic image-forensics capability** (e.g., PDF metadata/edit-history
  inspection, or simple copy-move detection via OpenCV) is the natural next feature — track it as a
  candidate post-MVP task, not squeezed into the MVP timeline.

## Presenter guidance

When asked "where's the AI/ML" or "how do you detect forgery," answer directly using this file:
name what's implemented (OCR + deterministic rules + blockchain audit trail), name what's
deferred (real registries, ML fraud scoring, image forensics), and state why (hackathon scope,
synthetic-data-only constraint, and a preference for explainable/deterministic behavior over an
untrained model producing unjustified confidence). This honesty is a strength, not a weakness — it
shows the team understands the difference between a demo and a production system.
