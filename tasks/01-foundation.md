# PS21 Task Specification

> **This file is a work order for the assigned developer and their AI coding agent.**
>
> This task defines the scope of the assigned work. Do not expand the scope without explicit
> approval from the project lead.

---

## Task Information

**Task:** `Repository and application foundation`
**Task ID:** `01` (`docs/implementation-plan.md` step 1; index: `tasks/ALL-TASKS.md`)
**Assigned To:** `Unassigned` (suggested: Member D)
**Branch:** `feature/task-01-foundation`
**Priority:** `Critical` — every other task is blocked on this
**Status:** `Not Started`

---

# 1. Goal

## Objective

Create the repository skeleton exactly as specified in `docs/backend.md` and `docs/frontend.md`,
implement configuration loading with fail-fast validation, expose `GET /health`, establish the test
baseline, and — critically — **produce a written environment compatibility report** for PaddleOCR,
PaddlePaddle, Node.js, and Hardhat across every team machine.

Expected outcome: any teammate can clone, follow `docs/setup.md`, run the backend, hit `/health`,
run `pytest`, and start the frontend dev server. And the team knows, in writing, which package
versions actually work on which machines.

## Why This Exists

Step 1 of `docs/implementation-plan.md`. Two things make this more than boilerplate:

**The folder structure is a locked contract.** `docs/backend.md` and `docs/frontend.md` specify
exact paths. Every subsequent task's Allowed Files section references those paths. If this task
creates `backend/app/api/routes/documents.py` instead of `backend/app/api/documents.py`, eleven
downstream task files become wrong simultaneously.

**The environment check is the highest-risk item in the project.** PaddlePaddle wheel availability
varies sharply by Python version and platform (`docs/decisions.md` D-02). Discovering on day three
that one teammate's machine cannot install it is recoverable. Discovering it the night before the
demo is not.

---

# 2. Authoritative Documentation

* `AGENTS.md` — all twelve rules, especially Rules 1 (never invent a contract) and 12 (never claim untested work)
* `docs/backend.md` — **authoritative** — exact backend folder layout, startup sequence, error-handling convention
* `docs/frontend.md` — **authoritative** — exact frontend folder layout
* `docs/configuration.md` — **authoritative** — every environment variable, defaults, validation rules
* `docs/api.md` — `GET /health` response shape; base path `/api/v1`; error envelope
* `docs/setup.md` — the setup steps this task must make true
* `docs/testing.md` — test layout and the `integration` marker convention
* `docs/git-workflow.md` — branch naming, `.gitignore` requirements
* `docs/decisions.md` — D-02 (PaddleOCR), D-05 (Hardhat), D-07 (internet available at setup)

---

# 3. Scope

## In Scope

* Full directory skeleton per `docs/backend.md`, with `__init__.py` where Python packages require it.
  Empty modules may be stubs, but the **paths must be exact**.
* Full directory skeleton per `docs/frontend.md` — Vite + React + TypeScript initialised, dev server
  runs, `VITE_API_BASE_URL` read from env.
* `backend/app/config.py` — a typed `Settings` object loading every variable in
  `docs/configuration.md`, with every documented validation rule, failing fast at startup with a
  message that names the offending variable.
* `backend/app/main.py` — FastAPI app, `/api/v1` router registration, the single global exception
  handler producing the `docs/api.md` error envelope, startup hooks.
* `backend/app/api/health.py` — `GET /health` per `docs/api.md`.
* `backend/.env.example` — every variable from `docs/configuration.md`, safe defaults/placeholders.
* `frontend/.env.example` — `VITE_API_BASE_URL`.
* `backend/requirements.txt` — foundation dependencies only (FastAPI, Uvicorn, SQLAlchemy,
  pydantic-settings, pytest, httpx). **Not** `paddleocr` or `web3` — those belong to Tasks 05 and 09.
* `backend/pytest.ini` — including the `integration` marker registration.
* `backend/tests/conftest.py` — the shared fixture skeleton (temp DB URL, temp upload dir, test
  settings override). Adapter fakes are added by their owning tasks.
