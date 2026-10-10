# Task 11 — Frontend upload, results, and review dashboard — Development Log

**Owner:** Member D (suggested) — built over repeated developer/AI sessions
**Branch:** `feature/task-11-frontend` (note: repository is **not** a git repo as of this log)
**Started:** 2026-09-24 (work spans multiple earlier sessions)
**Status:** Ready for review — with two open blockers, see "Blockers and open questions"

---

## Contracts this task implements

- `docs/frontend.md` — page flow, locked folder layout, hard rules (no hardcoded categories, banner
  on every result view, two badges never merged, no polling), loading/error/empty states,
  error-envelope conventions, blockchain failure detail.
- `docs/api.md` — every endpoint consumed (`GET /document-types`, `POST /documents`, `GET
  /documents/{id}`, `GET /documents/{id}/extraction`, `POST /documents/{id}/verify`, `POST
  /documents/{id}/review`, `GET /documents/{id}/verifications`, `GET /verifications/{id}`, `GET
  /verifications/{id}/blockchain`) plus the error envelope (`{ error: { code, message, details } }`).
- `docs/verification-rules.md` §"Status vocabulary" — exact status labels via `StatusBadge`.
- `docs/glossary.md` §"Words we deliberately do not use" — enforced mechanically by `wording.test.tsx`.
- `docs/category-schemas.md` — rendered only through `GET /document-types`, never hardcoded.
- `docs/configuration.md` — `VITE_API_BASE_URL`; runtime mock switches via URL query flags.
- `docs/blockchain.md` + `docs/judging-and-pitch.md` §3 — "what this proves and what it does not"
  wording on the receipt page.
- `AGENTS.md` Rules 1, 2, 4, 5 — no authenticity claims, technical failure ≠ verdict, no-record is
  neutral, OCR confidence ≠ authenticity confidence.

## Decisions I made inside my own scope

| Date | Decision | Why | Reversible? |
|---|---|---|---|
| 2026-09-24 | Mock mode switched by URL query flags (`?mock=…`, `?chain=…`, `?slow=1`) rather than only an env var | Lets the presenter demonstrate any status/error code on demand during rehearsal | Yes (config-only) |
| 2026-09-24 | `SyntheticDataBanner` kept per-page (rendered inside pages) instead of moving it to `AppLayout` | Guarantees NFR-08 banner on every result view and keeps the four page tests asserting it green | Yes, with test surgery |
| 2026-09-24 | `VERIFIED_MATCH` uses blue, not green; green reserved for reviewer ACCEPT/CORRECT action affordance | Status colours must not imply authenticity (task §11) | Yes (CSS only) |
| 2026-09-24 | `recentDocuments` hydrates "current status" from `GET /verifications/{id}` only for the listed ids | In-session "Documents"/"History" convenience; the endpoint list is the display source, `is_current` is never computed client-side. Needs project-lead sign-off that this is in scope | Yes |
| 2026-09-24 | Full reskin of `styles.css` to the reference console design (obsidian `#0f172a`, `#f8fafc` page, 4px/8px radii, Geist/Inter/JetBrains Mono) keeping every existing class name; status label strings and all copy untouched | User provided the reference screens (zips: DESIGN.md + code.html) and requested all screens match and stay responsive | Yes (CSS only) |
| 2026-09-24 | Added presentational `PipelineTrack` (1. Upload → 5. Record) on Upload/Detail/Result/Review/Receipt pages | Mirrors the reference console workflow; no logic added | Yes |

## Interfaces I published for other tasks

No new backend-facing contract. The frontend consumes the frozen `docs/api.md` shapes through
`src/types/api.ts`. Task 10's real backend is expected to match `docs/api.md`; **any divergence must
be reported to Task 10's owner, not worked around** (so far no divergence has been observed because
the real backend has not been exercised end-to-end — it was not running during this task).

The mock-mode handoff for rehearsal:

```text
?mock=<doc|status-name|err-code>   select a fixture scenario
?chain=<confirmed|pending|failed|not-requested>
?slow=1                            add artificial delay to observe loading states
```

## Progress

### 2026-09-25 (splash, demo login, nav, review redirect, API root)
- Did: Frontend-only splash (~2.6s CSS animation) then demo login/register (no backend auth; D-11 unchanged). Sidebar: "Upload Document"; removed Help/About/Demo Mode from nav; active item highlighting; back/forward in the topbar. After `REVIEW_REQUIRED` or `INTEGRITY_MISMATCH`, upload/detail navigate to the review page. Vite default opens `/` and proxies `/api` to port 8000. API client treats HTML responses as a reachable-API error. `recentDocuments` hydrates with `allSettled` so one bad id does not empty the queue. Backend: HTML landing at `GET /` plus CORS for localhost/127.0.0.1:5173.
- Verified: see session test run below.
- Next: remaining UX polish after the user reviews this pass. No commit/push.

