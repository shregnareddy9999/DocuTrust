# Repository Structure

The exact tree to create **before Task 01 begins**. Eleven task files cite these paths literally, so
a renamed folder breaks them all at once.

Two ways to create it: run `scaffold.sh` (or `scaffold.py`) shipped alongside this documentation set,
or build it by hand from the tree below. The script is faster and cannot typo a path.

---

## Where the documentation goes

Copy the two folders you were given into the repository root and rename them:

```text
PS21_docs/   →  docs/
PS21_tasks/  →  tasks/
```

Then move `docs/AGENTS.md` to the repository root as well, keeping the copy in `docs/`. Most AI
coding assistants look for a root-level `AGENTS.md` automatically, which is the whole point of it
being there.

---

## The full tree

```text
ps21/
├── AGENTS.md                          # copy of docs/AGENTS.md — agents read this first
├── README.md                          # short project readme (points at docs/)
├── .gitignore
│
├── docs/                              # ← the 30 project documents
│   ├── AGENTS.md
│   ├── AI-CONTEXT.md
│   ├── INDEX.md
│   ├── README.md
│   ├── project-context.md
│   ├── problem-statement-mapping.md
│   ├── requirements.md
│   ├── architecture.md
│   ├── workflow.md
│   ├── repo-structure.md              # this file
│   ├── backend.md
│   ├── frontend.md
│   ├── data-model.md
│   ├── category-schemas.md
│   ├── api.md
│   ├── api-manual-testing-guide.md
│   ├── document-processing.md
│   ├── verification-rules.md
│   ├── blockchain.md
│   ├── security-privacy.md
│   ├── configuration.md
│   ├── setup.md
│   ├── testing.md
│   ├── deployment-demo.md
│   ├── troubleshooting.md
│   ├── git-workflow.md
│   ├── decisions.md
│   ├── implementation-plan.md
│   ├── glossary.md
│   ├── judging-and-pitch.md
│   ├── development-log-template.md
│   ├── ENVIRONMENT-REPORT.md          # created by Task 01
│   └── DEMO-CHECKLIST.md              # created by Task 12
│
├── tasks/                             # ← the 14 task work orders
│   ├── 00-HOW-TO-USE-TASKS.md
│   ├── ALL-TASKS.md
│   └── 01-foundation.md … 12-e2e-demo-handoff.md
│
├── logs/                              # one development log per task
│   ├── README.md                      # copy of docs/development-log-template.md
│   └── task-NN-<slug>.md              # created by each task owner as they start
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app, routers, startup hooks         [Task 01]
│   │   ├── config.py                  # Settings + fail-fast validation             [Task 01]
│   │   ├── db.py                      # engine, SessionLocal, Base, get_db          [Task 02]
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── health.py                                                            [Task 01]
│   │   │   ├── document_types.py                                                    [Task 06]
│   │   │   ├── documents.py                                                         [Task 04/06/10]
│   │   │   └── verifications.py                                                     [Task 07/08/09/10]
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── upload_service.py                                                    [Task 04]
│   │   │   ├── ocr_service.py                                                       [Task 05]
│   │   │   ├── extraction_service.py                                                [Task 06]
│   │   │   ├── verification_service.py                                              [Task 07]
│   │   │   ├── review_service.py                                                    [Task 08]
│   │   │   └── blockchain_service.py                                                [Task 09]
│   │   │
│   │   ├── domain/                    # pure — no FastAPI, SQLAlchemy, PaddleOCR, Web3
│   │   │   ├── __init__.py
│   │   │   ├── status.py                                                            [Task 07]
│   │   │   ├── normalization.py                                                     [Task 07]
│   │   │   ├── matching.py                                                          [Task 07]
│   │   │   ├── rules.py                                                             [Task 07]
│   │   │   └── schemas/
│   │   │       ├── __init__.py                                                      [Task 06]
│   │   │       ├── academic_certificate.py                                          [Task 06]
│   │   │       ├── institutional_id.py                                              [Task 06]
│   │   │       ├── pan_like_demo.py                                                 [Task 06]
│   │   │       └── government_certificate.py                                        [Task 06]
│   │   │
│   │   ├── adapters/                  # the ONLY place paddleocr / web3 are imported
│   │   │   ├── __init__.py
│   │   │   ├── ocr/
│   │   │   │   ├── __init__.py        # factory selecting by OCR_ENGINE             [Task 05]
│   │   │   │   ├── base.py            # OcrAdapter, OcrResult, OcrRegion            [Task 05]
│   │   │   │   ├── paddleocr_adapter.py                                             [Task 05]
│   │   │   │   └── fake_adapter.py                                                  [Task 05]
│   │   │   └── blockchain/
│   │   │       ├── __init__.py        # factory                                     [Task 09]
│   │   │       ├── base.py            # BlockchainAdapter, ReceiptResult            [Task 09]
│   │   │       ├── web3_adapter.py                                                  [Task 09]
│   │   │       └── fake_adapter.py                                                  [Task 09]
│   │   │
│   │   ├── repositories/              # SQLAlchemy queries only — no business rules
│   │   │   ├── __init__.py
│   │   │   ├── documents_repo.py                                                    [Task 02]
│   │   │   ├── extraction_repo.py                                                   [Task 02]
│   │   │   ├── registry_repo.py                                                     [Task 02]
│   │   │   ├── verification_repo.py                                                 [Task 02]
│   │   │   ├── review_repo.py                                                       [Task 02]
│   │   │   └── blockchain_repo.py                                                   [Task 02]
│   │   │
│   │   ├── models/                    # must match data-model.md field for field
│   │   │   ├── __init__.py
│   │   │   ├── document.py            # documents                                   [Task 02]
│   │   │   ├── extraction.py          # extraction_results                          [Task 02]
│   │   │   ├── registry.py            # registry_records                            [Task 02]
│   │   │   ├── verification.py        # verification_results                        [Task 02]
│   │   │   ├── review.py              # review_actions                              [Task 02]
│   │   │   └── blockchain.py          # blockchain_records                          [Task 02]
│   │   │
│   │   └── fixtures/
│   │       ├── __init__.py
│   │       ├── README.md              # what each sample demonstrates               [Task 03]
│   │       ├── seed_registry.py                                                     [Task 03]
│   │       ├── generate_samples.py                                                  [Task 03]
│   │       ├── cleanup_expired.py     # retention script                            [Task 12]
│   │       └── sample_documents/      # 11 generated files                          [Task 03]
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                # temp DB, fake adapters                      [Task 01/02/05]
│   │   ├── test_health.py                                                           [Task 01]
│   │   ├── test_config.py                                                           [Task 01]
│   │   ├── test_models.py                                                           [Task 02]
│   │   ├── test_repositories.py                                                     [Task 02]
│   │   ├── test_seed_registry.py                                                    [Task 03]
│   │   ├── test_upload.py                                                           [Task 04]
│   │   ├── test_ocr_pipeline.py                                                     [Task 05]
│   │   ├── test_extraction.py                                                       [Task 06]
│   │   ├── test_matching_rules.py                                                   [Task 07]
│   │   ├── test_review.py                                                           [Task 08]
│   │   ├── test_blockchain_adapter.py                                               [Task 09]
│   │   ├── test_api_documents.py                                                    [Task 10]
│   │   ├── test_api_verifications.py                                                [Task 10]
│   │   ├── test_e2e_pipeline.py                                                     [Task 10]
│   │   ├── test_e2e_scenarios.py                                                    [Task 12]
│   │   └── test_cleanup.py                                                          [Task 12]
│   │
│   ├── data/                          # SQLite + uploads — gitignored, created at runtime
│   │   └── uploads/
│   ├── requirements.txt                                                             [Task 01]
│   ├── pytest.ini                                                                   [Task 01]
│   └── .env.example                                                                 [Task 01]
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx                                                                 [Task 01]
│   │   ├── App.tsx                    # routes                                      [Task 11]
│   │   ├── api/
│   │   │   ├── client.ts                                                            [Task 11]
│   │   │   ├── documents.ts                                                         [Task 11]
│   │   │   ├── verifications.ts                                                     [Task 11]
│   │   │   └── documentTypes.ts                                                     [Task 11]
│   │   ├── pages/
│   │   │   ├── UploadPage.tsx                                                       [Task 11]
│   │   │   ├── DocumentDetailPage.tsx                                               [Task 11]
│   │   │   ├── VerificationResultPage.tsx                                           [Task 11]
│   │   │   ├── ReviewPage.tsx                                                       [Task 11]
│   │   │   ├── BlockchainReceiptPage.tsx                                            [Task 11]
│   │   │   └── DemoDashboardPage.tsx                                                [Task 11]
│   │   ├── components/
│   │   │   ├── StatusBadge.tsx        # the ONLY status→label mapping               [Task 11]
│   │   │   ├── FieldComparisonTable.tsx                                             [Task 11]
│   │   │   ├── SyntheticDataBanner.tsx                                              [Task 11]
│   │   │   ├── UploadDropzone.tsx                                                   [Task 11]
│   │   │   ├── LoadingState.tsx                                                     [Task 11]
│   │   │   ├── ErrorState.tsx                                                       [Task 11]
│   │   │   └── EmptyState.tsx                                                       [Task 11]
│   │   ├── state/
│   │   │   ├── useDocument.ts                                                       [Task 11]
│   │   │   └── useVerification.ts                                                   [Task 11]
│   │   ├── types/
│   │   │   └── api.ts                 # mirrors api.md exactly                      [Task 11]
│   │   └── mocks/                     # msw handlers, so Task 11 starts early       [Task 11]
│   │       └── handlers.ts
│   ├── package.json                                                                 [Task 01]
│   ├── vite.config.ts                                                               [Task 01]
│   ├── tsconfig.json                                                                [Task 01]
│   └── .env.example                   # VITE_API_BASE_URL                           [Task 01]
│
├── chain/
│   ├── contracts/
│   │   └── VerificationRegistry.sol                                                 [Task 09]
│   ├── scripts/
│   │   └── deploy.js                                                                [Task 09]
│   ├── test/
│   │   └── VerificationRegistry.test.js                                             [Task 09]
│   ├── hardhat.config.js                                                            [Task 09]
│   └── package.json                                                                 [Task 09]
│
└── demo/                              # rehearsal artifacts                         [Task 12]
    ├── recording/
    ├── screenshots/
    └── fixtures/                      # staged files for the live demo
```