* `backend/tests/test_health.py`, `test_config.py`.
* `.gitignore` covering `.env`, `data/`, `__pycache__/`, `node_modules/`, `*.db`, `chain/artifacts/`,
  `chain/cache/`.
* `logs/` directory with `docs/development-log-template.md` copied to `logs/README.md`.
* `AGENTS.md` copied to the repository root.
* **`docs/ENVIRONMENT-REPORT.md`** — a new file recording, per team machine: OS, Python version,
  Node version, whether `paddlepaddle` + `paddleocr` installed, whether Hardhat ran, and the exact
  working version strings.

## Out of Scope

* Any SQLAlchemy model or table — **Task 02**.
* Any endpoint other than `/health` — Tasks 04, 10.
* Installing or pinning `paddleocr` / `web3` in `requirements.txt` — Tasks 05, 09. This task
  *tests* installability and reports it; it does not add the dependency.
* The Hardhat project itself — **Task 09**. This task only verifies Hardhat runs.
* Any frontend page or component — **Task 11**. Only the scaffold.
* CI configuration — not in MVP scope.

---

# 4. Allowed Files / Areas

```text
AGENTS.md                              (copy from docs/)
.gitignore
backend/app/main.py
backend/app/config.py
backend/app/api/health.py
backend/app/api/__init__.py            (and __init__.py across app/ packages)
backend/requirements.txt
backend/pytest.ini
backend/.env.example
backend/tests/conftest.py
backend/tests/test_health.py
backend/tests/test_config.py
frontend/                              (Vite scaffold: package.json, vite.config.ts, tsconfig,
                                        src/main.tsx, src/App.tsx, .env.example)
logs/README.md
docs/ENVIRONMENT-REPORT.md             (new)
```

### May Create As Empty Stubs (paths must be exact, contents may be placeholder)

```text
backend/app/db.py
backend/app/api/{document_types,documents,verifications}.py
backend/app/services/*.py
backend/app/domain/**/*.py
backend/app/adapters/**/*.py
backend/app/repositories/*.py
backend/app/models/*.py
backend/app/fixtures/
```

Creating a stub means an empty file or a module docstring naming its owning task. It does **not**
mean writing a partial implementation — that is scope creep into someone else's task.

---

# 5. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| None (this is the root task) | — | Every other task depends on this one |
| Python 3.11+ on every dev machine | **Hard (environment)** | `docs/decisions.md` D-02; 3.11 is the safe target for PaddlePaddle wheels |
| Node.js LTS on every dev machine | **Hard (environment)** | Needed by Vite and, in Task 09, Hardhat |
| Internet access during setup | **Assumed** | `docs/decisions.md` D-07 |

### Dependency Status

* [x] No upstream task dependencies
* [x] External dependency: Python and Node toolchains on each machine
* [x] Requires coordination: every teammate must run the environment check on their own machine

### Parallel-development notes

Nothing else starts until the skeleton is merged. Get this done fast and merge it — a perfect
foundation delivered on day three is worse than a correct one delivered on day one. Meanwhile, ask
every teammate to run the environment check on their own machine in parallel and send you results;
you aggregate them into `ENVIRONMENT-REPORT.md`.

---

# 6. Contracts That Must Be Preserved

### Folder structure

**Exact paths from `docs/backend.md` and `docs/frontend.md`.** No renaming, no "cleaner"
reorganisation, no extra nesting layer. Eleven downstream task files cite these paths literally.
If you believe a path is wrong, that is a project-lead conversation and a documentation change — not
a local improvement.

### Configuration

* Every variable in `docs/configuration.md` appears in `.env.example` with the documented default.
* Every documented validation rule is enforced in `config.py`: `MAX_UPLOAD_MB > 0`,
  `MAX_PDF_PAGES > 0`, `ALLOWED_MIME_TYPES` non-empty, `LOW_CONFIDENCE_THRESHOLD` in `(0, 1)`, and
  — when `BLOCKCHAIN_ENABLED=true` — `BLOCKCHAIN_RPC_URL`, `BLOCKCHAIN_CONTRACT_ADDRESS`, and
  `CHAIN_EVENT_SALT` all non-empty.
