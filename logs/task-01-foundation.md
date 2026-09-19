# Task 01 — Repository and application foundation — Development Log

**Owner:** Member D / later audit on `feature/task-02-database`
**Branch:** originally `feature/task-01-foundation` (merged via PR #1); remaining gaps recorded here
**Started:** 2026-09-18
**Status:** Not ready for a complete Task 01 DoD close-out

---

## Contracts this task implements

- `docs/backend.md` / `docs/frontend.md` — folder skeleton
- `docs/configuration.md` — Settings fields, validation, `.env.example` defaults
- `docs/api.md` — `/api/v1`, `GET /health` keys, error envelope
- `docs/testing.md` — `integration` marker excluded from default pytest
- `tasks/01-foundation.md` — full work order

## Decisions I made inside my own scope

| Date | Decision | Why | Reversible? |
|---|---|---|---|
| 2026-09-19 | Do not invent OCR/Hardhat results for machines that were not tested | AGENTS.md Rule 12 | n/a |
| 2026-09-19 | Leave `requirements.txt` pydantic range and alembic pin unchanged | Shared file; lead decision required | Yes |
| 2026-09-19 | Do not edit frontend `package.json` `^` pins | User forbade frontend changes | n/a |
| 2026-09-19 | Keep `.env.example` `BLOCKCHAIN_ENABLED=true` | Locked in `docs/configuration.md` | Must match docs |

## Interfaces I published for other tasks

`Settings` field names match `docs/configuration.md`. Fail-fast when `BLOCKCHAIN_ENABLED=true` and contract address / salt / RPC URL are empty.

Health keys: `status`, `database`, `ocr_adapter`, `blockchain`. After Task 02, `database` is `"ok"`/`"error"` from `SELECT 1`, not `"not_configured"`.

## Progress

### 2026-09-19 (audit)
- Did: Confirmed fail-fast Settings, health four keys, global 500 envelope, `.gitignore`.
- Did: Reverted accidental `BLOCKCHAIN_ENABLED=false` in `backend/.env.example`.
- Did: Set pytest `addopts` to `-m "not integration" -p no:asyncio -p no:warnings`.
- Next: Environment report still needs a Python 3.11 demo machine; teammates must add their rows.

## Blockers and open questions

| # | Question | Asked on | Answer | Resolved |
|---|---|---|---|---|
| 1 | Demo machine with Python 3.11 where PaddleOCR smoke + Hardhat pass | 2026-09-19 | Not identified. This laptop is 3.14; OCR smoke failed. | ☐ |
| 2 | Exact pins (`>=`, `^`) in requirements.txt / frontend package.json | 2026-09-19 | Left unchanged without lead approval / no frontend edits | ☐ |
| 3 | D-02 / D-05 / D-09 promotion from provisional | 2026-09-19 | ENVIRONMENT-REPORT exists but OCR did not pass here | ☐ |

## Tests

| Command | Last run | Result |
|---|---|---|
| `cd backend && pytest` (after pytest.ini change) | 2026-09-19 | `70 passed in 2.11s` (`.\venv\Scripts\python.exe -m pytest`) |

`docs/ENVIRONMENT-REPORT.md` previously claimed 18/18 tests; that is outdated once Task 02 tests exist. Do not treat that number as current.

## Known limitations at handoff

- No `backend/.env` in the repo (correct). Copy `.env.example` to `.env`, then either fill `BLOCKCHAIN_CONTRACT_ADDRESS` + `CHAIN_EVENT_SALT` or set `BLOCKCHAIN_ENABLED=false` **in `.env` only**.
- `logs/README.md` was never created (task asked to copy the development-log template there). `logs/log_entry.md` exists instead.
- ENVIRONMENT-REPORT covers one Windows 3.14 machine; OCR smoke failed; this machine is **not** the demo machine.

## Handoff notes

- Files changed in the 2026-09-19 audit pass: `backend/.env.example` (revert), `backend/pytest.ini`, this log.
- What I did **not** do: invent teammate environment rows, change frontend, pin alembic/pydantic, commit/push.
