# Task 09 — Solidity Contract and Local Chain Adapter

## Automated validation

- Solidity/Hardhat tests: 6 passing
- Blockchain adapter tests: 19 passing
- Full backend suite: 243 passed, 1 deselected

## Local chain

- RPC: http://127.0.0.1:8545
- Chain ID: 31337
- Contract: 0x5FbDB2315678afecb367f032d93F642f64180aa3
- Contract: VerificationRegistry

## Manual success test

A real transaction was submitted through Web3BlockchainAdapter to the local Hardhat chain.

- Transaction hash: 0x6e85bce9503fa1c2b7e845212f30b072044db8723cde19fd8b86aa2eb026cb64
- Receipt status: 1
- Block: 2
- Verification reference event matched: true
- Event digest matched: true
- Outcome code: 1
- Contract recordedAt event field was returned successfully

The test payload used only opaque 32-byte values and an outcome code. No personal data was submitted.

## Manual stopped-chain test

The Hardhat RPC process was stopped and port 8545 was verified unavailable.

A new Web3BlockchainAdapter submission then failed with:

`ConnectionError: RPC unavailable`

No transaction hash was produced.

## API validation

Swagger endpoint:

`GET /api/v1/verifications/{verification_id}/blockchain`

was manually exercised and returned HTTP 200 with:

`recording_status: NOT_REQUESTED`

when no blockchain record existed.

## Privacy

The contract accepts exactly:

1. verificationRef
2. eventDigest
3. outcomeCode

No personal verification fields are stored on-chain.

## Scope

Task 09 does not add overall verification-flow submission wiring. That remains for Task 10.
