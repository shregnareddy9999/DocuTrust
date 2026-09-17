# PS21 Task Specification

> **This file is a work order for the assigned developer and their AI coding agent.**
>
> Do not expand the scope without explicit approval from the project lead.

---

## Task Information

**Task:** `Database and persistence model`
**Task ID:** `02` (`docs/implementation-plan.md` step 2)
**Assigned To:** `Unassigned` (suggested: Member C)
**Branch:** `feature/task-02-database`
**Priority:** `Critical` — Tasks 03, 04, 07, 08, 09, 10 all persist through this layer
**Status:** `Not Started`

---

# 1. Goal

## Objective

Implement all six SQLAlchemy models and their repositories exactly as specified in
`docs/data-model.md`, wire the engine/session lifecycle in `db.py`, and make `create_all()` run at
startup.

Expected outcome: every table exists with the documented columns, foreign keys, and enum
constraints; each repository exposes the query functions its consumers need; `GET /health` reports
`database: "ok"`.

## Why This Exists

Step 2 of `docs/implementation-plan.md`. `docs/data-model.md` is the contract. Six entities carry
the entire audit story of this project, and two properties matter more than everything else:

**History is append-only.** A re-verification writes a *new* `verification_results` row. A reviewer
correction adds a field entry rather than replacing one. A retried chain submission creates a new
`blockchain_records` row. If this layer allows destructive updates where the docs specify additive
ones, the audit trail the whole project is built on quietly stops being one.

**Column names are a cross-task contract.** Tasks 03 through 10 all reference these names literally
in their own task files.

---

# 2. Authoritative Documentation

* `AGENTS.md` — Rules 1, 6, 9, 10
* `docs/data-model.md` — **authoritative** (entire document): all six entities, every column,
  relationships, retention
* `docs/backend.md` — `models/`, `repositories/`, `db.py` layout; the repository layer contract
  ("SQLAlchemy queries only; no business rules")
* `docs/architecture.md` — dependency direction; repositories sit below services, above SQLite
* `docs/verification-rules.md` — the six status values that constrain `verification_results.status`
* `docs/blockchain.md` — the four values that constrain `blockchain_records.recording_status`
* `docs/category-schemas.md` — the four category values that constrain `documents.category`
* `docs/configuration.md` — `DATABASE_URL`, `RETENTION_DAYS`
* `docs/decisions.md` — D-08 (SQLite), D-12 (retention), D-18 (corrections create new rows)

---

# 3. Scope

## In Scope

* `backend/app/db.py` — engine, `SessionLocal`, `Base`, a `get_db()` dependency.
* `backend/app/models/` — six SQLAlchemy models matching `docs/data-model.md` field for field:
  `document.py`, `extraction.py`, `registry.py`, `verification.py`, `review.py`, `blockchain.py`.
* `backend/app/repositories/` — six repository modules with the query functions listed in §7.
* `create_all()` wired into `main.py`'s startup sequence (`docs/backend.md`).
* `GET /health` updated to report real database connectivity.
* `backend/tests/conftest.py` extended with a temp-SQLite session fixture.
* `backend/tests/test_models.py` and `test_repositories.py`.

## Out of Scope

* Seeding any data — **Task 03**.
* Any business rule: matching, status assignment, precedence — **Task 07**. Repositories return
  rows; they do not decide anything.
* Any API endpoint beyond the `/health` database field — Tasks 04, 10.
* A migration tool. `create_all()` is sufficient at MVP scale (`docs/backend.md`); during
  development, schema changes mean deleting `data/app.db` and re-seeding.
* Retention **enforcement** — the cleanup script is Task 12. This task only stores the timestamps
  that make it possible.

---

# 4. Allowed Files / Areas

```text
backend/app/db.py
backend/app/models/__init__.py
backend/app/models/{document,extraction,registry,verification,review,blockchain}.py
backend/app/repositories/{documents_repo,extraction_repo,registry_repo,verification_repo,review_repo,blockchain_repo}.py
backend/tests/test_models.py           (new)
backend/tests/test_repositories.py     (new)
```

