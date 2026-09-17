# PS21 — Blockchain-Based Document Verification System

## Purpose

A hackathon-scope, demonstrable application that accepts supported documents, extracts visible text
with OCR, compares selected fields against a clearly labeled synthetic reference registry, applies
explainable deterministic integrity checks, supports human review, and records a minimal
tamper-evident event on a local Ethereum-compatible blockchain.

> **This is a hackathon demonstration, not a government verification service.** It does not
> establish the authenticity of real identity, academic, or government documents. See
> `problem-statement-mapping.md` for exactly what is and isn't implemented, and why.

## Documentation map

| File | What it covers |
|---|---|
| `AGENTS.md` | **Read first.** The twelve hard rules, scope discipline, and approval gates for every contributor. Also lives at the repository root |
| `AI-CONTEXT.md` | Single-file consolidated context — read this second if you're an AI picking up a task cold |
| `project-context.md` | Problem, users, MVP scope, key limitations |
| `problem-statement-mapping.md` | Line-by-line mapping of the problem statement to what's built vs. deferred, and why |
| `requirements.md` | Functional/non-functional requirements, acceptance criteria |
| `architecture.md` | Components, dependency direction, trust boundaries, failure isolation |
| `workflow.md` | Narrative end-to-end walkthrough of all 10 stages, with do/don't per stage |
| `repo-structure.md` | The exact repository tree to scaffold before Task 01, with owning task per file |
| `backend.md` | Locked backend folder structure and module responsibilities |
| `frontend.md` | Locked frontend folder structure, pages, and component rules |
| `data-model.md` | All 6 database entities, relationships, retention |
| `category-schemas.md` | Exact field lists + synthetic registry fixtures for all 4 document categories |
| `api.md` | Full API contract — every endpoint's request/response schema |
| `api-manual-testing-guide.md` | curl walkthrough of the whole flow, for testing without the frontend |
| `document-processing.md` | Upload validation, preprocessing, PaddleOCR pipeline, failure states |
| `verification-rules.md` | Normalization, matching, deterministic rules, status precedence, review |
| `blockchain.md` | Contract design, event digest construction, chain states |
| `security-privacy.md` | Threat model, safeguards, resolved auth/retention decisions |
| `configuration.md` | Every environment variable, default, and validation rule |
| `setup.md` | Developer environment setup, step by step |
| `deployment-demo.md` | Local startup order and the rehearsed demo script |
| `testing.md` | Test layers, required scenarios, how to run the suites |
| `git-workflow.md` | Branching, commits, PRs, conflict handling |
| `decisions.md` | Full decision log, including previously-open items now resolved |
| `implementation-plan.md` | Task sequence, dependency graph, suggested team allocation |
| `glossary.md` | Shared vocabulary, and the words this project deliberately never uses |
| `troubleshooting.md` | Known failure modes during build and on demo day, with fixes |
| `judging-and-pitch.md` | Demo narrative, wording discipline, and answers to the hard questions |
| `development-log-template.md` | The `logs/task-NN-*.md` format every task keeps |

Tasks live in `../tasks/` — one work-order file per implementation task, indexed in
`../tasks/ALL-TASKS.md`.

## Current decisions (see `decisions.md` for the full log)

- Four demo categories, exact schemas frozen in `category-schemas.md`.
- PaddleOCR is the OCR engine; deterministic rules (not a trained ML model) do the reasoning —
  rationale in `problem-statement-mapping.md`.
- Registry entries are synthetic and visibly labeled as demo data.
- Local Hardhat chain + Solidity + Web3.py for the blockchain layer.
- No authentication system in the MVP — explicit, documented, not production-acceptable
  (`security-privacy.md`).
- No third-party paid API keys anywhere in the stack.

## Status vocabulary (say this exact wording in the UI and in demos)

`VERIFIED_MATCH` → "matched our synthetic demo reference," never "authentic" or "government
verified." See `verification-rules.md` and `deployment-demo.md` for the full presenter wording
table.