### 2026-09-24 (capstone session — reskin + audit)
- Did: Rewrote `frontend/src/styles.css` to the reference console design (all classes preserved).
  Added Google Fonts (Geist/Inter/JetBrains Mono) + console title to `frontend/index.html`.
  Restyled `SyntheticDataBanner` (same test-visible string). Added `PipelineTrack` component and wired
  it into five pages. Audited Task 11 acceptance criteria against the implementation.
- Verified by running:
  - `npm run lint` → **0 findings**
  - `npm test` → **17 files, 106 tests passed** (vitest 3.2.7, 12.65s)
  - `npx tsc -b` → exit 0
  - `npm run build` → ✓ 296 modules, built in 333ms
- Next: see "Blockers and open questions" — real-backend walkthrough and git workflow are the two
  remaining Definition-of-Done items.

### Earlier sessions (Steps already delivered)
- Did: Built all six pages + all listed components; `api/client.ts` error-envelope parsing with typed
  `ApiError`; `state/useDocument` + `state/useVerification`; `loading/error/empty` on every page;
  `FieldComparisonTable` showing every match field (no hidden mismatches); `ReviewPage` with
  ACCEPT/CORRECT/UNRESOLVED + pre-filled corrections + "(reviewer-corrected)" wording; receipt page
  with "what it proves and what it does not" + `error_code` plain-language translation; `DemoDashboard`
  projector page (`/demo` redirects to most recent document, EmptyState otherwise); mock server for all
  endpoints + error codes; MSW/vitest suite.
- Verified by running: `npm test` → 106 passed (multiple runs), `npm run lint` clean, `npx tsc -b`
  exit 0, `npm run build` ✓, dev server booted with no console errors.
- Fixed during the "solve the errors" session: hoisted inline `Row`→`ReceiptRow` (lint warning);
  `recentDocuments` effect restructured to a single async `load()` (no sync setState in effect);
  `SearchContext`/`useShellSearch` moved out of `AppLayout.tsx` into `state/shellSearch.tsx`
  (react/only-export-components). Responsive pass: table min-widths inside scroll wrappers, `td`
  overflow-wrap, `48vh` preview clamp, 480px mobile tier, `16px` minimum text.

## Blockers and open questions

| # | Question | Asked on | Answer | Resolved |
|---|---|---|---|---|
| 1 | Real backend (`http://127.0.0.1:8000`) was **not running** — the acceptance "manual walkthrough against the real backend, no console errors" and the api.md-divergence report cannot be completed here | 2026-09-24 | — | ☐ |
| 2 | Project root is **not a git repository** — `feature/task-11-frontend` branch, push, and PR (Definition of Done) cannot be produced | 2026-09-24 | — | ☐ |
| 3 | `frontend/index.html` edited (fonts + title) — this file is outside the task's Allowed Files list; the reskin required it and was explicitly requested by the user | 2026-09-24 | — | ☐ |
| 4 | Result page cannot detect a "(reviewer-corrected)" outcome on re-navigation (both return `VERIFIED_MATCH`); noted on the post-review success screen only | earlier | — | ☐ |
| 5 | `CORRECT` implemented as success screen + "View the new result" link, not silent auto-navigation | earlier | — | ☐ |
| 6 | `frontend/DESIGN_SPEC.md` referenced by later docs does not exist; the 17-screen inventory and §18 box were not implemented | earlier | — | ☐ |

## Tests

| Command | Last run | Result |
|---|---|---|
| `cd frontend && npm test` | 2026-09-24 | 17 files / 106 passed, 12.65s |
| `cd frontend && npm run lint` | 2026-09-24 | 0 findings |
| `cd frontend && npx tsc -b` | 2026-09-24 | exit 0 |
| `cd frontend && npm run build` | 2026-09-24 | ✓ built in 333ms |

Coverage highlights: StatusBadge exact documented labels; banned-words source-wide scan (no
"Verified/Authentic/Genuine/Valid/Invalid/Forged/Rejected/Fraud/Tamper"; "fake" restricted to the
`NO_TRUSTED_RECORD` label; "Valid" only in the schema `valid_until` label); banner present on every
result page; two-badge separation; FieldComparisonTable shows every field incl. mismatches; category
form renders from `GET /document-types`; 400/413/415/422 distinct upload messages; history uses
`is_current` from the endpoint (never computed client-side); `FAILED` blockchain shows translated
`error_code` + "verification unaffected" note; no fabricated hashes; ProcessingSteps test asserts no
`setInterval`/`setTimeout(..)` in non-test source (no polling).