### May Modify If Required

```text
backend/app/main.py       (startup: create_all + engine init only)
backend/app/api/health.py (database field only)
backend/tests/conftest.py (add the DB session fixture)
```

---

# 5. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Task 01 (skeleton, `Settings`, `main.py` startup hook) | **Hard** | `db.py` reads `DATABASE_URL` from `Settings` |
| `docs/data-model.md` | **Contract** | Frozen. Nothing to wait for |
| Task 03 (seeding) | **Downstream** | Consumes `registry_repo` |

### Dependency Status

* [x] Dependency exists and is ready (once Task 01 merges)
* [ ] Being developed separately
* [x] Requires coordination: `conftest.py` and `main.py` are shared with other tasks

### Parallel-development notes

This is the second-most-blocking task in the project. Prioritise merging it over polishing it.
Tasks 03 and 04 both queue behind it.

---

# 6. Contracts That Must Be Preserved

### Data model

* **Column names, types, and nullability exactly as `docs/data-model.md` specifies.** Not
  `doc_id` for `document_id`. Not `created` for `created_at`. Downstream tasks cite these literally.
* UUID string primary keys via `uuid4().hex` — not integers, not database-generated.
* Enum-constrained columns carry their documented value sets and nothing else:
  * `documents.category` — the four from `docs/category-schemas.md`
  * `documents.processing_state` — `UPLOADED`, `OCR_IN_PROGRESS`, `OCR_DONE`, `OCR_FAILED`
  * `extraction_results.status` — `SUCCEEDED`, `FAILED`
  * `verification_results.status` — the six from `docs/verification-rules.md`
  * `review_actions.action` — `ACCEPT`, `CORRECT`, `UNRESOLVED`
  * `blockchain_records.recording_status` — `NOT_REQUESTED`, `PENDING`, `CONFIRMED`, `FAILED`
* `verification_results.registry_record_id` is **nullable** — null is exactly the
  `NO_TRUSTED_RECORD` case, and a non-null constraint here would make that status unrepresentable.
* `verification_results.supersedes_verification_id` is a **nullable self-referencing FK** — null for
  a first verification, set when a `CORRECT` review produced this row (`data-model.md`,
  `decisions.md` D-23).
* **"Current" has exactly one definition:** the greatest `created_at` for that `document_id`,
  implemented once in `verification_repo.get_latest_for_document()`. No other module may compute it
  (`data-model.md` §"Which verification is current"). Divergent "latest result" logic across
  contributors is the specific failure this rule prevents.
* JSON is stored as text columns holding serialised JSON, with the documented internal shape.
* **No file bytes in any column.** Files live under `UPLOAD_DIR`; the database stores `storage_key`.

### Append-only history (`docs/decisions.md` D-18)

The repositories expose **no** function that mutates a `verification_results` row's `status`, a
`review_actions` row, or a completed `blockchain_records` row. Re-running verification creates a new
row. Retrying a submission creates a new row. If you find yourself writing `update_status()`, stop —
that function is not in the design, and adding it would silently disable the audit trail.

### Layering (`docs/architecture.md`)

Repositories contain SQLAlchemy queries only. No status logic, no normalization, no matching, no
"if there's no record then…". A repository returns rows or `None`; a service decides what that
means.

### Security

No `print()` or log line emits `raw_ocr_json`, `extracted_fields_json`, or `fields_json` content
(`docs/security-privacy.md`).

---

# 7. Implementation Requirements

### Requirement 1 — `db.py`

Engine from `Settings.DATABASE_URL`, `sessionmaker` → `SessionLocal`, declarative `Base`, and a
`get_db()` generator suitable as a FastAPI dependency that always closes its session. For SQLite,
pass `check_same_thread=False`.

