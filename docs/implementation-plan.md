# Implementation Plan

12 tasks, detailed individually in `tasks/`. This file is the dependency map and coordination view;
`tasks/ALL-TASKS.md` is the quick-reference index.

## Before you start

Read `AGENTS.md`, then `AI-CONTEXT.md`, then `workflow.md` for the end-to-end picture.
`glossary.md` fixes the shared vocabulary, `troubleshooting.md` covers what goes wrong, and
`judging-and-pitch.md` is the project lead's guide to the demo. Every task keeps a log per
`development-log-template.md`.

**The exact folder tree to create before Task 01 begins is in `repo-structure.md`.** Scaffold it
first — Task 01 fills it in, and eleven task files cite those paths literally.

## Task sequence

1. **Repository/application foundation** — skeleton, config loading, health endpoint, lint/test
   baseline, `.gitignore`, environment compatibility check (Python/Node/PaddleOCR/Hardhat versions).
2. **Database and persistence model** — SQLAlchemy models + repositories for all 6 entities in
   `data-model.md`.
3. **Synthetic registry and seed fixtures** — `seed_registry.py`, sample documents per category
   (matching + mismatching), per `category-schemas.md`.
4. **Secure upload and file handling** — `POST /documents`, validation, storage.
5. **PaddleOCR adapter and preprocessing** — `ocr.py` pipeline, `paddleocr_adapter.py`,
   `fake_adapter.py`.
6. **Category-specific field extraction** — `extraction_service.py` + `domain/schemas/*`.
7. **Registry matching and deterministic rules** — `domain/matching.py`, `rules.py`, `status.py`.
8. **Integrity checks and human review** — `review_service.py`, `POST /verifications/{id}/review`.
9. **Solidity contract and local chain adapter** — `chain/`, `web3_adapter.py`, `fake_adapter.py`.
10. **Backend workflow/API integration** — wire services behind the full `api.md` surface end to end.
11. **Frontend upload, results, and review dashboard** — all pages/components in `frontend.md`.
12. **End-to-end tests, demo rehearsal, and handoff** — full `testing.md` "Required scenarios" pass,
    `deployment-demo.md` rehearsed at least once end to end.

## Dependency graph

```
1 → 2 → 3
1,2 → 4
1,4 → 5 → 6
2,3,6 → 7 → 8
1 → 9 (parallel; needs event-schema approval before merging, already resolved — see decisions.md D-13/D-17)
2..9 → 10
1, api.md → 11 (can start against the frozen api.md contract before 10 is fully done, using a mock server)
10,11 → 12
```

## Suggested 4-person allocation

| Member | Tasks |
|---|---|
| A | 5, 6 (OCR/extraction) |
| B | 7, 8 (rules/review) |
| C | 2, 3, 9 (data/registry/blockchain) |
| D | 1, 11 (foundation/frontend) |
| Project lead | Shared tasks 4, 10, 12; contract approval; demo rehearsal; unresolved decisions |

This is a starting suggestion, not an assignment — the project lead finalizes ownership in
`tasks/ALL-TASKS.md`.

## Parallel-work rules

Every schema referenced above (`api.md`, `data-model.md`, `category-schemas.md`,
`verification-rules.md`, `blockchain.md`) is already frozen by this documentation set — a
contributor/AI should not need to wait for another task to *define* a contract, only to
*implement* against one that's already written down. If an implementation reveals that a frozen
contract is wrong or incomplete, stop and flag it to the project lead rather than silently
diverging (`AI-CONTEXT.md`).

## MVP-critical vs. deferred

All 12 tasks above are MVP-critical — none are optional for a working end-to-end demo. Deferred
items (production auth, encryption at rest, ML add-ons, image forensics) are tracked in
`decisions.md` and `problem-statement-mapping.md`, not in this task list.