## Known limitations at handoff

- The AI cannot view images (`screen.png`, pasted screenshots fail with "this model does not support
  image input"); the reskin was derived from the reference zip's `DESIGN.md` + `code.html`, which are
  complete.
- `NO_TRUSTED_RECORD`'s label intentionally contains "fake" (it is the documented, spec-mandated
  wording); the wording test restricts "fake" to that one label.
- `UploadPage.test.tsx` carries a harmless `{ timeout: 6000 }` on a navigation assertion.
- The pipeline track and banner restyle are CSS/presentational only; no copy or status strings changed.

## Handoff notes

- Files changed (frontend scope): `src/pages/*Pages.tsx`, `src/components/*` (StatusBadge, FieldComparison,
  SyntheticDataBanner, UploadDropzone, LoadingState, ErrorState, EmptyState, BlockchainStatusBadge,
  ProcessingSteps, PipelineTrack), `src/api/client.ts` + four module wrappers, `src/state/useDocument.ts`,
  `src/state/useVerification.ts`, `src/state/recentDocuments.ts`, `src/state/shellSearch.tsx`,
  `src/state/preview.ts`, `src/mocks/*`, `src/types/api.ts`, `src/utils/*`, `src/styles.css`,
  `frontend/index.html` (outside allowed list — flagged), `frontend/vite.config.ts`, `frontend/package.json`.
- What the next task/human needs to know: (1) start the backend, then walk the full flow and confirm
  every response matches `docs/api.md` — report any difference to Task 10's owner, do not adapt the
  frontend; (2) this repo needs `git init` + branch `feature/task-11-frontend` + PR per
  `docs/git-workflow.md` before Task 11 can be marked done; (3) mock-mode URL flags document how to
  rehearse awkward states.
- What I deliberately did **not** do: no backend or `docs/` changes; no status/field/endpoint invented;
  no commit/push (AGENTS.md §6 forbids committing without explicit human authorization — and there is
  no git repo anyway).

---

## QA pass (task-11 QA file § DoD) — session record

**Flakiness check — `npm test` 3 consecutive standalone runs, exact captured output:**
- Run 1 (via `npm run check` ⇐ typecheck+lint+test+build): **17 files, 106 passed**, duration 9.94s, exit 0
- Standalone run 2: **17 files, 106 passed**, duration 8.41s, standalone-exit=0
- Standalone run 3: **17 files, 106 passed**, duration 10.07s, standalone-exit=0
- `npm run check` (typecheck `tsc -b` exit 0, `oxlint` 0 warnings / 0 errors, `vitest run` 106/106,
  `tsc -b && vite build` ✓) — passes end to end.

**Wording / anti-polling / no-hardcode (§1.7, §1.10, §3.1):**
- static scan of `src/**` (excl. tests/mocks): no single `setInterval` / `setTimeout` in app code —
  the only occurrences anywhere are in `wording.test.tsx` asserting their ABSENCE and a jsdom
  `setTimeout` helper inside test files.
- banned-word grep hits under `src/**` are all inside `wording.test.tsx`/`StatusBadge` contract that
  asserts the absences — no banned string in any rendered UI string.
- categories still arrive only from `GET /document-types`; field labels only from the endpoint; no
  hardcoded category/field list.

**Responsive deltas applied this session (Phase 2 §2.4/§2.7):**
- `index.html`: viewport meta now `viewport-fit=cover` (was missing → safe-area insets were inert).
- `assets/css`: `--safe-*` insets from `env(safe-area-inset-*)` on `.sidebar`, `.topbar`, footer; a
  `min-height: 44px` vs 36px touch floor on `.topbar__menu` (was 36px, below the 44px guide).
  Reduced-motion block intact; fluid `clamp()`/`auto-fit`/`min()` already in use; no `100vw`
  anywhere (0 hits).

**Scripts added (§3.3):** `typecheck` (`tsc -b --pretty false`) and `check` (typecheck→lint→test→build).
  `test`, `test:watch`, `lint`, `build` already existed. Nothing silently swallows failures.

All changes are **staged** (index updated) and **uncommitted** — awaiting explicit commit/PR
authorization per AGENTS.md §6. No Playwright/coverage/axe installed (no approval granted).
---

## FINAL QA + PR prep (Part C/D/E, this session) — 2026-09-24