* **Fail fast.** Invalid configuration stops startup with a clear message naming the variable. It
  must never silently flip `BLOCKCHAIN_ENABLED` to `false` to get the app running — that would let a
  demo run without the chain layer while appearing healthy.
* No variable is read from the environment anywhere except through `Settings`.

### API

* Base path `/api/v1` (`docs/api.md`). This is fixed; there is no alternative and no decision open.
* `GET /health` returns exactly
  `{"status", "database", "ocr_adapter", "blockchain"}` and leaks no secret, connection string, or
  filesystem path.
* One global exception handler in `main.py` produces the `docs/api.md` error envelope. Route
  handlers do not format errors themselves.

### Security

* `.env` is in `.gitignore` before the first commit. A committed `CHAIN_EVENT_SALT` means generating
  a new one and rewriting history.
* `data/` and `*.db` are ignored.

---

# 7. Implementation Requirements

### Requirement 1 — Backend skeleton

Create every path in `docs/backend.md`. Python packages get `__init__.py`. Stub modules carry a
one-line docstring naming their owning task, e.g. `"""Owned by Task 05 — PaddleOCR adapter."""`.

### Requirement 2 — Configuration with fail-fast validation

`config.py` exposes a single `Settings` instance (pydantic-settings or equivalent). Types are real
types — `MAX_UPLOAD_MB` is an `int`, `ALLOWED_MIME_TYPES` is a `list[str]`, `BLOCKCHAIN_ENABLED` is a
`bool`. Validation runs at import/startup, and failure raises with a message that names the variable
and states what was wrong.

### Requirement 3 — Application entry point

`main.py`: create the FastAPI app, load and validate `Settings`, register the global exception
handler, register routers under `/api/v1`, and expose `/health`. Startup ordering follows
`docs/backend.md` §"Startup sequence". Database engine creation and `create_all()` are stubbed with
a TODO naming Task 02 — do not implement them here.

### Requirement 4 — Health endpoint

Report `database` as `"not_configured"` until Task 02 lands (do not fake `"ok"`), `ocr_adapter` from
the `OCR_ENGINE` setting, `blockchain` as `"enabled"`/`"disabled"` from `BLOCKCHAIN_ENABLED`.

### Requirement 5 — Test baseline

`pytest.ini` registers the `integration` marker and excludes it from the default run.
`conftest.py` provides a settings-override fixture pointing at a temp directory — tests never read
the developer's real `.env` (`docs/configuration.md`).

### Requirement 6 — Frontend scaffold

`npm create vite@latest` with the React + TypeScript template, the folder skeleton from
`docs/frontend.md` created (empty component files are fine), `.env.example` with
`VITE_API_BASE_URL`, and `npm run dev` serving a page.

### Requirement 7 — Environment compatibility report

On **each** team machine, record and then attempt:

```bash
python --version
node --version
pip install paddlepaddle
pip install paddleocr
python -c "import paddleocr; print(paddleocr.__version__)"
npx hardhat --version
```

**A version that installs is not a version that works.** Run these smoke tests too, on each machine,
and record pass/fail with the exact error text for any failure:

```bash
# OCR actually runs and returns text on a real image
python -c "from paddleocr import PaddleOCR; o=PaddleOCR(lang='en'); print(o.ocr('sample.png'))"

# Hardhat actually starts a node and deploys
cd chain && npx hardhat node &          # must stay up
npx hardhat compile

# Vite actually builds, not just starts
cd frontend && npm run build
```

Windows-specific checks, because these are where this stack breaks and where a "it installed fine"
report is misleading:

- PaddlePaddle wheel present for the installed Python **and** `import paddleocr` succeeds without a
  DLL-load error.
- The first-run model weight download completed — run OCR twice and confirm the second run does not
  re-download.
- A **thread-based** timeout works. Signal-based timeouts do not work on Windows, and Task 05 depends
  on this (`tasks/05-ocr-adapter.md` §10).