### Requirement 2 — Models

One file per entity, matching `docs/data-model.md` field for field. Declare relationships explicitly
so `document.extractions`, `verification.review_actions`, and similar traversals work. Enum columns
use SQLAlchemy `Enum` (or a `String` with an explicit `CheckConstraint`) — not a bare `String` that
accepts anything.

### Requirement 3 — Repository functions

Minimum surface, all taking an explicit `Session`:

```text
documents_repo:    create, get_by_id, update_processing_state, list_recent
extraction_repo:   create, get_latest_for_document, get_latest_successful_for_document
registry_repo:     create, get_by_category_and_key, list_active_by_category, get_by_id
verification_repo: create, get_by_id, get_latest_for_document, list_for_document (newest first)
review_repo:       create, list_for_verification
blockchain_repo:   create, get_by_verification_id, get_active_for_verification, mark_confirmed, mark_failed
```

Two notes. `update_processing_state` is the one permitted state mutation — `documents` tracks
current pipeline position, not history. `mark_confirmed`/`mark_failed` transition a single
in-flight submission row from `PENDING`; they never resurrect a `FAILED` row, because a retry
creates a new row (`docs/blockchain.md`).

`get_active_for_verification` returns the newest non-`FAILED` row, which is how Task 09 prevents
duplicate submissions.

### Requirement 4 — Startup wiring

`main.py` creates the engine and calls `Base.metadata.create_all(bind=engine)` in the startup hook,
per `docs/backend.md`. Ensure the `data/` directory exists first.

### Requirement 5 — Health check

`GET /health` executes a trivial query (`SELECT 1`) and reports `"ok"` or `"error"`. It must not
report `"ok"` without actually touching the database, and must not leak the connection string.

### Requirement 6 — Test fixtures

`conftest.py` gains a session fixture backed by a temporary SQLite file, created and torn down per
test. Never the developer's real `data/app.db` (`docs/configuration.md`).

### Error Handling

* Duplicate `registry_records.synthetic_record_key` within a category → integrity error surfaced to
  the caller, not swallowed. Task 03 relies on this to keep seeding idempotent.
* Foreign key referencing a missing row → integrity error surfaced, not silently ignored.
* Malformed JSON in a JSON-text column → the repository returns raw text and lets the caller parse;
  it does not guess or repair.

---

# 8. Testing Requirements

## Automated Tests

`backend/tests/test_models.py`:
* All six tables are created by `create_all()` with the documented column names.
* Every enum column rejects an undocumented value.
* `verification_results.registry_record_id` accepts `NULL`.
* Relationship traversal works in both directions.
* A `documents` row cannot be created without its non-nullable columns.

`backend/tests/test_repositories.py`:
* Create and retrieve for each of the six repositories.
* `get_latest_for_document` returns the newest row when several exist — verify explicitly by
  creating two rows with different timestamps, since this ordering is what "current verification"
  means everywhere downstream.
* `get_latest_successful_for_document` skips `FAILED` extractions.
* `list_active_by_category` excludes `active = false` records.
* `get_active_for_verification` returns the newest non-`FAILED` blockchain row, and `None` when every
  row is `FAILED`.
* Duplicate `synthetic_record_key` in the same category raises.
* **No repository function mutates a `verification_results.status`** — assert by inspecting the
  module's public surface.

Run:

```bash
cd backend && pytest tests/test_models.py tests/test_repositories.py
```

## Manual Verification

1. Start the backend; confirm `data/app.db` appears.
2. `sqlite3 data/app.db ".schema"` → compare every column name against `docs/data-model.md`
   line by line. This five-minute check prevents the most expensive class of bug in this task.
3. `GET /api/v1/health` → `database: "ok"`.
4. Stop the app, delete `data/app.db`, restart → tables recreate cleanly.

---

# 9. Acceptance Criteria

