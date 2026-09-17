# PS21 Task Specification

> **This file is a work order for the assigned developer and their AI coding agent.**
>
> Do not expand the scope without explicit approval from the project lead.

---

## Task Information

**Task:** `Solidity contract and local chain adapter`
**Task ID:** `09` (`docs/implementation-plan.md` step 9)
**Assigned To:** `Unassigned` (suggested: Member C)
**Branch:** `feature/task-09-blockchain`
**Priority:** `High` — the problem statement names blockchain explicitly; can start right after Task 01
**Status:** `Not Started`

---

# 1. Goal

## Objective

Implement the Hardhat project, `VerificationRegistry.sol` exactly as `docs/blockchain.md` specifies,
the `BlockchainAdapter` interface with a Web3.py implementation and a fake, and the digest
construction — with retries, receipt verification, and duplicate prevention.

Expected outcome: a terminal verification submits one transaction carrying three non-identifying
values; the receipt is verified before `CONFIRMED` is shown; a stopped chain node produces `FAILED`
and changes no verification status.

## Why This Exists

Step 9 of `docs/implementation-plan.md`. The problem statement requires a tamper-resistant ledger,
and this provides it honestly: an append-only record of **what our application concluded, and when**.

Two properties define the task.

**Privacy by construction.** No document, no OCR text, no field value, no name reaches the chain —
not because a policy forbids it, but because the payload has no field capable of carrying it
(`AGENTS.md` Rule 6). A chain is permanent and public by nature; a privacy mistake here cannot be
undone with a database delete.

**Failure isolation.** The chain is an external process that will go down, and when it does, nothing
about the verification result may change. Being able to kill the node mid-demo and have verification
carry on is both correct engineering and one of the strongest things you can show a judge
(`docs/judging-and-pitch.md` §3).

---

# 2. Authoritative Documentation

* `AGENTS.md` — Rules 2, 3, 6, 10, 11
* `docs/blockchain.md` — **authoritative** (entire document): contract shape, `outcomeCode` enum,
  digest construction, chain states, operational notes
* `docs/data-model.md` — `blockchain_records` columns
* `docs/configuration.md` — all `BLOCKCHAIN_*` variables and `CHAIN_EVENT_SALT`
* `docs/api.md` — `GET /verifications/{id}/blockchain`
* `docs/security-privacy.md` — nothing personal on-chain; secret handling
* `docs/decisions.md` — D-05 (Hardhat/Solidity/Web3.py), D-13 (digest), D-17 (`outcomeCode`)
* `docs/deployment-demo.md` — the deploy sequence
* `docs/ENVIRONMENT-REPORT.md` — confirmed Node and Hardhat versions
* `docs/workflow.md` Stage 8

---

# 3. Scope

## In Scope

* `chain/` — Hardhat project: `hardhat.config.js`, `package.json`, `contracts/VerificationRegistry.sol`,
  `scripts/deploy.js`, `test/VerificationRegistry.test.js`.
* `backend/app/adapters/blockchain/base.py` — the `BlockchainAdapter` interface.
* `backend/app/adapters/blockchain/web3_adapter.py` — Web3.py implementation with retries and
  receipt verification.
* `backend/app/adapters/blockchain/fake_adapter.py` — deterministic canned responses, including RPC
  failure and timeout modes.
* `backend/app/services/blockchain_service.py` — digest construction, duplicate prevention,
  `blockchain_records` persistence.
* `GET /verifications/{verification_id}/blockchain` per `docs/api.md`.
* `backend/tests/test_blockchain_adapter.py`.
* `web3` added to `requirements.txt`.

## Out of Scope

* Deciding **when** submission happens in the overall flow — **Task 10**. This task exposes
  `submit_verification(verification_id)`; Task 10 calls it.
* Any change to verification logic — **Task 07**. The chain never influences a verification status.
* Public testnet or mainnet deployment — `docs/decisions.md` D-05, local Hardhat only.
* Storing documents, hashes of documents, or any field value on-chain.
* Wallet management, gas optimisation, or a token. None of these are in scope.
* An on-chain read/query UI — `GET .../blockchain` reads from the database.
* Frontend rendering of `error_code` — that is Task 11; this task only ensures the field is
  populated correctly and returned by the endpoint.

---

# 4. Allowed Files / Areas