---

## Notes on the scaffold

**Stub files carry a docstring, not an implementation.** A scaffolded Python module should contain
one line naming its owning task:

```python
"""Owned by Task 05 — PaddleOCR adapter. See tasks/05-ocr-adapter.md."""
```

Creating a stub is not permission to sketch the implementation — that is scope creep into someone
else's task (`tasks/01-foundation.md` §4).

**`__init__.py` matters.** Every Python package directory needs one, or imports fail in ways that
look like unrelated bugs.

**`data/` is created at runtime and gitignored.** Do not commit it, and do not commit `data/app.db`.

**`frontend/` is scaffolded by Vite, not by hand.** Run `npm create vite@latest frontend -- --template
react-ts` and then create the empty folders above inside `src/`. The script does this for you if Node
is present, and falls back to creating the tree if not.

---

## `.gitignore`

Write this **before** the first `git add`. A committed `.env` means generating a new
`CHAIN_EVENT_SALT` and rewriting history.

```gitignore
# Python
__pycache__/
*.py[cod]
venv/
.venv/
*.egg-info/

# Environment — never commit
.env
.env.local

# Runtime data
backend/data/
*.db
*.sqlite3

# Node
node_modules/
dist/
frontend/.vite/

# Hardhat
chain/artifacts/
chain/cache/
chain/node_modules/

# OS / editor
.DS_Store
Thumbs.db
.idea/
.vscode/
```

---

## After scaffolding

1. `git init`, commit the tree plus `docs/` and `tasks/` as the first commit.
2. Every teammate clones it.
3. Task 01 begins — it fills in `config.py`, `main.py`, `health.py`, the test baseline, the Vite
   scaffold, and `docs/ENVIRONMENT-REPORT.md`.
4. Nobody else starts until Task 01 merges (`tasks/ALL-TASKS.md`).
