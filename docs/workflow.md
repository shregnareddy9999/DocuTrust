# End-to-End Workflow

This is the narrative walkthrough of the whole system, stage by stage. It exists so a new
contributor, a teammate, or a judge can understand what happens between "user picks a file" and
"dashboard shows a result" without reading nine contract documents first.

**This file describes. It does not define.** Every concrete value here — field names, statuses,
endpoints, limits — is owned by another document, cited at each stage. If this file and a contract
document ever disagree, the contract document wins and this file is the one with the bug.

Supersedes the earlier `document-verification-workflow.md` draft, which was directionally right but
left several things undecided that are now locked.

---

## 0. The whole system in ten lines

```
1. User selects a category and uploads a PDF/image
2. Backend validates the file and creates a document record
3. Backend preprocesses it (PDF → page images, conservative image cleanup)
4. PaddleOCR reads text + per-region confidence
5. Extraction maps OCR output onto that category's fixed schema
6. Matching finds the applicable synthetic registry record (or finds none)
7. Deterministic rules run; status precedence assigns exactly one status
8. If uncertain → human review; corrections create a NEW verification, never overwrite
9. On a terminal status → minimal, non-identifying event recorded on the local chain
10. Dashboard shows extraction, comparison, rules, reasons, review history, chain status
```

Two things are **always tracked separately** and never merged into a single "overall status":
the **verification status** (6 values) and the **blockchain recording status** (4 values).

---

## Stage 0 — Prepare the synthetic demo data

**Owner:** Task 03. **Contracts:** `category-schemas.md`, `data-model.md` (`registry_records`).

Before anybody uploads anything, `backend/app/fixtures/seed_registry.py` populates the registry with
the four locked fixtures — one per category — and `sample_documents/` holds the matching document
images generated from those same values, plus deliberately mismatching siblings.

The registry is the trusted reference **for this controlled demo only**. It is not a government
database, not a university database, and not proof of any real person's credentials.

**Do**
- Seed exactly the fixtures in `category-schemas.md`, with their `DEMO-` keys and fictional names.
- Provide, per category, at least: one matching document, one mismatching document.
- Provide at least one document whose identifying key exists in no registry record, to demonstrate
  `NO_TRUSTED_RECORD`.
- Provide at least one deliberately degraded/blurry scan to demonstrate `REVIEW_REQUIRED`.
- Make seeding idempotent — re-running it must not produce duplicate records.

**Don't**
- Don't use a teammate's real marksheet, PAN card, or ID card as a fixture. Ever.
- Don't invent a realistic-looking real PAN number, Aadhaar number, or roll number.
- Don't label a fabricated record as government-verified anywhere in seed data or UI copy.
- Don't seed two active records in the same category sharing an identifying key — matching treats
  that as a seeding bug and reports `PROCESSING_FAILED` (`verification-rules.md` step 6).

---

## Stage 1 — Upload

**Owner:** Task 04. **Contracts:** `api.md` (`POST /documents`), `document-processing.md`,
`security-privacy.md`, `configuration.md`.

The user picks one of the four categories and a file. The frontend posts multipart form data. The
backend validates before it stores anything, writes a `documents` row, and returns a `document_id`
with `processing_state: "UPLOADED"`.

Validation is by **content**, not by filename: extension, declared MIME, magic-byte signature, byte
size against `MAX_UPLOAD_MB` (10), and page count against `MAX_PDF_PAGES` (5). All four must pass.

**Do**
- Generate a server-side `storage_key` — never build a path from the user's filename.
- Keep `UPLOAD_DIR` outside any static/public web route.
- Compute and store `sha256` over the original bytes at upload time.
- Return the exact error codes in `api.md`: `400 INVALID_CATEGORY`, `413 FILE_TOO_LARGE`,
  `415 UNSUPPORTED_MEDIA_TYPE`, `422 EMPTY_OR_CORRUPT_FILE`.

**Don't**
- Don't trust `Content-Type` or the file extension alone.
- Don't execute an uploaded file, or pass its path to a shell command.
- Don't accept a corrupt file and return empty text as though processing succeeded.
- Don't create a `documents` row for a file that failed validation.

---

## Stage 2 — Preprocess

**Owner:** Task 05. **Contract:** `document-processing.md` steps 1–4.

PDFs are rendered page by page to images at a bounded resolution (long edge ≤ 2000px). Images get
conservative cleanup: grayscale, EXIF orientation correction, light denoise and contrast
normalization.

Preprocessing improves readability. It never changes meaning.

**Do**
- Operate on an in-memory copy; the stored original is never modified.
- Apply the same repeatable steps to every page, in the same order.
- Track per-page warnings so one bad page is visible without erasing the others.
- Enforce `OCR_TIMEOUT_SECONDS` (30s, per page).

**Don't**
- Don't overwrite the original with the processed image.
- Don't "repair," sharpen aggressively, or redraw content — that alters the evidence.
- Don't assume every PDF has a valid text layer, or that every PDF opens at all.
- Don't let one failed page silently discard results from the pages that worked.

