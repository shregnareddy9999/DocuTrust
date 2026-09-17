# PS21 — Complete Project Context (Single-File)

> **Purpose:** Upload this one file to a fresh AI chat/assistant to give it full working context on
> PS21 without re-reading every doc. For actually implementing a task, still read the specific
> authoritative docs and task file listed in "Required reading" below — this file is a map and a
> summary, not a replacement for the detailed contracts.

---

## 1. What this is

PS21 is a hackathon MVP for the problem statement: *"Develop a Blockchain-based document
verification system that uses AI/ML and OCR to extract and validate information from uploaded
documents, cross-check records with authorized databases, detect forged or tampered documents, and
store verification records on a tamper-resistant blockchain ledger while ensuring data security and
privacy."*

It is **not** a government verification service. It uses a synthetic (fictional) reference registry,
deterministic rules instead of a trained ML fraud model, and a local development blockchain instead
of a production chain — every one of these simplifications is deliberate and documented in
`problem-statement-mapping.md`, precisely so nobody mistakes a demo shortcut for a misunderstanding
of the problem.

## 2. What it does (one paragraph)

Upload a PDF/image → validate + store it → PaddleOCR extracts text → map extracted text to one of 4
fixed category schemas (`category-schemas.md`) → compare required fields against a synthetic
registry entry → run deterministic consistency rules → assign one of 6 statuses
(`verification-rules.md`) → optional human review/correction, preserving original OCR → optional
minimal, non-identifying event recorded on a local Ethereum-compatible chain
(`blockchain.md`) → dashboard shows everything together (`frontend.md`).

## 3. Locked stack

Frontend: React + Vite + TypeScript. Backend: Python 3.11+, FastAPI, SQLAlchemy, SQLite. OCR:
PaddleOCR (CPU, English only for MVP). Blockchain: Solidity ^0.8.24 on a local Hardhat network,
Web3.py client. Tests: pytest + FastAPI TestClient (backend), vitest (frontend). No third-party
paid API keys anywhere.

## 4. The 4 MVP document categories

`academic_certificate`, `institutional_id`, `pan_like_demo`, `government_certificate`. Exact field
lists, required/optional flags, and one synthetic registry fixture per category are frozen in
`category-schemas.md` — never invent or guess a field name.

## 5. The 6 verification statuses (locked, never add/rename)

`PENDING`, `VERIFIED_MATCH`, `REVIEW_REQUIRED`, `NO_TRUSTED_RECORD`, `INTEGRITY_MISMATCH`,
`PROCESSING_FAILED`. Exact precedence order when multiple conditions apply is in
`verification-rules.md`. The 4 blockchain states (`NOT_REQUESTED`, `PENDING`, `CONFIRMED`, `FAILED`)
are always tracked independently of verification status.

## 6. Non-negotiable rules

- Never claim government/issuer verification. `VERIFIED_MATCH` means "matched our synthetic demo
  reference," always phrased that way in the UI.
- Never use real identity data or realistic-looking real identifiers in fixtures — everything is
  `DEMO-`-prefixed or an obviously fictional name.
- Never put a document, raw OCR text, or an identity field value on-chain — only the minimal event
  in `blockchain.md`.
- OCR confidence is not authenticity confidence; a first-time hash is not tamper detection; "no
  record" is not "forged."
- Never invent a field, status, endpoint, dependency, or configuration key not already in this
  documentation set — if something is missing, ask the project lead rather than guessing.
- Never add an ML model or LLM without an explicit project-lead decision (`decisions.md` D-06);
  never let a rule or model produce an unsupported numeric "fraud score."
- Preserve original OCR values when a human review corrects a field — corrections are additive, not
  overwrites (`data-model.md`).
- Never claim tests pass, or a feature works, without having actually run it in that session.

## 7. Repository layout (top level)

```
backend/    — FastAPI app; see backend.md for the full module tree
frontend/   — React app; see frontend.md for the full module tree
chain/      — Solidity contract + Hardhat project; see blockchain.md
docs/       — this documentation set
tasks/      — one work-order file per implementation task
```

## 8. API surface (summary — full schemas in `api.md`)

`GET /health`, `GET /document-types`, `POST /documents`, `GET /documents/{id}`,
`GET /documents/{id}/extraction`, `POST /documents/{id}/verify`, `GET /verifications/{id}`,
`POST /verifications/{id}/review`, `GET /verifications/{id}/blockchain`. All under `/api/v1`.
Standard error envelope: `{"error": {"code", "message", "details"}}`.

## 9. Required reading before implementing any task

0. `AGENTS.md` (repository root) — the twelve hard rules. Non-negotiable, read it first.
1. `docs/README.md` and this file.
2. `docs/project-context.md` and `docs/problem-statement-mapping.md`.
3. `docs/requirements.md` and `docs/architecture.md`.
4. `docs/workflow.md` for how your stage fits into the whole pipeline.
5. `docs/backend.md` or `docs/frontend.md` (whichever side the task touches).
6. The specific domain contract(s) the task touches: `api.md`, `data-model.md`,
   `category-schemas.md`, `document-processing.md`, `verification-rules.md`, `blockchain.md`,
   `security-privacy.md`, `configuration.md`.
7. The assigned file in `tasks/`, completely — including its Allowed Files and Acceptance Criteria.
8. The existing repository code, tests, `.env.example`, and `logs/task-NN-*.md` for that area.

## 10. Operating procedure for an AI coding assistant

**Before coding:** confirm the task's scope and acceptance criteria against its task file; identify
which files you're allowed to touch (`tasks/<NN>-*.md` §"Allowed files"); if a cited contract looks
incomplete or contradictory, stop and ask rather than filling the gap yourself.

**During coding:** make the smallest coherent change that satisfies the task; follow the folder
structure in `backend.md`/`frontend.md` exactly; add focused tests alongside the change; never touch
a file outside your task's allowed area without flagging it first; never silently change a status
name, API shape, DB column, or blockchain payload field — those are shared contracts.

**Before handoff:** run the task's required tests and report the exact command and result; run
`git diff`/`git status` and confirm no unrelated changes; list files changed, limitations, and
integration notes; do not say "done" if any acceptance-criteria checkbox is unmet.

**Never, without explicit human authorization in that session:** run `git commit`, `git push`,
merge/approve a PR, or mark a task's status as complete.

## 11. Where to find everything else

`README.md` has the full documentation map; `INDEX.md` lists every file in recommended reading
order. Beyond the contracts above, four supporting documents are worth knowing about:

- `workflow.md` — the whole pipeline as a narrative, stage by stage, with do/don't lists and the
  owning task for each stage. Read this if you want to understand how your piece fits.
- `glossary.md` — shared vocabulary, including the exact words this project never uses
  ("authentic", "forged", "fraud score") and what to say instead.
- `troubleshooting.md` — known failure modes with fixes. Check it before debugging from scratch.
- `judging-and-pitch.md` — for the project lead: demo narrative, wording discipline, and prepared
  answers to the hard questions this project attracts.

If this summary doesn't answer your question, the answer is in one of those or in a contract doc —
it is not something for you to decide.