* [ ] Six models exist, matching `docs/data-model.md` column for column.
* [ ] Every enum-constrained column rejects undocumented values.
* [ ] `verification_results.registry_record_id` is nullable.
* [ ] `verification_results.supersedes_verification_id` exists as a nullable self-referencing FK.
* [ ] `get_latest_for_document` is the single implementation of "current".
* [ ] No column stores file bytes.
* [ ] Six repositories expose at least the §7 function surface.
* [ ] No repository mutates verification status, a review action, or a completed blockchain record.
* [ ] Repositories contain no business logic.
* [ ] `create_all()` runs at startup; `data/` is created if absent.
* [ ] `GET /health` reports real database connectivity.
* [ ] `conftest.py` provides a temp-DB session fixture; no test touches the real database.
* [ ] Both test files pass.
* [ ] Manual `.schema` comparison done and recorded in the log.
* [ ] `git diff` reviewed; development log updated; branch pushed; PR prepared.

---

# 10. Known Risks

* **Silent column-name drift.** An assistant writing SQLAlchemy models from a table in prose will
  occasionally "improve" a name. This is the single most likely failure here and it is invisible
  until Task 07 cannot find a column. The `.schema` comparison in §8 exists specifically to catch it.
* **Adding an `update_status()` because it seems obviously useful.** It is not in the design. Its
  presence would let a later task quietly overwrite history (`docs/decisions.md` D-18).
* **SQLite enum enforcement is weaker than Postgres.** SQLAlchemy's `Enum` on SQLite may not produce
  a database-level constraint. If so, enforce at the application layer and note it in the log —
  do not silently accept unconstrained columns.
* **Session leakage in tests.** A fixture that doesn't dispose its engine leaves file handles open on
  Windows and produces confusing teardown errors.

---

# 11. Open Questions

* None. `docs/data-model.md` is complete and every enum's value set is fixed by another frozen
  contract. If you find something genuinely undefined, that is a documentation gap — report it to
  the project lead rather than choosing a default.

---

# 12. Handoff Notes

* Publish in the log: the exact repository function signatures. Tasks 03, 04, 07, 08, 09, and 10 all
  call them.
* Task 03 needs `registry_repo.create` and `list_active_by_category`.
* Task 04 needs `documents_repo.create` and `update_processing_state`.
* Task 07 needs `verification_repo.create` and `registry_repo.list_active_by_category`.
* Task 09 needs `blockchain_repo.create`, `get_active_for_verification`, `mark_confirmed`,
  `mark_failed`.
* State plainly in the log that there is no migration tool: schema changes mean deleting the local
  database. The team needs to know this before someone loses a day of demo state to it.

---

# 13. Definition of Done

```text
Implementation complete
        +
Tests passing
        +
Manual .schema comparison against docs/data-model.md complete
        +
Scope verified (no business logic in repositories)
        +
Git diff reviewed
        +
Development log updated
        +
No locked contracts violated
        +
Feature branch pushed
        ↓
PR ready
```

---

## Final Agent Instruction

Before making changes:

1. Read `AGENTS.md`.
2. Read `docs/data-model.md` **completely** — it is the whole specification for this task.
3. Read `docs/backend.md` §"Module responsibilities" for the repository-layer contract.
4. Read this task file completely.
5. State your plan, including every model class and every repository function, before coding.

During implementation:

* Copy column names character for character from `docs/data-model.md`. Do not improve them.
* Write no business logic in a repository. If a function needs an `if` about verification status,
  it belongs in a service, not here.
* Write no function that mutates history.
* Test incrementally.

If a column, type, or relationship seems wrong or missing, **stop and ask the project lead**.

Before PR:

* Run both test files and report exact output.
* Run `sqlite3 data/app.db ".schema"` and diff mentally against `docs/data-model.md`.
* Review `git diff` and `git status`.
* Update `logs/task-02-database.md` with the repository signatures.
* Push and open the PR per `docs/git-workflow.md`.