```text
chain/hardhat.config.js
chain/package.json
chain/contracts/VerificationRegistry.sol
chain/scripts/deploy.js
chain/test/VerificationRegistry.test.js
backend/app/adapters/blockchain/base.py
backend/app/adapters/blockchain/web3_adapter.py
backend/app/adapters/blockchain/fake_adapter.py
backend/app/adapters/blockchain/__init__.py     (factory)
backend/app/services/blockchain_service.py
backend/app/api/verifications.py                (add the blockchain endpoint only)
backend/requirements.txt                         (add web3)
backend/tests/test_blockchain_adapter.py         (new)
```

---

# 5. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| Task 01 (`Settings`, skeleton) | **Hard** | All `BLOCKCHAIN_*` config |
| Task 02 (`blockchain_repo`) | **Hard, but only for the last step** | Needed solely by `blockchain_service.py`'s persistence. The contract, Solidity tests, adapters, and digest construction need nothing from Task 02 |
| Node.js + Hardhat | **Hard (environment)** | Versions from `docs/ENVIRONMENT-REPORT.md` |
| Task 07 (`verification_id`, `outcome_code`) | **Soft** | Both can be stubbed — see below |

### Dependency Status

* [x] Dependency exists and is ready (Task 01; Task 02 needed only for the final persistence step)
* [x] External dependency: Node.js and Hardhat provisioned
* [x] Requires coordination: Task 10 wires submission into the flow

### Parallel-development notes

**This task starts immediately after Task 01** and is the best parallelism opportunity in the
project. Build in this order, so the Task 02 dependency bites as late as possible: `chain/` project
and contract → Solidity tests → `base.py` → `fake_adapter.py` → `web3_adapter.py` → digest
construction as a pure function → **then** `blockchain_service.py` persistence, which is the only
part that touches `blockchain_repo`. Everything before that last step needs Task 01 only. The event schema, digest formula, and `outcomeCode` enum are all frozen
(`docs/decisions.md` D-13, D-17), so nothing here waits on the verification pipeline. Build against
a stub `verification_id` and a hardcoded `outcome_code` and finish the whole thing before Task 07
exists.

---

# 6. Contracts That Must Be Preserved

### The contract (`docs/blockchain.md`)

Exactly as documented — one event, one function, three arguments:

```solidity
event VerificationRecorded(
    bytes32 indexed verificationRef,
    bytes32 eventDigest,
    uint8 outcomeCode,
    uint256 recordedAt
);

function recordVerification(bytes32 verificationRef, bytes32 eventDigest, uint8 outcomeCode) external;
```

* **Append-only.** No update function, no delete function, no owner, no pause, no upgrade mechanism.
  If you add one "for completeness", you have broken the only property that makes this a tamper-
  evident record.
* `verificationRef` is `keccak256` of the verification UUID string — **never** the raw UUID.
* Solidity `^0.8.24`.

### `outcomeCode` (`docs/decisions.md` D-17) — locked

| Code | Status |
|---|---|
| 0 | `VERIFIED_MATCH` |
| 1 | `REVIEW_REQUIRED` |
| 2 | `NO_TRUSTED_RECORD` |
| 3 | `INTEGRITY_MISMATCH` |
| 4 | `PROCESSING_FAILED` |

`PENDING` is never recorded. Only a terminal status submits.

### Digest (`docs/decisions.md` D-13)

```
event_digest = SHA256(verification_id + ":" + outcome_code + ":" + CHAIN_EVENT_SALT)
```

Exactly this, exactly this order, exactly this separator. Any deviation makes the backend unable to
re-derive and verify its own events.

`CHAIN_EVENT_SALT` comes from `Settings`, never from a literal, never logged, never returned by any
endpoint, never committed.

### Nothing personal on-chain (`AGENTS.md` Rule 6)

The submission path is the single chokepoint. Three values go in. No name, no ID number, no field
value, no OCR text, no document hash, no filename. If a future change adds a fourth argument, that
is a `docs/blockchain.md` change requiring project-lead approval — and a very careful look at what it
would leak permanently.

### Failure isolation (`AGENTS.md` Rule 3, `docs/architecture.md`)

Chain state lives only in `blockchain_records.recording_status`. **No chain outcome ever modifies a
`verification_results` row.** Not on failure, not on success, not on retry. If `blockchain_service.py`
imports `verification_repo` for anything other than reading a verification's ID and status, look
hard at why.

