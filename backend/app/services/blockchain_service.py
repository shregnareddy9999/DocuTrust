"""Task 09 blockchain recording service."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from eth_hash.auto import keccak
from sqlalchemy.orm import Session

from app.adapters.blockchain.base import BlockchainAdapter, ReceiptResult
from app.adapters.blockchain.fake_adapter import FakeBlockchainAdapter
from app.adapters.blockchain.web3_adapter import Web3BlockchainAdapter
from app.models.blockchain import (
    BlockchainErrorCode,
    BlockchainRecord,
    RecordingStatus,
)
from app.models.verification import VerificationStatus
from app.repositories import blockchain_repo, verification_repo


OUTCOME_CODES = {
    VerificationStatus.VERIFIED_MATCH: 0,
    VerificationStatus.REVIEW_REQUIRED: 1,
    VerificationStatus.NO_TRUSTED_RECORD: 2,
    VerificationStatus.INTEGRITY_MISMATCH: 3,
    VerificationStatus.PROCESSING_FAILED: 4,
}


def build_verification_ref(verification_id: str) -> bytes:
    """Return keccak256(verification UUID string)."""
    return keccak(verification_id.encode("utf-8"))


def build_event_digest(
    verification_id: str,
    outcome_code: int,
    chain_event_salt: str,
) -> bytes:
    """Return SHA-256(verification_id:outcome_code:salt)."""
    value = f"{verification_id}:{outcome_code}:{chain_event_salt}"
    return hashlib.sha256(value.encode("utf-8")).digest()


def outcome_code_for_status(status) -> int | None:
    """Map terminal verification status to its chain outcome code."""
    if isinstance(status, str):
        try:
            status = VerificationStatus(status)
        except ValueError:
            return None
    return OUTCOME_CODES.get(status)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _record_not_requested(
    session: Session,
    verification_id: str,
    chain_id: int,
    contract_address: str,
) -> BlockchainRecord:
    record = BlockchainRecord(
        verification_id=verification_id,
        chain_id=chain_id,
        contract_address=contract_address or "",
        transaction_hash=None,
        event_digest="",
        recording_status=RecordingStatus.NOT_REQUESTED,
        submitted_at=None,
        confirmed_at=None,
        error_code=None,
    )
    return blockchain_repo.create(session, record)


def _failure(
    session: Session,
    record_id: str,
    error_code: BlockchainErrorCode,
) -> BlockchainRecord:
    record = blockchain_repo.mark_failed(session, record_id, error_code)
    if record is None:
        raise RuntimeError("Unable to mark blockchain record as FAILED")
    return record


def _event_matches(
    receipt: ReceiptResult,
    verification_ref: bytes,
    event_digest: bytes,
    outcome_code: int,
) -> bool:
    return (
        receipt.verification_ref == verification_ref
        and receipt.event_digest == event_digest
        and receipt.outcome_code == outcome_code
    )


def _select_default_adapter() -> BlockchainAdapter:
    """Select the blockchain adapter for the current application environment."""
    from app.config import settings

    if settings.APP_ENV == "demo":
        return Web3BlockchainAdapter()

    return FakeBlockchainAdapter()


def submit_verification(
    session: Session,
    verification_id: str,
    *,
    adapter: BlockchainAdapter | None = None,
    enabled: bool = True,
    chain_id: int = 31337,
    contract_address: str = "",
    chain_event_salt: str = "TASK09-SIMULATED-SALT",
    timeout_seconds: int = 30,
) -> BlockchainRecord:
    """
    Record a terminal verification on the blockchain adapter.

    If no adapter is supplied, the adapter is selected from APP_ENV:
    - demo: real Web3 adapter
    - development/test: deterministic fake adapter
    """

    verification = verification_repo.get_by_id(session, verification_id)

    if verification is None:
        raise ValueError("Verification not found")

    if not enabled:
        return _record_not_requested(
            session,
            verification_id,
            chain_id,
            contract_address,
        )

    if verification.status == VerificationStatus.PENDING:
        return _record_not_requested(
            session,
            verification_id,
            chain_id,
            contract_address,
        )

    existing = blockchain_repo.get_active_for_verification(
        session,
        verification_id,
    )

    if existing is not None:
        return existing

    outcome_code = outcome_code_for_status(verification.status)

    if outcome_code is None:
        return _record_not_requested(
            session,
            verification_id,
            chain_id,
            contract_address,
        )

    verification_ref = build_verification_ref(verification_id)
    event_digest = build_event_digest(
        verification_id,
        outcome_code,
        chain_event_salt,
    )

    record = BlockchainRecord(
        verification_id=verification_id,
        chain_id=chain_id,
        contract_address=contract_address or "",
        transaction_hash=None,
        event_digest=event_digest.hex(),
        recording_status=RecordingStatus.PENDING,
        submitted_at=_now(),
        confirmed_at=None,
        error_code=None,
    )

    blockchain_repo.create(session, record)

    if adapter is None:
        adapter = _select_default_adapter()

    try:
        tx_hash = adapter.submit_event(
            verification_ref,
            event_digest,
            outcome_code,
        )
        record.transaction_hash = tx_hash
        session.flush()
    except ConnectionError:
        return _failure(
            session,
            record.id,
            BlockchainErrorCode.RPC_UNAVAILABLE,
        )
    except Exception:
        return _failure(
            session,
            record.id,
            BlockchainErrorCode.RPC_UNAVAILABLE,
        )

    try:
        receipt = adapter.get_receipt(
            tx_hash,
            timeout_seconds,
        )
    except TimeoutError:
        return _failure(
            session,
            record.id,
            BlockchainErrorCode.RECEIPT_TIMEOUT,
        )
    except ConnectionError:
        return _failure(
            session,
            record.id,
            BlockchainErrorCode.RPC_UNAVAILABLE,
        )
    except Exception:
        return _failure(
            session,
            record.id,
            BlockchainErrorCode.RPC_UNAVAILABLE,
        )

    if receipt.status != 1:
        return _failure(
            session,
            record.id,
            BlockchainErrorCode.TX_REVERTED,
        )

    if not _event_matches(
        receipt,
        verification_ref,
        event_digest,
        outcome_code,
    ):
        return _failure(
            session,
            record.id,
            BlockchainErrorCode.EVENT_MISMATCH,
        )

    confirmed = blockchain_repo.mark_confirmed(
        session,
        record.id,
        _now(),
    )

    if confirmed is None:
        raise RuntimeError("Unable to confirm blockchain record")

    return confirmed


def submit_verification_simulated(
    session: Session,
    verification_id: str,
    *,
    mode: str = "success",
    enabled: bool = True,
    chain_id: int = 31337,
    contract_address: str = "0xSIMULATED",
    chain_event_salt: str = "TASK09-SIMULATED-SALT",
    timeout_seconds: int = 30,
) -> BlockchainRecord:
    """Convenience entry point for deterministic Task 09 simulation."""

    adapter = FakeBlockchainAdapter(mode=mode)

    return submit_verification(
        session,
        verification_id,
        adapter=adapter,
        enabled=enabled,
        chain_id=chain_id,
        contract_address=contract_address,
        chain_event_salt=chain_event_salt,
        timeout_seconds=timeout_seconds,
    )