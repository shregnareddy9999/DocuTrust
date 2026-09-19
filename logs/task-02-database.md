# Task 02 — Database and persistence model — Development Log

**Owner:** Member C / AI session
**Branch:** `feature/task-02-database`
**Started:** 2026-09-18
**Status:** Ready for review (git commit/push not authorized)

---

## Contracts this task implements

- `docs/data-model.md` — six entities, columns, FKs, enums, “current verification”
- `docs/backend.md` — `models/`, `repositories/`, `db.py`, startup `create_all()`
- `docs/verification-rules.md` — six `verification_results.status` values
- `docs/blockchain.md` — four `recording_status` values and four `error_code` values
- `docs/category-schemas.md` — four `documents.category` / `registry_records.category` values
- `docs/configuration.md` — `DATABASE_URL`, SQLite file at `data/app.db`
- `tasks/02-database-model.md` — allowed files, repository surface, tests, acceptance

---

## Decisions I made inside my own scope

| Date | Decision | Why | Reversible? |
|---|---|---|---|
| 2026-09-18 | `create(session, row)` takes a constructed ORM instance, not kwargs | Least invented public surface | Yes |
| 2026-09-18 | `blockchain_repo.get_by_verification_id` returns **all** rows, newest first | Retries create multiple rows | Yes |
| 2026-09-18 | Writes use `session.add` + `session.flush()`, never `commit()` | Request-scoped sessions belong to the caller | Yes |
| 2026-09-18 | `list_recent(session, limit)` requires caller `limit`; order `uploaded_at` desc, `rowid` desc | Docs name the function but not a page size | Yes |
| 2026-09-19 | Drop `Mapped[T \| None]` unions; keep `nullable=True` on `mapped_column` | Python 3.14 + SQLAlchemy 2.0 `make_union_type()` crash | Yes (or later SQLAlchemy bump with lead approval) |
| 2026-09-19 | Enable `PRAGMA foreign_keys=ON` on SQLite connects in `db.py` | SQLite otherwise ignores FKs; task requires integrity errors to surface | Yes |

> Schema column names, enum value sets, and API shapes were not changed.

---

## Interfaces I published for other tasks

All functions take an explicit `sqlalchemy.orm.Session`. JSON text columns are stored as the caller supplied them (no parse/repair). Integrity errors are not swallowed.

```python
# documents_repo
create(session, document: Document) -> Document
get_by_id(session, document_id: str) -> Document | None
update_processing_state(session, document_id: str, processing_state: ProcessingState) -> Document | None
list_recent(session, limit: int) -> list[Document]

# extraction_repo
create(session, extraction: ExtractionResult) -> ExtractionResult
get_latest_for_document(session, document_id: str) -> ExtractionResult | None
get_latest_successful_for_document(session, document_id: str) -> ExtractionResult | None  # SUCCEEDED only

# registry_repo
create(session, record: RegistryRecord) -> RegistryRecord
get_by_category_and_key(session, category: DocumentCategory, synthetic_record_key: str) -> RegistryRecord | None
list_active_by_category(session, category: DocumentCategory) -> list[RegistryRecord]  # active=True
get_by_id(session, record_id: str) -> RegistryRecord | None

# verification_repo  — get_latest_for_document is the ONLY definition of "current"
create(session, result: VerificationResult) -> VerificationResult
get_by_id(session, verification_id: str) -> VerificationResult | None
get_latest_for_document(session, document_id: str) -> VerificationResult | None
list_for_document(session, document_id: str) -> list[VerificationResult]  # newest first

# review_repo
create(session, action: ReviewAction) -> ReviewAction
list_for_verification(session, verification_id: str) -> list[ReviewAction]  # newest first

# blockchain_repo
create(session, record: BlockchainRecord) -> BlockchainRecord
get_by_verification_id(session, verification_id: str) -> list[BlockchainRecord]
get_active_for_verification(session, verification_id: str) -> BlockchainRecord | None  # newest non-FAILED
mark_confirmed(session, record_id: str, confirmed_at: datetime) -> BlockchainRecord | None  # PENDING only
mark_failed(session, record_id: str, error_code: BlockchainErrorCode) -> BlockchainRecord | None  # PENDING only
```

There is **no** `verification_repo.update_status()`. A retry after a failed chain submit **creates a new row**.

There is **no migration tool**. Schema changes mean deleting the local SQLite file and re-seeding (Task 03).

---

## Progress

### 2026-09-18
- Did: Implemented six repository modules against documented models.
- Verified by running: `python -c "from app.repositories import documents_repo"` → failed then because `app.db` had no `Base` (later resolved).
- Next: Wire `db.py` / models / tests (other Task 02 work on the same branch).

