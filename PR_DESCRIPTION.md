# PR — Task 11 · Frontend: synthetic document verification dashboard

**Branch:** `feature/task-11-frontend` → target `main`
**Status:** Staged and reviewed; NOT committed / pushed / merged (AGENTS.md §6 — awaiting your explicit
authorization). No backend, no `docs/`, no lock-package changes.

## Summary

The frontend delivers the full six-screen flow specified by `tasks/11-frontend.md` and
`docs/frontend.md`:

- **Requirement 1–6:** Upload (drag-drop + category picker from `GET /document-types`), document
  detail with extracted fields + per-field confidence, verification result with every match field shown
  (mismatches never hidden), review/correction (original OCR always visible), blockchain receipt, and
  the demo dashboard.
- **Honesty contract (AGENTS.md Rules 2/4/5/7):** separate verification + blockchain badges; no
  "Verified/Authentic/Genuine/Valid" wording in any rendered UI (banned-words test enforces); naming
  via `StatusBadge`/wording contract; synthetic-data banner on every result screen; honest "matched
  our synthetic demo reference" language; no fabricated hashes.
- **States:** loading/error/empty on every page; ProcessingSteps shows the synchronous contract
  (no polling loop); blockchain badges reflect `CONFIRMED/PENDING/NOT_REQUESTED/FAILED` honestly,
  never implying approval.
- **Responsive:** fluid units (clamp/auto-fit/dvh/safe-area insets), breakpoints at 900/720/480/420
  per `docs/DESIGN_SPEC.md`; sidebar → drawer <900px with backdrop; tables scroll inside their own
  `overflow-x` containers (no page-level horizontal scroll); touch targets ≥44px; reduced-motion
  respected.

## Screens delivered (mock mode)

- `/` → Dashboard/landing
- `/demo` → synthetic demo dashboard (projector-ready)
- `/upload` → Upload page
- `/documents/:id` → document detail + fields
- `/documents/:id/verifications` → history
- `/documents/:id/review` → review / correction
- `/verify/:id` → verification result (all statuses incl. mismatch show every field)
- `/receipt/:id` → blockchain receipt

## Test evidence (exact, this session)

- `npm run check` → typecheck `tsc -b` ✓ · oxlint 0 warnings / 0 errors · **17 files / 106 passed**
  · build ✓ (Vite ESM, CSS 20.17 kB)
- `npm test` — 3 consecutive standalone runs: **17 / 106 passed** each (7.08s / 6.83s / 7.1s), exit 0
  all three — no flakiness.
- Banned-word scan: 0 banned strings in rendered UI; wording contract mechanically enforced by test.
- No `setInterval`/polling in app code (ProcessingSteps test proves absence of `setInterval`/`setTimeout`).

## Scope check

Only `frontend/**` (src, components, pages, api, state, mocks, styles, tests) + `logs/task-11-frontend.md`
changed. **No** backend, docs, lock-file, `.env`, screenshots, or root-file changes. `git diff` shows
frontend-only scope; branch matches `feature/task-11-frontend`.

## Known limitations (stated honestly)

- Playwright/coverage not added (new deps require approval per AGENTS §5).
- Live-browser walkthrough at projector resolutions not run in this session (no browser tool available);
  responsive rules are verified by CSS-inspection + tests, marked accordingly (not claim-browser-verified).

## Open questions for the lead

1. Wording: confirm final projects-label copy beyond the approved shop vocabulary.
2. Whether `/demo` needs a separate nav entry vs. single dashboard — currently topbar routes to it.

## Approvals required before merge

Per AGENTS §5: no new deps, no backend fields, no env vars beyond `VITE_API_BASE_URL`. All staged
changes are within the task's allowed-files list.
