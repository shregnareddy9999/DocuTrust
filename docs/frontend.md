# Frontend Structure (React + Vite + TypeScript)

## Locked folder layout

```text
frontend/
  src/
    main.tsx
    App.tsx                        # routes
    api/
      client.ts                    # fetch wrapper, base URL from env, error-envelope parsing
      documents.ts                 # uploadDocument, getDocument, getExtraction
      verifications.ts             # startVerification, getVerification, submitReview, getBlockchain
      documentTypes.ts             # getDocumentTypes (drives all category-specific forms)
    pages/
      UploadPage.tsx                # category picker + file upload + progress
      DocumentDetailPage.tsx        # extracted fields, confidence, warnings
      VerificationResultPage.tsx    # registry comparison, rule outcomes, reasons, status badge
      ReviewPage.tsx                # reviewer correction form (accept/correct/unresolved)
      BlockchainReceiptPage.tsx     # tx hash, chain status, explanation of what it proves
      DemoDashboardPage.tsx         # single screen combining the above for live demos
    components/
      StatusBadge.tsx               # renders one of the fixed status enums with fixed color/label
      FieldComparisonTable.tsx      # side-by-side extracted vs. registry value, per field
      SyntheticDataBanner.tsx       # persistent "synthetic demo data" banner — used on every result view
      UploadDropzone.tsx
      LoadingState.tsx / ErrorState.tsx / EmptyState.tsx
    state/
      useDocument.ts                # small hooks wrapping api/ calls + loading/error state
      useVerification.ts
    types/
      api.ts                        # TypeScript types mirroring api.md exactly (source of truth: backend)
  package.json
  vite.config.ts
  .env.example                      # VITE_API_BASE_URL
```

No global state management library (Redux/Zustand) is required for MVP scope — page-level hooks are
sufficient given the linear upload → result flow. Revisit only if a real cross-page shared-state need
appears.

## Hard rules

- The frontend never hardcodes a category's field list — it always calls `GET /document-types` and
  renders forms/tables from that response. This keeps `category-schemas.md` the single source of
  truth.
- Every screen that shows a registry match or a `VERIFIED_MATCH` status renders
  `SyntheticDataBanner` — this is not optional per-screen styling, it is a project requirement
  (`NFR-08`).
- `StatusBadge` is the only place status→label/color mapping exists; do not inline status strings
  elsewhere in JSX.
- Blockchain status and verification status are always rendered as two separate badges, never merged
  into one "overall status."

## Page flow

```
UploadPage
   → (on success) DocumentDetailPage  [shows extraction while verification may still be running]
       → VerificationResultPage        [comparison + rule outcomes]
           → ReviewPage (if REVIEW_REQUIRED or INTEGRITY_MISMATCH)
               → back to VerificationResultPage (post re-run)
           → BlockchainReceiptPage (if BLOCKCHAIN_ENABLED)
```

`DemoDashboardPage` is a single-screen assembly of the same data for stage/projector use during the
actual hackathon demo — it calls the same hooks, no separate backend logic.

## Loading / error / empty states

Every page that calls the API must render all three of `LoadingState`, `ErrorState`, and
`EmptyState` appropriately — a blank white screen during OCR processing (which can take several
seconds) is treated as a bug, not an acceptable MVP gap.

## API integration conventions

- `api/client.ts` parses the error envelope from `api.md` and throws a typed `ApiError` with
  `code`, `message`; components render `message` and never a raw stack trace.
- **No polling.** `POST /documents/{id}/verify` is synchronous and returns a terminal status, so
  `VerificationResultPage` shows a loading state for the duration of that call and then renders the
  result. There is no `PENDING`-to-terminal transition to wait for
  (`document-processing.md` §"Processing-state contract"). `StatusBadge` still handles `PENDING` as a
  defensive default only.
- ~~Polling~~ (superseded): `VerificationResultPage` polls `GET /verifications/{id}` every 2s while status is
  `PENDING`, stopping on any terminal status; no WebSocket/SSE is required for MVP scope.

## Blockchain failure detail (resolves a gap found in audit)

`BlockchainReceiptPage` renders `error_code` when `recording_status: "FAILED"`, translated to a short
plain-language line (e.g. `RPC_UNAVAILABLE` → "Could not reach the blockchain network"). Do not show
a bare error code with no explanation, and do not imply the verification result is affected — chain
failure and verification status are independent (`architecture.md`).