---

## Stage 3 — OCR

**Owner:** Task 05. **Contract:** `document-processing.md` steps 5–6.

PaddleOCR (English, CPU) runs on each preprocessed page and returns recognized text regions with
confidence scores and bounding boxes. The adapter normalizes that into the internal `OcrResult`
shape: `text`, `regions[]`, `mean_confidence`, `engine_version`.

This is **recognition, not verification**. OCR confuses `0`/`O` and `1`/`I` on poor scans, and it
knows nothing about who issued the document.

**Do**
- Preserve raw OCR output (subject to `RETENTION_DAYS`) separately from normalized fields.
- Preserve per-region confidence and page context.
- Record `engine_name` and `engine_version` from the installed package at runtime, not hardcoded.
- Emit warnings for unreadable or low-confidence regions.

**Don't**
- Don't let PaddleOCR's raw response format leak past `paddleocr_adapter.py`.
- Don't treat OCR confidence as a fraud probability.
- Don't silently replace an uncertain character with a guess.
- Don't require an LLM anywhere in this path (`decisions.md` D-06).

**Outcome nuance:** OCR returning *no text at all* is `status: SUCCEEDED` with a
`no_text_detected` warning — an unhelpful but legitimate result. OCR *crashing or timing out* is
`status: FAILED`. These are different states and must not be collapsed.

---

## Stage 4 — Structured field extraction

**Owner:** Task 06. **Contracts:** `category-schemas.md`, `document-processing.md` step 7.

The extraction service maps `OcrResult` onto the selected category's fixed schema. For an academic
certificate the result looks like this:

```json
{
  "document_type": "academic_certificate",
  "extracted_fields": {
    "student_name":               { "value": "Aarav Demo",     "confidence": 0.96, "source": "ocr" },
    "institution_name":           { "value": "Example Technical Institute", "confidence": 0.93, "source": "ocr" },
    "student_id":                 { "value": "DEMO-STU-001",   "confidence": 0.91, "source": "ocr" },
    "course_name":                { "value": "B.Tech CSE",     "confidence": 0.95, "source": "ocr" },
    "semester_or_year":           { "value": "5",              "confidence": 0.88, "source": "ocr" },
    "certificate_or_marksheet_id":{ "value": null,             "confidence": null, "source": "ocr" }
  },
  "warnings": ["missing_field:certificate_or_marksheet_id"],
  "status": "SUCCEEDED"
}
```

Unlike the earlier draft, this shape is **not illustrative** — it is the frozen contract in
`api.md` (`GET /documents/{id}/extraction`). Build to it exactly.

**Do**
- Use exactly one schema per category, sourced from `category-schemas.md`.
- Represent a field with no OCR evidence as `null` plus a `missing_field:<name>` warning.
- Keep `confidence` a separate key from `value` — never blend them.
- Normalize carefully (trim whitespace) without changing meaning.

**Don't**
- Don't invent a value because the schema expects one.
- Don't turn an unreadable value into a confident one.
- Don't apply one category's schema to another category's document.
- Don't let any future LLM assist add a fact the OCR output doesn't support.

---

## Stage 5 — Registry comparison and rules

**Owner:** Task 07. **Contract:** `verification-rules.md` (authoritative, entire document).

Matching looks for the applicable synthetic registry record, then the rule engine compares required
fields. Both are pure functions with no database or HTTP imports.

The critical subtlety: "no match" splits into two genuinely different situations.

| What was found | Status |
|---|---|
| A record shares the identifying key and **all** match-fields agree | `VERIFIED_MATCH` |
| A record shares the identifying key but a match-field **disagrees** | `INTEGRITY_MISMATCH` (names the exact field, expected vs. observed) |
| **No** record shares even the identifying key | `NO_TRUSTED_RECORD` |
| A required field is missing, or a match-field's confidence is below `LOW_CONFIDENCE_THRESHOLD` | `REVIEW_REQUIRED` |
| OCR failed, or the registry itself is inconsistent | `PROCESSING_FAILED` |
| Not run yet | `PENDING` |

When more than one condition could apply, `verification-rules.md` defines a strict precedence order
(failure → review → no-record → mismatch → match). That order is the answer to "which status wins" —
it is not a judgement call at implementation time.

**Do**
- Record which specific fields matched and which did not, individually.
- Keep matching and normalization deterministic and reproducible.
- Attach a reason code and a human-readable explanation to every outcome.
- Keep verification status and blockchain status strictly separate.

**Don't**
- Don't call a document forged because no record was found.
- Don't call a document genuine because its text looks plausible.
- Don't invent an authenticity percentage.
- Don't loosen a matching rule to make a demo pass. If a demo fails, fix the fixture or the bug,
  and say what happened.

---

## Stage 6 — Human review

**Owner:** Task 08. **Contracts:** `verification-rules.md`, `api.md`
(`POST /verifications/{id}/review`), `data-model.md`.

When the system is uncertain, the reviewer sees the extracted fields, the confidence values, and
the explicit reasons the item needs review. They can `ACCEPT`, `CORRECT`, or mark `UNRESOLVED`.

