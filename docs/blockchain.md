# Blockchain Design

## Goal

Record a minimal, non-identifying, tamper-evident event per completed verification on a local
Ethereum-compatible chain. The chain is an **audit mechanism for what our application recorded**,
never a source of document authenticity (`project-context.md`).

## Components (locked, resolves D-05)

- **Chain:** Hardhat local network (`chain/hardhat.config.js`), chain ID `31337`.
- **Contract:** `chain/contracts/VerificationRegistry.sol`, Solidity `^0.8.24`.
- **Backend adapter:** `backend/app/adapters/blockchain/web3_adapter.py`, using Web3.py.
- **Configuration:** `BLOCKCHAIN_ENABLED`, `BLOCKCHAIN_RPC_URL`, `BLOCKCHAIN_CHAIN_ID`,
  `BLOCKCHAIN_CONTRACT_ADDRESS` (`configuration.md`).

Exact Web3.py / Hardhat / Node.js version compatibility is confirmed during Task 01/09's environment
check before pinning — do not pin blindly from this doc.

## Contract (locked shape)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract VerificationRegistry {
    event VerificationRecorded(
        bytes32 indexed verificationRef,
        bytes32 eventDigest,
        uint8 outcomeCode,
        uint256 recordedAt
    );

    function recordVerification(
        bytes32 verificationRef,
        bytes32 eventDigest,
        uint8 outcomeCode
    ) external {
        emit VerificationRecorded(verificationRef, eventDigest, outcomeCode, block.timestamp);
    }
}
```

Append-only: the contract has no update/delete function for a recorded event. `verificationRef` is
a `bytes32` derived from the internal `verification_results.id` UUID (`keccak256` of the UUID
string) — never the raw UUID string itself, and never any PII.

## `outcomeCode` enum (locked, resolves ambiguity from the earlier draft)

| Code | Status |
|---|---|
| `0` | `VERIFIED_MATCH` |
| `1` | `REVIEW_REQUIRED` |
| `2` | `NO_TRUSTED_RECORD` |
| `3` | `INTEGRITY_MISMATCH` |
| `4` | `PROCESSING_FAILED` |

`PENDING` is never recorded on-chain — only a *terminal* verification status triggers a chain
submission.

## Two different goals — do not conflate them (resolves D-22)

This system has two integrity questions, and they are answered by two different mechanisms. Mixing
them up is the most consequential thing anyone can get wrong about this document.

| Goal | Question it answers | Mechanism | Where it lives |
|---|---|---|---|
| **Outcome integrity** | "Did our system really reach this outcome, at this time, and has that record been altered since?" | The on-chain `eventDigest` below | The chain |
| **Document integrity** | "Is the file we are holding now byte-identical to the file that was uploaded?" | `documents.sha256`, computed at upload | The local database only |

**The `eventDigest` is not a document hash and must never be described as one.** It takes the
verification ID, the outcome code, and a server-side salt. It contains no document bytes, so it
cannot detect that a document changed, and it cannot prove anything about the uploaded file.

The wording rule that follows from this: say "the verification outcome is recorded on-chain and
cannot be silently altered." Never say "the document is hashed on the blockchain", "blockchain-
verified document", or "tamper-proof document". Those claim document integrity, which nothing here
provides (`glossary.md`, `AGENTS.md` Rule 2).

### Why document integrity is out of scope for the MVP

`documents.sha256` tells us our own stored copy has not changed. It cannot tell us the *uploaded*
document was unaltered, because we have no trusted prior digest to compare against — the issuer
never published one. A hash of a file someone hands you proves only that you received that file.

Putting `documents.sha256` on-chain would make this worse, not better. It would look like proof of
document authenticity while proving nothing, and — because a digest of a known document is
verifiable by anyone holding that document — it would create a permanent confirmation oracle:
given a candidate certificate, a chain observer could test whether that exact file passed through
our system. That is a privacy regression in exchange for a false guarantee.

### What real document integrity would require

Recorded here so the team can answer the question properly if a judge asks, and so nobody
improvises it under deadline pressure:

1. The **issuing institution** publishes a digest of the document at issuance, signed with a key
   bound to its identity.
2. Verification recomputes the digest of the presented file and compares it to that published,
   signed value.
3. The chain anchors the *issuer's* commitment, not ours.

The essential ingredient is a **trusted prior digest from the issuer**. We do not have one and
cannot obtain one in a hackathon, which is exactly the same sourcing constraint that makes our
registry synthetic (`project-context.md`). Adding any of this to the MVP requires project-lead
approval and a security review — it is not a change anyone makes inside a task.

## Event digest construction (resolves D-13)

```
event_digest = SHA256( verification_id + ":" + outcome_code + ":" + CHAIN_EVENT_SALT )
```

- `CHAIN_EVENT_SALT` is a server-side secret, generated once per environment, stored in `.env`
  (never committed — `configuration.md`), never transmitted anywhere.
- This produces an opaque value that (a) cannot be reversed to recover the verification ID without
  the salt, and (b) still lets the backend re-derive and match the digest for its **own**
  verification rows, confirming an on-chain event corresponds to a real local record without
  exposing that link to anyone reading the chain.
- **Scope, stated plainly:** it binds "this internal verification ID produced this outcome." It
  binds nothing about the document. See the table above.

## What is never on-chain

Full documents, raw OCR text, extracted field values, names, dates of birth, `demo_pan_code`
values, ID numbers, or any value from `extracted_fields_json`/`fields_json`. Enforced by the
`event_digest` construction above containing none of these as direct or recoverable inputs, and by
code review of `blockchain_service.py`'s payload-building function as the single chokepoint.

## Chain state (`blockchain_records.recording_status`)

| State | Meaning |
|---|---|
| `NOT_REQUESTED` | `BLOCKCHAIN_ENABLED=false`, or verification status is still `PENDING` |
| `PENDING` | Transaction submitted, awaiting receipt |
| `CONFIRMED` | Receipt received and event fields verified to match what was submitted |
| `FAILED` | RPC unreachable, transaction reverted, or receipt wait timed out (`BLOCKCHAIN_TX_TIMEOUT_SECONDS`, default 30) |

Chain state is always independent of `verification_results.status` — a `FAILED` chain state never
changes, retries, or hides the verification result itself.

## Operational notes

- Local Hardhat network state resets on restart. `deployment-demo.md` documents the exact
  deploy/seed sequence so the contract address is reproducible per session.
- `web3_adapter.py` retries a submission up to `BLOCKCHAIN_MAX_RETRIES` (default 2) with backoff
  before setting `FAILED`; a duplicate submission for the same `verification_id` is prevented by
  checking for an existing non-`FAILED` `blockchain_records` row first.
- Tests use `adapters/blockchain/fake_adapter.py` (deterministic canned tx hash/receipt, and a mode
  that simulates RPC failure) — no test requires a running Hardhat node (`NFR-05`).
