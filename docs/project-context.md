# Project Context — PS21 Document Verification System

## Problem statement (as given)

> Develop a Blockchain-based document verification system that uses AI/ML and OCR to extract and
> validate information from uploaded documents, cross-check records with authorized databases,
> detect forged or tampered documents, and store verification records on a tamper-resistant
> blockchain ledger while ensuring data security and privacy.

This is a **hackathon MVP** built against that statement. It is not a production government system.
`problem-statement-mapping.md` explains, line by line, what is fully implemented, what is
deliberately simplified for the demo, and what would need to change for production. Read that file
alongside this one — it exists specifically so nobody (teammate, judge, or a future AI contributor)
mistakes a demo shortcut for a misunderstanding of the problem.

## What PS21 actually demonstrates

A document (PDF or image) is uploaded, OCR-extracted, mapped to a category-specific schema,
compared field-by-field against a small **synthetic** reference registry, run through deterministic
consistency rules, optionally corrected by a human reviewer, and recorded — as a minimal
tamper-evident event, never the document or its personal fields — on a local Ethereum-compatible
blockchain. The dashboard shows every step's result plainly, including uncertainty and failure.

## Intended demo users

| Role | What they do | Notes |
|---|---|---|
| Operator | Uploads a document, selects category, views processing/verification status | No login required in MVP; see `security-privacy.md` D-11 |
| Reviewer | Opens `REVIEW_REQUIRED` / `INTEGRITY_MISMATCH` items, corrects OCR values, records a decision | Identified by a free-text reviewer name for MVP, not a real account |
| Administrator | Manages synthetic registry fixtures, reads configuration | Same "no real auth" caveat |
| Auditor / judge | Views the verification result and the blockchain transaction/receipt | Read-only; never sees anything not already on the dashboard |

These are conceptual roles for the demo, not an access-control system. See `security-privacy.md`
§"Authentication and roles (D-11 — resolved)" for the exact MVP behavior.

## MVP document categories (locked)

1. **Academic certificate** (e.g., marksheet/degree)
2. **Institutional identity card**
3. **PAN-like demo document** (obviously synthetic identifiers only — never a real PAN format value)
4. **Other government-style certificate** (synthetic template)

Exact required/optional fields for each category are frozen in `category-schemas.md`. No task may
add, rename, or drop a field for these categories without a documentation update approved by the
project lead.

## In scope (MVP)

- PDF and common image upload, within limits fixed in `configuration.md`.
- PaddleOCR-based text extraction (see `document-processing.md`).
- Category-specific field mapping with explicit uncertainty (`category-schemas.md`).
- Synthetic reference registry and deterministic field comparison (`verification-rules.md`).
- Explainable, deterministic integrity/consistency checks — no black-box scoring.
- Human review and correction with full audit history.
- A minimal, non-identifying on-chain event per verification (`blockchain.md`).
- A dashboard showing extraction, comparison, status, reasons, and chain status together.

## Out of scope (MVP)

- Any real government/issuer database integration, or a claim of government verification.
- Real PAN/Aadhaar/passport numbers, or any production identity processing.
- Face recognition or biometric matching.
- Automatically labeling a document "forged" — the system only ever reports match /
  no-record / mismatch / review-needed / failed, with evidence.
- Production-grade authentication, authorization, or multi-tenant deployment.
- Public blockchain deployment, or putting documents/personal data on-chain.
- Any AI/ML model beyond OCR (see `problem-statement-mapping.md` for the explicit deferral and
  rationale) — deterministic rules are the MVP's "intelligence," not a learned model.
- Guaranteeing OCR correctness or proving document authenticity in any absolute sense.

## Key limitations (state these in every demo)

- OCR reads visible characters. It says nothing about who issued the document or whether it is
  genuine.
- A `VERIFIED_MATCH` means the extracted fields match the **configured synthetic record** — nothing
  more. It is never "government verified" or "authentic."
- Computing a hash for the first time is not tamper detection. Tamper detection requires comparing
  against a **previously trusted** fingerprint, which this MVP only has for the synthetic registry
  fixtures themselves.
- The blockchain event proves "our application recorded this outcome at this time, unmodified since."
  It does not prove the outcome itself was correct, and it does not validate the synthetic registry.

## Definition of project success (for this hackathon)

A teammate or judge can, from a clean checkout, run the seed script, start the three services
(backend, frontend, local chain), and walk through all of: a matching fixture, a mismatching
fixture, a fixture with no registry entry, a low-confidence/handwritten scan needing review, and a
completed on-chain receipt — with the dashboard explaining, at every step, exactly why that status
was assigned.