- Long-path support: confirm the repository path plus `node_modules` nesting does not exceed the
  path limit.
- `npx hardhat node` runs from a plain terminal and stays up.

Write results to `docs/ENVIRONMENT-REPORT.md` in this shape:

```markdown
| Machine | OS | Python | Node | paddlepaddle | paddleocr | OCR smoke | Hardhat | compile | vite build | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| Lead's laptop | Windows 11 | 3.11.9 | 20.11.0 | 2.6.1 ✅ | 2.7.3 ✅ | ✅ | 2.22.5 ✅ | ✅ | ✅ | demo machine |
| Member A | macOS 14 | 3.11.8 | 20.11.0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
```

Then add a **Pinned versions** section stating the exact version strings the team commits to, and
write those same versions into `requirements.txt` and `package.json` as exact pins — not `>=`, not
`^`. `decisions.md` D-02, D-05, and D-09 are **provisional until this report exists** (D-24); report
back to the project lead so they can be marked plain "Accepted".

Finally, name the **demo machine** explicitly in the report. It must be one where the OCR smoke test
and the Hardhat checks both pass. Discovering on demo day that the presenting laptop was never the
one that ran real OCR is a preventable disaster, and this line is the prevention.

Record failures with the **exact error text**, not "didn't work". Then state a recommendation:
the version set the team pins, and which machines (if any) must work against `fake_adapter.py` only.

### Error Handling

* Missing required env var → startup fails, message names the variable.
* Invalid type or range → startup fails, message states expected versus received.
* Unhandled exception in any route → global handler returns `500 INTERNAL_ERROR` with a
  `correlation_id` in `details` and **no** stack trace, file path, or raw exception text in
  `message`.

---

# 8. Testing Requirements

`pytest` from `backend/`.

## Automated Tests

`backend/tests/test_health.py`:
* `GET /api/v1/health` → `200` with all four documented keys.
* Response contains no value resembling a filesystem path, connection string, or secret.

`backend/tests/test_config.py`:
* Valid environment → `Settings` loads, types are correct.
* `MAX_UPLOAD_MB=0` → raises.
* `LOW_CONFIDENCE_THRESHOLD=1.5` → raises.
* `BLOCKCHAIN_ENABLED=true` with empty `BLOCKCHAIN_CONTRACT_ADDRESS` → raises.
* `BLOCKCHAIN_ENABLED=true` with empty `CHAIN_EVENT_SALT` → raises.
* `BLOCKCHAIN_ENABLED=false` with both empty → loads successfully.
* Every key in `.env.example` has a corresponding field on `Settings` — this test catches drift
  between the file and the class, which otherwise goes unnoticed until someone's app won't start.

Run:

```bash
cd backend && pytest
```

Expected:

```text
test_health.py ..    PASSED
test_config.py ....... PASSED
```

## Manual Verification

1. Fresh clone → follow `docs/setup.md` verbatim → backend starts, `/api/v1/health` returns 200.
2. Delete a required line from `.env` → backend refuses to start, message names the variable.
3. `cd frontend && npm run dev` → page loads.
4. `git status` on a fresh clone after a full run → no `.env`, no `data/`, no `node_modules`.

---

# 9. Acceptance Criteria

* [ ] Every path in `docs/backend.md` exists, spelled exactly as documented.
* [ ] Every path in `docs/frontend.md` exists, spelled exactly as documented.
* [ ] `config.py` loads all `docs/configuration.md` variables with correct types.
* [ ] Every documented validation rule is enforced and fails fast with a variable-naming message.
* [ ] The app never silently disables blockchain to work around bad configuration.
* [ ] `GET /api/v1/health` matches `docs/api.md` and leaks nothing sensitive.
* [ ] The global exception handler produces the `docs/api.md` error envelope; no route formats
      errors locally.
* [ ] `.env.example` and `frontend/.env.example` are complete.
* [ ] `.gitignore` covers `.env`, `data/`, `*.db`, `__pycache__/`, `node_modules/`, `chain/artifacts/`,
      `chain/cache/`.