### `CONFIRMED` means confirmed

Only after a receipt is received **and** the emitted event's fields are verified to match what was
submitted. Submission alone is `PENDING` (`docs/blockchain.md`). Showing `CONFIRMED` for an
unconfirmed transaction is the blockchain equivalent of claiming untested code works.

### Duplicate prevention

Before submitting, check for an existing non-`FAILED` `blockchain_records` row for that verification
(`blockchain_repo.get_active_for_verification`). A retry after failure creates a **new** row rather
than mutating the failed one, so the history of attempts survives.

### Testing (`AGENTS.md` Rule 11)

No Python test requires a running Hardhat node. `fake_adapter.py` covers the default suite. The
Solidity tests run under Hardhat separately.

---

# 7. Implementation Requirements

### Requirement 1 — Hardhat project

`chain/` with the local network on chain ID `31337`, `hardhat.config.js` pinned to Solidity
`0.8.24`, and `scripts/deploy.js` printing the deployed address in a form that is easy to paste into
`.env` (`docs/deployment-demo.md`).

### Requirement 2 — The contract

As specified. Nothing more. Resist adding access control, events for other lifecycle moments, or a
`getVerification` view — none are in the design, and each adds surface without adding value.

### Requirement 3 — Solidity tests

`chain/test/VerificationRegistry.test.js`: the event emits with correct arguments; `recordedAt`
matches `block.timestamp`; two different refs produce two independent events; the ABI exposes no
update or delete function.

```bash
cd chain && npx hardhat test
```

### Requirement 4 — Adapter interface

```python
class BlockchainAdapter(ABC):
    def submit_event(self, verification_ref: bytes, event_digest: bytes, outcome_code: int) -> str:
        """Submit; return the transaction hash. Raises on submission failure."""

    def get_receipt(self, tx_hash: str, timeout_seconds: int) -> ReceiptResult:
        """Wait for a receipt. Returns status, block number, and emitted event fields."""
```

`web3` is imported **only** in `web3_adapter.py`.

### Requirement 5 — Web3 adapter

Connect to `BLOCKCHAIN_RPC_URL`, verify the connected chain ID equals `BLOCKCHAIN_CHAIN_ID` at
startup (a mismatch is a configuration error, not a runtime surprise), load the ABI, and sign with
the local Hardhat account. Retry submission up to `BLOCKCHAIN_MAX_RETRIES` (default 2) with backoff
before raising. Wait up to `BLOCKCHAIN_TX_TIMEOUT_SECONDS` (default 30) for a receipt.

### Requirement 6 — Fake adapter

Modes: `success` (canned deterministic tx hash and matching receipt), `rpc_unavailable` (raises on
connect), `revert` (receipt with failure status), `timeout` (never returns a receipt),
`event_mismatch` (receipt whose emitted fields differ from what was submitted — this is what proves
the verification step in Requirement 7 actually runs).

### Requirement 7 — Blockchain service

`submit_verification(verification_id, session) -> BlockchainRecord`:

1. `BLOCKCHAIN_ENABLED=false` → write `NOT_REQUESTED`, return.
2. Verification status is `PENDING` → `NOT_REQUESTED`, return.
3. An active non-`FAILED` record exists → return it; do not resubmit.
4. Compute `verification_ref = keccak256(verification_id)` and the digest per the formula.
5. Map status → `outcomeCode`.
6. Write a `PENDING` row, submit, store the tx hash.
7. Wait for the receipt; **verify the emitted event fields match what was submitted**; then
   `CONFIRMED`.
8. Any failure → `FAILED` with an `error_code`. **Never touch the verification row.**

### Requirement 8 — Endpoint

`GET /verifications/{verification_id}/blockchain` per `docs/api.md`, **including `error_code`** —
this is what makes a `FAILED` state diagnosable from the API alone. When disabled, `200` with
`recording_status: "NOT_REQUESTED"` and every other field null, `error_code` included. `404` only
when the *verification* does not exist. Never returns `CHAIN_EVENT_SALT` or a private key.

### Error Handling

