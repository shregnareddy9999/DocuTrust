# PS21 Task Index

Twelve tasks. All twelve are MVP-critical — none are optional for a working end-to-end demo.

New here? Read [`00-HOW-TO-USE-TASKS.md`](00-HOW-TO-USE-TASKS.md) first.

---

## The tasks

*"Depends on" lists every task whose output this task's own file cites as a direct dependency —
including ones already guaranteed by an earlier entry in the same list (e.g. Task 05 needs Task 02
directly for `extraction_repo`, even though waiting on Task 04 would already imply Task 02 is done).
Listed for clarity, not because the build order changes. See each task's own §5 for exact reasons.*

| ID | Task | Depends on | Branch | Suggested owner | Status |
|---|---|---|---|---|---|
| [01](01-foundation.md) | Repository and application foundation | — | `feature/task-01-foundation` | Member D | Not started |
| [02](02-database-model.md) | Database and persistence model | 01 | `feature/task-02-database` | Member C | Not started |
| [03](03-synthetic-registry.md) | Synthetic registry and seed fixtures | 02 | `feature/task-03-registry` | Member C | Not started |
| [04](04-secure-upload.md) | Secure upload and file handling | 01, 02 | `feature/task-04-upload` | Lead | Not started |
| [05](05-ocr-adapter.md) | PaddleOCR adapter and preprocessing | 01, 02, 04 | `feature/task-05-ocr` | Member A | Not started |
| [06](06-field-extraction.md) | Category-specific field extraction | 02, 05 | `feature/task-06-extraction` | Member A | Not started |
| [07](07-registry-matching.md) | Registry matching and deterministic rules | 02, 03, 06 | `feature/task-07-rules` | Member B | Not started |
| [08](08-integrity-review.md) | Integrity checks and human review | 02, 06, 07 | `feature/task-08-review` | Member B | Not started |
| [09](09-blockchain.md) | Solidity contract and local chain adapter | 01 (contract + adapters) · 02 (persistence) | `feature/task-09-blockchain` | Member C | Not started |
| [10](10-backend-integration.md) | Backend workflow and API integration | 02–09 | `feature/task-10-integration` | Lead | Not started |
| [11](11-frontend.md) | Frontend upload, results, and review dashboard | 01 + frozen `api.md` | `feature/task-11-frontend` | Member D | Not started |
| [12](12-e2e-demo-handoff.md) | End-to-end tests, demo rehearsal, and handoff | 03, 10, 11 | `feature/task-12-e2e` | Lead | Not started |

The project lead owns this table. Contributors do not edit their own Status column.

---

## Dependency graph

```
01 ──┬─→ 02 ──→ 03 ──┐
     │      ↘        │
     ├─────→ 04 ──→ 05 ──→ 06 ──┴─→ 07 ──→ 08 ──┐
     │                                           ├─→ 10 ──┐
     ├─────→ 09 ────────────────────────────────┘         ├─→ 12
     │                                                     │
     └─────→ 11 (against frozen api.md, via mock server) ──┘
```

## What can run in parallel

Every contract this project needs is **already frozen in `docs/`**. Nobody waits for someone else
to *define* an interface — only to *implement* one. That is what makes the parallelism below real
rather than aspirational.

- **Task 09 splits across two dependency points, and the split is worth respecting precisely.**
  - *Needs only Task 01:* the whole `chain/` Hardhat project, `VerificationRegistry.sol`, the
    Solidity tests, `deploy.js`, the `BlockchainAdapter` interface, `web3_adapter.py`,
    `fake_adapter.py`, and the digest construction. That is the large majority of the task, and the
    event schema, digest formula, and `outcomeCode` enum are all already locked
    (`blockchain.md`, `decisions.md` D-13/D-17).
  - *Needs Task 02:* only `blockchain_service.py`'s persistence — it writes through
    `blockchain_repo`. Build the digest and submission logic as pure functions first and wire
    persistence last.
  So Task 09 starts immediately after Task 01 and stalls only at the final step if Task 02 has not
  landed by then. In practice Task 02 will be done well before that point.
- **Task 11 starts immediately after Task 01.** `api.md` is frozen, so the frontend builds against a
  mock server (`msw` or a static JSON server) long before Task 10 exists.
- **Tasks 05/06 (Member A) and 07/08 (Member B) run concurrently** once 02–04 land. They touch
  disjoint files: Member A owns `adapters/ocr/` and `services/ocr_service.py` +
  `extraction_service.py`; Member B owns `domain/matching.py`, `rules.py`, `status.py`, and
  `services/review_service.py`.
- **Task 03 overlaps Task 04.** Different files entirely.

## The real critical path

```
01 → 02 → 04 → 05 → 06 → 07 → 10 → 12
```

Eight tasks. Anything that slips here slips the demo. Tasks 03, 09, and 11 have slack — if someone
finishes early, move them onto the critical path rather than polishing.

## Coordination points that have historically caused trouble

| When | Who must talk | About |
|---|---|---|
| Task 05 → 06 | Member A with themselves | The `OcrResult` shape. Publish it in the log the day it stabilises |
| Task 06 → 07 | Member A → Member B | The extracted-fields dict shape. Member B builds matching directly against it |
| Task 04 → 10 | Lead with themselves | Who owns the `documents` router. Task 04 owns a minimal version; Task 10 completes it |
| Task 09 → 10 | Member C → Lead | Contract address handling and the `BlockchainAdapter` interface |
| Task 11 → 10 | Member D → Lead | Any place the real backend's response differs from `api.md`. Flag it, never silently adapt the frontend |

## Suggested allocation

| Member | Tasks | Theme |
|---|---|---|
| A | 05, 06 | OCR and extraction |
| B | 07, 08 | Rules and review |
| C | 02, 03, 09 | Data, registry, blockchain |
| D | 01, 11 | Foundation and frontend |
| Lead | 04, 10, 12 | Shared surfaces, integration, demo |

A starting suggestion, not an assignment. The lead finalises ownership in the table above.

See [`../docs/implementation-plan.md`](../docs/implementation-plan.md) for the full rationale.