* [ ] `pytest.ini` registers `integration` and excludes it by default.
* [ ] `pytest` passes.
* [ ] `npm run dev` serves the frontend.
* [ ] `AGENTS.md` is at the repository root.
* [ ] `logs/` exists with the template.
* [ ] **`docs/ENVIRONMENT-REPORT.md` is filled in for every team machine**, including the smoke-test
      columns — installs alone are not sufficient evidence.
* [ ] Exact version pins recorded and written into `requirements.txt` and `package.json` (no `>=`, no `^`).
* [ ] The Windows-specific checks were run on every Windows machine, thread-based timeout included.
* [ ] The demo machine is named in the report and passes every smoke test.
* [ ] D-02, D-05, D-09 reported back to the project lead for promotion from provisional (D-24).
* [ ] `git diff` reviewed; development log updated; branch pushed; PR prepared.

---

# 10. Known Risks

* **PaddlePaddle is the project's biggest environment risk.** Wheel availability lags new Python
  releases. Python 3.11 is the safe target. If a machine cannot install it, that teammate works
  against `fake_adapter.py` — which the architecture supports by design (`AGENTS.md` Rule 11) — but
  the *team* needs at least one machine that runs real PaddleOCR, and it must be the demo machine.
* **Stub files drifting into implementations.** The temptation to "just sketch" `ocr_service.py`
  while creating it is strong and it is scope creep. Docstring only.
* **Structure drift.** An assistant scaffolding a FastAPI project from habit will produce
  `app/routers/` or `app/api/v1/endpoints/`. Both are conventional. Both are wrong here. Check every
  path against `docs/backend.md` before committing.
* **`.env` committed on the first push.** Write `.gitignore` before the first `git add`.

---

# 11. Open Questions

* **Resolved by this task:** the exact pinned versions of `paddlepaddle`, `paddleocr`, Node, and
  Hardhat. `docs/decisions.md` D-02 and D-05 are "Accepted — verify environment"; this task performs
  that verification. Report findings to the project lead, who updates the decision log status to
  plain "Accepted" with the pinned versions recorded.
* If no team machine can run PaddleOCR, stop and escalate immediately. That is a stack decision
  (`docs/decisions.md` D-02), not something to work around locally.

---

# 12. Handoff Notes

* Publish in the log: pinned Python/Node versions, the `Settings` field names, and confirmation that
  the structure matches `docs/backend.md` exactly.
* Task 02 needs `db.py` stubbed and `main.py`'s startup hook ready for `create_all()`.
* Tasks 05 and 09 need the environment report before they pin their dependencies.
* Task 11 needs the frontend scaffold and `VITE_API_BASE_URL` wired.
* Tell the team the moment this merges — everyone is blocked until then.

---

# 13. Definition of Done

```text
Implementation complete
        +
Tests passing
        +
Manual verification complete
        +
Environment report filled in for every machine
        +
Scope verified (no stub became an implementation)
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
2. Read `docs/AI-CONTEXT.md`.
3. Read `docs/backend.md`, `docs/frontend.md`, and `docs/configuration.md` completely — the folder
   structure and variable list are contracts, not suggestions.
4. Read this task file completely.
5. State your plan, including the full list of files you will create, before writing any code.

During implementation:

* Create every documented path exactly as written. Do not restructure.
* Stub files get a docstring, not an implementation.
* Do not add `paddleocr` or `web3` to `requirements.txt` — test installability, report it, move on.
* Test incrementally.

If you discover that the documented structure is wrong or a required variable is missing, **stop and
ask the project lead**. Do not resolve it yourself — every downstream task file cites these paths.

Before PR:

* Run `pytest` and report the exact output.
* Confirm `docs/ENVIRONMENT-REPORT.md` is complete.
* Review `git diff` and `git status`; confirm no `.env` and no unrelated changes.
* Update `logs/task-01-foundation.md`.
* Push the branch and open the PR per `docs/git-workflow.md`.