| Situation | Result |
|---|---|
| RPC unreachable | `FAILED`, `error_code: RPC_UNAVAILABLE` |
| Transaction reverts | `FAILED`, `error_code: TX_REVERTED` |
| Receipt timeout | `FAILED`, `error_code: RECEIPT_TIMEOUT` |
| Emitted event does not match submission | `FAILED`, `error_code: EVENT_MISMATCH` — never `CONFIRMED` |
| Chain ID mismatch | Startup configuration error |
| Contract address unset with blockchain enabled | Startup failure (Task 01's validation) |

In every one of these, the verification status is unchanged.

---

# 8. Testing Requirements

## Solidity Tests

```bash
cd chain && npx hardhat test
```

Event arguments correct; `recordedAt` equals `block.timestamp`; independent events for different
refs; ABI contains no update or delete function.

## Python Tests — default suite, fake adapter only

`backend/tests/test_blockchain_adapter.py`:

**Digest**
* Matches the `docs/blockchain.md` formula exactly, verified against an independently computed
  expected value — not against your own implementation calling itself.
* Same inputs → same digest; different `outcome_code` → different digest; different salt →
  different digest.
* **The digest contains no recoverable field value.** Assert it is a fixed-length hex string and does
  not contain any fixture value as a substring.

**Payload privacy — the most important tests here**
* The submitted arguments are exactly three values of the right types.
* `verification_ref` is `keccak256`, not the raw UUID — assert the raw UUID string does not appear.
* **Assert no fixture value — `"Aarav Demo"`, `"DEMO-STU-001"`, `"B.Tech CSE"` — appears anywhere in
  the submitted payload.**

**Status mapping**
* Each of the five terminal statuses maps to its documented code.
* `PENDING` → `NOT_REQUESTED`, nothing submitted.

**Chain states**
* Success → `CONFIRMED` with tx hash, `submitted_at`, `confirmed_at`.
* `rpc_unavailable` → `FAILED`, `RPC_UNAVAILABLE`.
* `revert` → `FAILED`, `TX_REVERTED`.
* `timeout` → `FAILED`, `RECEIPT_TIMEOUT`.
* `event_mismatch` → `FAILED`, `EVENT_MISMATCH`, **never** `CONFIRMED`.

**Failure isolation — assert explicitly**
* After every failure mode above, the `verification_results` row is byte-identical to before.

**Duplicates**
* Submitting twice with an active record → one submission, existing record returned.
* Submitting after a `FAILED` → a new row; the failed row still exists.

**Disabled**
* `BLOCKCHAIN_ENABLED=false` → `NOT_REQUESTED`, no adapter call at all.

**Secrets**
* `CHAIN_EVENT_SALT` never appears in any response body or log line.

**Isolation**
* No `web3` import during the default suite — assert `"web3" not in sys.modules`.

Run:

```bash
cd backend && pytest tests/test_blockchain_adapter.py
```

## Manual Verification

1. `cd chain && npx hardhat node` in its own terminal.
2. `npx hardhat run scripts/deploy.js --network localhost` → paste the address into `.env`.
3. Submit a verification → `CONFIRMED` with a real tx hash.
4. Inspect the transaction in the Hardhat node output. **Confirm by eye that it contains no personal
   data** — three values, one of them an opaque digest.
5. Stop the node. Submit another → `FAILED`, `RPC_UNAVAILABLE`, **and the verification status is
   unchanged**.
6. Restart the node, redeploy, retry → a new record, `CONFIRMED`; the failed record persists.

---

# 9. Acceptance Criteria

* [ ] Contract matches `docs/blockchain.md` exactly; append-only, no update/delete/owner/upgrade.
* [ ] `verificationRef` is `keccak256` of the UUID, never the raw UUID.
* [ ] Digest matches the D-13 formula exactly.
* [ ] `outcomeCode` mapping matches D-17; `PENDING` never submitted.
* [ ] **No personal data, field value, OCR text, or document hash in any submitted payload.**
* [ ] `web3` imported only in `web3_adapter.py`.
* [ ] `fake_adapter.py` covers success, RPC failure, revert, timeout, and event mismatch.
* [ ] `CONFIRMED` only after receipt **and** event-field verification.
* [ ] Retries bounded by `BLOCKCHAIN_MAX_RETRIES`; timeout by `BLOCKCHAIN_TX_TIMEOUT_SECONDS`.
* [ ] Duplicate prevention works; a retry after failure creates a new row.
* [ ] **No chain outcome ever modifies a verification row** — asserted in tests.
* [ ] `GET .../blockchain` matches `docs/api.md`, including `error_code`; `NOT_REQUESTED` when disabled.
* [ ] `CHAIN_EVENT_SALT` never logged, returned, or committed.
* [ ] Solidity tests pass; Python default suite passes without importing `web3`.
* [ ] Manual verification done, including the node-down isolation check.
* [ ] `git diff` reviewed; development log updated; branch pushed; PR prepared.

---

# 10. Known Risks

* **Describing the digest as a document hash.** It is not one, and saying so would claim document
  integrity this project does not provide (`decisions.md` D-22, `blockchain.md` §"Two different
  goals"). Never put `documents.sha256` on-chain — it would create a permanent confirmation oracle
  while proving nothing.
* **Adding a field to the payload.** Every instinct says "include the document hash, it's just a
  hash". It is also permanent, and combined with a known document it becomes a confirmation oracle.
  Three values, as documented.
* **Marking `CONFIRMED` on submission.** The single most likely correctness bug here, and it makes
  the UI lie. The `event_mismatch` fake mode exists to prove the verification step runs.
* **Chain failure leaking into verification status.** Test it explicitly; do not assume.
* **Hardhat state resetting on restart.** Expected. The contract address changes every time.
  `docs/deployment-demo.md` specifies the order for this reason, and it is the most common demo-day
  confusion.
* **Committing the salt or a private key.** `.gitignore` covers `.env`; verify before the first push.
  A committed salt means generating a new one and rewriting history.
* **Enriching the contract.** Access control, a getter, an upgrade path — each sounds like good
  practice and each is out of scope. An append-only contract with one function is the design.

---

# 11. Open Questions

* None on the contract or digest — D-13 and D-17 resolve them.
* **Whether a corrected verification (Task 08) triggers a second submission** is **Task 10**'s
  decision. This task supports it: a new verification ID produces a different `verificationRef` and a
  different digest, so both events coexist without collision. Flag it to the lead; do not decide it.
* Node/Hardhat versions come from `docs/ENVIRONMENT-REPORT.md`. If Hardhat will not run on a
  teammate's machine, that teammate uses `fake_adapter.py`, but the **demo machine must run it**.

---

# 12. Handoff Notes

* Publish in the log: the `BlockchainAdapter` signatures, the `submit_verification()` signature, and
  the deploy command with an example address.
* Tell Task 10 that submission happens only on a terminal status, and ask them to decide the
  corrected-verification re-submission behaviour.
* Tell Task 11 that blockchain status is a **separate badge** and that `FAILED` there is not a
  verification failure (`docs/frontend.md`).
* Write the exact demo sequence — start node, deploy, paste address, restart backend — into
  `docs/deployment-demo.md` if it is not already precise. Task 12 depends on it being right.

---

# 13. Definition of Done

```text
Implementation complete
        +
Solidity tests passing
        +
Python default suite passing without importing web3
        +
Manual verification complete (including node-down isolation)
        +
Payload confirmed to contain no personal data
        +
Scope verified (no flow wiring, no verification changes)
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

1. Read `AGENTS.md`, especially Rules 3 and 6.
2. Read `docs/blockchain.md` **completely** — contract shape, digest formula, and `outcomeCode`
   mapping are all exact.
3. Read `docs/configuration.md` for the `BLOCKCHAIN_*` variables.
4. Read this task file completely.
5. State your plan, including the exact digest construction, before coding.

During implementation:

* **Put nothing on-chain beyond the three documented values.** No document hash, no field value, no
  name, no filename.
* Keep the contract append-only. No update, delete, owner, pause, or upgrade.
* Mark `CONFIRMED` only after a receipt **and** event-field verification.
* **Never let a chain outcome change a verification status.** Ever.
* Import `web3` only in `web3_adapter.py`.
* Build against `fake_adapter.py` first; verify the real path manually once.
* Never log or return `CHAIN_EVENT_SALT`.

If you think the payload needs another field, **stop and ask the project lead** — that is a
`docs/blockchain.md` change with permanent privacy consequences.

Before PR:

* Run `npx hardhat test` and `pytest tests/test_blockchain_adapter.py`; report both outputs.
* Manually confirm a real transaction contains no personal data.
* Manually confirm a stopped node leaves verification status unchanged.
* Review `git diff` and `git status`; confirm no `.env` and no salt.
* Update `logs/task-09-blockchain.md`.
* Push and open the PR per `docs/git-workflow.md`.
