# Core Task 01 — Student & Government Document Database — Development Log

**Owner:** Rehan
**Branch:** `feature/core-student-gov-db` (local, uncommitted)
**Status:** Ready for review — awaiting project-lead approval of the proposed contract changes

## Contracts this task implements
- `CORE.md` Task 1 (database for student and government documents, real-time behaviour, backend boundary).
- Proposed additions to `docs/data-model.md` and `docs/api.md` (marked PROPOSED).

## Decisions inside my scope
| Decision | Why | Reversible? |
|---|---|---|
| Link table `student_documents` instead of adding `student_id` to `documents` | `create_all` would not alter an existing table, and `documents` is a locked contract | Yes |
| Aadhaar stored only as hash + last 4 | Raw identifier must not be stored or exposed | Yes |
| Deterministic marksheet summary, no LLM | `decisions.md` D-04 / D-06 / D-07 and AGENTS Rule 8 | Yes |
| Fixture "Aadhaar" values start with 0 (`0000 0000 0001`) | Invalid by construction, so they cannot be a real number (Rule 7) | Yes |
| Refresh on tab focus + Refresh button (no timers) | `ProcessingSteps.test.tsx` forbids timers in app source; true real-time needs an approved transport | Yes |

## Needs project-lead approval (AGENTS.md §5)
- New tables (`data-model.md`) and endpoints / error codes (`api.md`).
- One-line change in `backend/app/main.py` (Task 01 file) to register the new router.
- New frontend route `/students` and a nav entry in `AppLayout.tsx` (Task 11 files).

## Interfaces published for other tasks
`app/services/student_service.py`: `find_student_by_aadhaar`, `get_government_records`,
`add_marksheet`, `get_marksheet_history`, `link_document`, `list_student_documents`.

## Verification (commands actually run)
- `cd backend && BLOCKCHAIN_ENABLED=false python -m pytest -q` → 311 passed (296 existing + 15 new).
- `python -m app.fixtures.seed_students` run twice → CREATED x3, then UNCHANGED x3.

## Open questions for the project lead
1. **Real-time transport.** `ProcessingSteps.test.tsx` forbids `setInterval`/`setTimeout` in app source, so
   the page refreshes on tab focus, on the Refresh button, and after actions. For live updates while the
   tab stays focused, approve either (a) a small polling exception for read-only data, or (b) an SSE
   endpoint. I did not pick one.
2. **Approval of the proposed tables, endpoints and error codes** (see the PROPOSED sections in `docs/`).

## Pre-existing failures on `main` (not caused by this task; I did not touch them)
- `frontend/src/pages/UploadPage.test.tsx` ends mid-file (syntax error at line 128), which also fails `tsc -b` and `oxlint`.
- `DocumentDetailPage > shows the synthetic data banner and preview state` fails.
- `wording.test.tsx > contains no banned word anywhere in non-test source` fails.

## Frontend verification (commands actually run)
- `npx vitest run src/pages/StudentsPage.test.tsx` → 4 passed.
- Full `npx vitest run`: the same 3 failures as untouched `main`, nothing new.