### 2026-09-19
- Did: Diagnosed model import crash as Python 3.14 + SQLAlchemy stringified `X | None` unions, not a missing `VerificationResult` import. Removed `Mapped[T | None]` from blockchain/verification/review models; left `nullable=True`. Enabled SQLite FK pragma in `db.py`.
- Verified by running: with `BLOCKCHAIN_ENABLED=false`, `python -c "from app.models import BlockchainRecord; print('Model import OK')"` → `Model import OK`
- Verified by running: `.\venv\Scripts\python.exe -m pytest -q -p no:asyncio` → `70 passed in 2.13s`
- Manual: started uvicorn with `BLOCKCHAIN_ENABLED=false`; `GET http://127.0.0.1:8000/api/v1/health` → `200 {"status":"ok","database":"ok","ocr_adapter":"paddleocr","blockchain":"disabled"}`
- Manual: Python `sqlite3` on `backend/data/app.db` listed all six tables with documented column names (see Tests / Manual below).
- Manual: `create_all` / `drop_all` / `create_all` on a **temporary** SQLite file → `RECREATE_OK`. Did **not** delete `backend/data/app.db`.
- Next: human review + authorized git commit/push.

### 2026-09-19 (audit follow-up)
- Did: Reverted `backend/.env.example` `BLOCKCHAIN_ENABLED=true` (locked default). Local start uses gitignored `.env`, not `.env.example`.
- Did: `pytest.ini` `addopts = -m "not integration" -p no:asyncio -p no:warnings`.
- Verified by running: `cd backend && .\venv\Scripts\python.exe -m pytest` → `70 passed in 2.11s` (70 items collected; no INTERNALERROR).
- Next: human commit/push; optional delete-and-recreate of `data/app.db` only with owner approval.

---

## Blockers and open questions

| # | Question | Asked on | Answer | Resolved |
|---|---|---|---|---|
| 1 | Python 3.14 + SQLAlchemy 2.0 `Union.__getitem__` on stringified `T \| None` | 2026-09-19 | Workaround: no `Mapped[T \| None]`; nullability stays on `mapped_column`. Do not bump SQLAlchemy without lead approval. | ☑ workaround |
| 2 | Bare `pytest` fails: pytest-asyncio `Package` has no `obj` | 2026-09-19 | Workaround: `pytest.ini` now includes `-p no:asyncio` (2026-09-19 audit). | ☑ workaround |
| 3 | May `backend/data/app.db` be deleted to re-run the “delete and recreate” demo check? | 2026-09-19 | Not asked until confirmed empty of user data. Recreate proven on a temp file instead. | ☐ wait for owner |

---

## Tests

| Command | Last run | Result |
|---|---|---|
| `.\venv\Scripts\python.exe -c "from app.models import BlockchainRecord; print('Model import OK')"` (with `BLOCKCHAIN_ENABLED=false`) | 2026-09-19 | `Model import OK` |
| `.\venv\Scripts\python.exe -m pytest` | 2026-09-19 (after pytest.ini) | `70 passed in 2.11s` |
| `.\venv\Scripts\python.exe -m pytest -q -p no:asyncio` | 2026-09-19 | `70 passed in 2.13s` |
| `.\venv\Scripts\python.exe -m pytest tests/test_models.py tests/test_repositories.py -p no:asyncio` | included in the 70 | passed as part of full suite |

Tests use `conftest.py` temp SQLite files, not `backend/data/app.db`.

---

## Manual checks

| Check | Result |
|---|---|
| Start app (`BLOCKCHAIN_ENABLED=false`) | Application startup complete |
| `GET /api/v1/health` | `database: "ok"`; blockchain `"disabled"`; no connection string in body |
| Six tables in `backend/data/app.db` | `blockchain_records`, `documents`, `extraction_results`, `registry_records`, `review_actions`, `verification_results` |
| Column names vs `docs/data-model.md` | Matched for all six tables (Python `sqlite3` + `PRAGMA table_info`) |
| Recreate after delete of **local demo DB** | **Not done** on `data/app.db`. Proven on a temp file (`RECREATE_OK`). |
| `sqlite3` CLI | Not used; Python `sqlite3` module used instead |

---

## Known limitations at handoff

- SQLite enum enforcement is weaker than Postgres. Application-layer `Enum(..., native_enum=False, create_constraint=True, validate_strings=True)` is used; undocumented values are rejected by SQLAlchemy, not by a native PG enum.
- Python 3.14 workaround: optional columns are annotated as `Mapped[T]` with `nullable=True`. Runtime nullability is unchanged.
- Default `pytest` uses `pytest.ini` `-p no:asyncio` so the Python 3.14 pytest-asyncio collection bug is avoided. `pytest -m integration` still available for later tasks.
- Live app import still requires valid Settings (set `BLOCKCHAIN_ENABLED=false` or fill contract address + `CHAIN_EVENT_SALT`).
- No Alembic/migrations. Changing the schema means deleting the local DB and re-seeding.
- Task 03 seeding is not implemented.

---

## Handoff notes

- Files changed this finish pass (plus earlier Task 02 work already on the branch): models `blockchain.py` / `verification.py` / `review.py`; `backend/app/db.py` (FK pragma); this log. Repositories were already implemented. `main.py`, `health.py`, `conftest.py`, `test_*.py` were already present on the branch.
- Task 03 needs `registry_repo.create` and `list_active_by_category`.
- Task 04 needs `documents_repo.create` and `update_processing_state`.
- Task 07 needs `verification_repo.create`, `get_latest_for_document`, and `registry_repo.list_active_by_category`.
- Task 09 needs `blockchain_repo.create`, `get_active_for_verification`, `mark_confirmed`, `mark_failed`.
- What I did **not** do: commit, push, PR, Task 03 seed, frontend, deleting `backend/data/app.db`.
