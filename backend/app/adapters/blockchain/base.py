from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ReceiptResult:
    status: int
    block_number: int | None
    verification_ref: bytes | None
    event_digest: bytes | None
    outcome_code: int | None
    recorded_at: int | None = None


class BlockchainAdapter(ABC):
    @abstractmethod
    def submit_event(
        self,
        verification_ref: bytes,
        event_digest: bytes,
        outcome_code: int,
    ) -> str:
        """Submit; return transaction hash."""

    @abstractmethod
    def get_receipt(
        self,
        tx_hash: str,
        timeout_seconds: int,
    ) -> ReceiptResult:
        """Wait for receipt and return status/event fields."""
