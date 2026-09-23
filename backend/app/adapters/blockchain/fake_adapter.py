"""Deterministic fake blockchain adapter for Task 09 tests."""

from __future__ import annotations

import hashlib
import time

from .base import BlockchainAdapter, ReceiptResult


class FakeBlockchainAdapter(BlockchainAdapter):
    MODES = {
        "success",
        "rpc_unavailable",
        "revert",
        "timeout",
        "event_mismatch",
    }

    def __init__(self, mode: str = "success"):
        if mode not in self.MODES:
            raise ValueError(f"Unknown fake blockchain mode: {mode}")

        self.mode = mode
        self.submissions = []

        if mode == "rpc_unavailable":
            raise ConnectionError("RPC unavailable")

    def submit_event(
        self,
        verification_ref: bytes,
        event_digest: bytes,
        outcome_code: int,
    ) -> str:
        self.submissions.append(
            (verification_ref, event_digest, outcome_code)
        )

        payload = (
            verification_ref
            + event_digest
            + bytes([outcome_code])
        )
        return "0x" + hashlib.sha256(payload).hexdigest()

    def get_receipt(
        self,
        tx_hash: str,
        timeout_seconds: int,
    ) -> ReceiptResult:
        if self.mode == "timeout":
            time.sleep(0)
            raise TimeoutError("Receipt timeout")

        verification_ref, event_digest, outcome_code = self.submissions[-1]

        if self.mode == "revert":
            return ReceiptResult(
                status=0,
                block_number=123,
                verification_ref=None,
                event_digest=None,
                outcome_code=None,
                recorded_at=None,
            )

        if self.mode == "event_mismatch":
            return ReceiptResult(
                status=1,
                block_number=123,
                verification_ref=b"\x00" * 32,
                event_digest=event_digest,
                outcome_code=outcome_code,
                recorded_at=123,
            )

        return ReceiptResult(
            status=1,
            block_number=123,
            verification_ref=verification_ref,
            event_digest=event_digest,
            outcome_code=outcome_code,
            recorded_at=123,
        )