### Pre-PR checks (exact, in order)
- \
pm run check\ -> typecheck \	sc -b\ exit 0; oxlint 0 warnings / 0 errors; **17 files / 106
  passed**; build ✓ (CSS 20.17 kB). 
- \
pm test\ standalone x3 -> 17/106, 17/106, 17/106 passed; exit 0 each; no flaky.
- Misc proofs: no 100vw in styles (0 hits); dvh/svh used; safe-area insets added on notched phones;
  \prefers-reduced-motion\ respected; touch targets >= 44px; tables scroll in own overflow-x
  containers; no setInterval/setTimeout polling in app code (test-enforced).

### Scope audit (exact \git diff --cached --name-only\, no truncation)
- 74 frontend/** + 1 logs/task-11-frontend.md = staged. 0 backend, 0 docs, 0 root config/.env,
  0 screenshots/coverage. No scope violations.

### Part E
- Branch: \eature/task-11-frontend\ (matches docs/git-workflow.md convention).
- PR_DESCRIPTION.md written at repo root (authorized by task §8 + Part E) — NOT committed.
- Nothing committed / pushed / merged; awaiting human authorization (AGENTS §6).

### Nothing hidden
- Cannot read images in this session (no image-input for the assistant), so screenshot-level polish
  is verified by CSS inspection + tests, not by eyeballing a pasted screenshot.

---

## Supabase auth completion session - 2026-10-09

### Changes made
- Repaired malformed TypeScript in the Supabase auth/session files by removing stray Markdown code fences.
- Replaced the browser demo login/register path in `AuthPage.tsx` with `registerUser()` and `loginUser()`.
- Added pending states, safe auth error messages, password visibility preservation, email normalization, and email-confirmation messaging.
- Kept `setDemoSession()` as a test-only compatibility helper and kept session-change notifications for `recentDocuments`.
- Made protected/guest routes wait for Supabase session restoration before redirecting.
- Made `AppLayout` and `ProfilePage` read auth state reactively through `useAuthSession()`.
- Switched profile logout to Supabase sign-out and changed account deletion copy to state that a secure backend operation is required.
- Restored the document detail synthetic-data banner/test-visible preview fallback and removed banned wording from the blockchain receipts page/source scan.

### Verification run this session
- `npm run typecheck` -> exit 0.
- `npm run lint` -> exit 0, with one warning in `src/pages/SplashPage.tsx` about missing `finish` in a hook dependency array.
- `npm test` -> first sandbox run failed with `spawn EPERM`; reran with approved escalation. Final result: 19 files / 119 tests passed.
- `npm run build` -> first sandbox run failed with `spawn EPERM`; reran with approved escalation. Final result: built successfully in 729ms, with Vite chunk-size warning for chunks over 500 kB.

### Notes
- No Supabase secrets were printed or added.
- No backend schema, RLS policy, database migration, or service-role key was added.
- Manual Supabase Dashboard setup is still required: email/password auth enabled, frontend URL/redirect URLs configured, and a `public.profiles` table/RLS policy that lets authenticated users read/upsert only their own profile if profile display names should persist before/after reload.

---

## Supabase auth failure follow-up - 2026-10-09

### Root cause found
- Ran a one-time Supabase Auth sign-up probe with a synthetic `demo-auth-check+...@example.test`
  address and the local frontend `.env` values. The request reached Supabase and returned
  `AuthApiError`, status `429`, code `over_email_send_rate_limit`, message `email rate limit
  exceeded`.
- This explains the observed empty Supabase Authentication > Users table: Supabase rejected the
  registration while trying to send the confirmation email, before creating an auth user.
- Login then fails with rejected credentials because no account was created.

### Changes made
- `AuthPage.tsx`: auth errors are now read by `message`, `code`, and `status`, not only by
  `instanceof Error`. The Supabase `over_email_send_rate_limit` / HTTP 429 failure now displays the
  actual safe cause and next action instead of falling through to the generic message.
- `auth.ts`: profile upsert is now non-blocking after successful Supabase registration. A missing
  optional `profiles` table or restrictive profile RLS policy no longer makes real Auth account
  creation look like a failed registration.
- `AuthPage.test.tsx`: added coverage for the Supabase email send rate-limit error object.

### Verification run this follow-up
- `npm run typecheck` -> exit 0.
- `npm test -- AuthPage.test.tsx` -> first sandbox run failed with `spawn EPERM`; reran with
  approved escalation. Final result: 1 file / 4 tests passed.
- `npm test` -> approved escalation because of the same esbuild/vitest spawn restriction. Final
  result: 20 files / 123 tests passed.

### Notes
- The temporary Supabase probe file was removed after use.
- No Supabase secrets were printed or added.
- No database schema, migration, service-role key, backend endpoint, or privileged account-deletion
  path was added.
- Supabase project configuration still needs attention outside the repo: wait for the email rate
  limit window to clear or configure custom SMTP, and make sure the frontend URL is in the allowed
  redirect URLs for confirmation links.

---

## Auth/account isolation + AI summary follow-up - 2026-10-09

### Changes made
- Changed cold app-load session restoration so a persisted Supabase session no longer skips the
  splash-to-login/register path. A user must sign in/register during the current app load before
  protected routes open.
- Fixed `recentDocuments` account isolation: switching to an account with an empty document store now
  clears the in-memory list instead of showing the previous account's documents. The in-memory
  fallback still works when localStorage is unavailable.
- Added Supabase-backed account deletion: frontend calls `DELETE /api/v1/account` with the current
  Supabase access token; backend verifies the token and deletes that exact Auth user using the
  backend-only service-role key. After success, the frontend clears that email's local document list
  and cached previews, signs out locally, and sends the user to registration.
- Added backend-only Supabase account deletion config placeholders to `backend/.env.example` and
  documented the new endpoint/config in `docs/api.md` and `docs/configuration.md`.
- Switched the default AI summary Ollama URL from `localhost` to `127.0.0.1` to avoid local host
  resolution differences. Verified this machine's Ollama responds at `/api/tags` and has
  `llama3.2:latest` installed.

### Verification run this follow-up
- `Invoke-WebRequest http://127.0.0.1:11434/api/tags` -> returned models including
  `llama3.2:latest`.
- `Invoke-WebRequest http://127.0.0.1:11434/api/generate` with `llama3.2:latest` -> returned a
  summary response.
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_account.py tests\test_academic_summary.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-account-summary`
  -> 8 passed in 0.94s.
- `cd backend; .\venv311\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .test-tmp\pytest-full`
  -> 307 passed, 1 deselected in 16.58s.
- `cd frontend; npm run typecheck` -> exit 0.
- `cd frontend; npm run lint` -> exit 0 with the existing `SplashPage.tsx` exhaustive-deps warning.
- `cd frontend; npm test` -> 21 files / 126 tests passed.
- `cd frontend; npm run build` -> built successfully in 1.08s, with the existing Vite chunk-size
  warning for chunks over 500 kB.

### Setup note
- Account deletion requires backend `.env` values `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
  The service-role key must stay backend-only and must not be added to any `VITE_` variable.

---

## AI summary multi-document timeout follow-up - 2026-10-09

### Root cause
- Single-document summaries worked, but multi-document summaries could send full raw OCR text for
  every selected document to local Ollama. That made the prompt much larger and could trigger a
  local Ollama timeout, which surfaced in the frontend as `AI_SUMMARY_UNAVAILABLE`.

### Changes made
- Multi-document summaries now send a compact, comparison-focused prompt using extracted fields
  first, with only a bounded OCR excerpt per document.
- The Ollama adapter now caps local generation with deterministic options (`temperature: 0`,
  bounded context, bounded predicted tokens) so comparison summaries finish more reliably.
- Added backend coverage proving a multi-document request includes both document labels, uses the
  multi-document comparison prompt, and keeps the prompt bounded.

### Verification run this follow-up
- `cd backend; .\venv311\Scripts\python.exe -m pytest tests\test_academic_summary.py -q -p no:cacheprovider --basetemp .test-tmp\pytest-academic-multi`
  -> 7 passed in 0.82s.
- `cd backend; .\venv311\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .test-tmp\pytest-full-academic-multi`
  -> 308 passed, 1 deselected in 16.36s.
- `cd frontend; npm run typecheck` -> exit 0.

### Runtime note
- Restart the backend after pulling this change so the updated summary service and Ollama adapter are
  loaded by Uvicorn.

---

## Auth reload session follow-up - 2026-10-10

### Change made
- Adjusted the Supabase session compatibility layer so the first frontend start in a tab still shows
  splash then login/register, but a reload after a successful login restores the existing Supabase
  session and continues into the app.
- The restore marker is stored in `sessionStorage`, so it survives reloads in the same tab but is
  cleared on logout/account deletion and does not turn a brand-new tab into an automatic login.

### Verification run this follow-up
- `cd frontend; npm run typecheck` -> exit 0.
- `cd frontend; npm test -- AuthPage.test.tsx ProfilePage.test.tsx recentDocuments.test.tsx`
  -> 3 files / 12 tests passed.