A `CORRECT` action — say, fixing a `6` that OCR misread as a `5` — stores the corrected value as an
**additional** field entry with `source: "corrected"`, then re-runs the identical rule precedence
against the corrected values and writes a **new** `verification_results` row.

**Do**
- Show original OCR value and corrected value side by side, visibly distinct.
- Record who reviewed, what changed, when, and why.
- Preserve the previous verification result as history.
- Re-run the same rules — never hand-assign a status after a review.

**Don't**
- Don't overwrite the original OCR value.
- Don't let a reviewer edit the registry from the review screen.
- Don't claim a human review equals issuer confirmation. Post-review wording stays
  "matched our synthetic demo reference (reviewer-corrected)."
- Don't let anyone edit blockchain history — the contract has no update or delete function.

---

## Stage 7 — Persist

**Owner:** Task 10. **Contract:** `data-model.md`.

The database holds document metadata, extraction output, verification results, review actions, and
blockchain records. The document file itself stays in controlled filesystem storage and is never
written into the database as a blob, and never onto the chain.

**Do**
- Use UUID primary keys and real foreign-key relationships.
- Store timestamps and preserve status transitions as new rows, not mutations.
- Honour `RETENTION_DAYS` — raw OCR text and uploaded bytes expire; audit rows do not.
- Keep sensitive document contents out of application logs.

**Don't**
- Don't put documents or OCR text on-chain.
- Don't assume a hash is encryption. It is not.
- Don't expose uploads through guessable public URLs.
- Don't let the UI show a success state before the backend has actually persisted the result.

---

## Stage 8 — Record the minimal on-chain event

**Owner:** Task 09. **Contract:** `blockchain.md` (authoritative).

On a **terminal** verification status, the backend submits one transaction to the local Hardhat
chain via `VerificationRegistry.recordVerification`. The payload is three values: a `bytes32`
verification reference, a `bytes32` event digest, and a `uint8` outcome code. Nothing else.
`PENDING` is never recorded.

This gives a tamper-evident record of **what our application concluded, and when**. It does not
independently validate the document, and it does not make the synthetic registry authoritative.
Say that sentence out loud in the demo.

It is also **not** a document-integrity record. Nothing derived from the document's bytes goes
on-chain (`decisions.md` D-22, `blockchain.md` §"Two different goals"). `documents.sha256` covers our
locally stored copy and stays local.

**Do**
- Use the local development chain; keep keys and `CHAIN_EVENT_SALT` out of source control.
- Wait for and verify the receipt before displaying `CONFIRMED`.
- Handle chain unavailability with bounded retries, then `FAILED`.
- Prevent duplicate submissions by checking for an existing non-`FAILED` record first.

**Don't**
- Don't put any personal detail on-chain.
- Don't say "blockchain verified" and let anyone hear "government verified."
- Don't mark a transaction confirmed merely because it was submitted.
- Don't change the verification result because the chain is unavailable. Those are independent.

---

## Stage 9 — Display

**Owner:** Task 11. **Contracts:** `frontend.md`, `api.md`, `deployment-demo.md`.

The dashboard must let a teammate or a judge understand the outcome without reading backend logs.
One document's result view shows:

- Category and document reference ID
- Extracted fields, with confidence, and any missing or uncertain values marked
- Registry comparison table — extracted value vs. registry value, per field
- Verification status badge with the plain-language reason
- Review history, where applicable
- Blockchain status badge and transaction reference, as a **separate** badge
- A persistent synthetic-data banner

**Do**
- Render verification status and blockchain status as two distinct badges.
- Write warnings in plain language, not error codes.
- Provide the review flow directly from an uncertain result.
- Implement loading, error, and empty states on every page — a blank screen during a multi-second
  OCR run is a bug, not an acceptable gap.

**Don't**
- Don't show a green "genuine" badge on the strength of OCR alone.
- Don't hide mismatched fields to make the screen look cleaner.
- Don't display a fake transaction hash, or present a failed transaction as succeeded.
- Don't describe a synthetic match as an official verification anywhere on screen.

---

## What changed from the earlier draft

If you read the original `document-verification-workflow.md`, these are the substantive
corrections now reflected above:

| Earlier draft | Now |
|---|---|
| "The actual API contract will be finalized in the documentation" | Frozen in `api.md`; the JSON in Stage 4 is the real shape |
| "agree on supported formats and limits before implementation" | Locked: JPEG/PNG/PDF, 10 MB, 5 pages (`configuration.md`) |
| Match / issue as a two-way branch | Six statuses with an explicit precedence order (`verification-rules.md`) |
| "minimal metadata, such as … result code, and timestamp" | Exact three-argument contract call and digest formula (`blockchain.md`) |
| Review described generally | `ACCEPT` / `CORRECT` / `UNRESOLVED`, with corrections creating a new verification row |
| Retention "define retention and deletion behavior" | `RETENTION_DAYS=7` with a specified cleanup script (`data-model.md`) |
| No mention of who builds what | Every stage names its owning task |
