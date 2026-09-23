import hashlib

import pytest

from app.adapters.blockchain.base import BlockchainAdapter
from app.adapters.blockchain.fake_adapter import FakeBlockchainAdapter
from app.services.blockchain_service import (
    build_event_digest,
    build_verification_ref,
    outcome_code_for_status,
)


def test_digest_exact_sha256():
    result = build_event_digest(
        "abc",
        0,
        "secret",
    )

    expected = hashlib.sha256(
        b"abc:0:secret"
    ).digest()

    assert result == expected
    assert len(result) == 32


def test_digest_deterministic():
    assert build_event_digest("abc", 0, "salt") == \
        build_event_digest("abc", 0, "salt")


def test_digest_changes_with_verification_id():
    assert build_event_digest("abc", 0, "salt") != \
        build_event_digest("xyz", 0, "salt")


def test_digest_changes_with_outcome():
    assert build_event_digest("abc", 0, "salt") != \
        build_event_digest("abc", 1, "salt")


def test_digest_changes_with_salt():
    assert build_event_digest("abc", 0, "salt1") != \
        build_event_digest("abc", 0, "salt2")


def test_verification_ref_is_keccak_32_bytes():
    ref = build_verification_ref("abc")

    assert isinstance(ref, bytes)
    assert len(ref) == 32


@pytest.mark.parametrize(
    "status,expected",
    [
        ("VERIFIED_MATCH", 0),
        ("REVIEW_REQUIRED", 1),
        ("NO_TRUSTED_RECORD", 2),
        ("INTEGRITY_MISMATCH", 3),
        ("PROCESSING_FAILED", 4),
    ],
)
def test_outcome_mapping(status, expected):
    assert outcome_code_for_status(status) == expected


def test_pending_has_no_outcome():
    assert outcome_code_for_status("PENDING") is None


def test_fake_success():
    adapter = FakeBlockchainAdapter()

    ref = b"r" * 32
    digest = b"d" * 32

    tx = adapter.submit_event(ref, digest, 0)
    receipt = adapter.get_receipt(tx, 30)

    assert receipt.status == 1
    assert receipt.verification_ref == ref
    assert receipt.event_digest == digest
    assert receipt.outcome_code == 0


def test_fake_revert():
    adapter = FakeBlockchainAdapter(mode="revert")

    tx = adapter.submit_event(
        b"r" * 32,
        b"d" * 32,
        0,
    )

    receipt = adapter.get_receipt(tx, 30)

    assert receipt.status == 0


def test_fake_timeout():
    adapter = FakeBlockchainAdapter(mode="timeout")

    tx = adapter.submit_event(
        b"r" * 32,
        b"d" * 32,
        0,
    )

    with pytest.raises(TimeoutError):
        adapter.get_receipt(tx, 30)


def test_fake_event_mismatch():
    adapter = FakeBlockchainAdapter(mode="event_mismatch")

    ref = b"r" * 32
    digest = b"d" * 32

    tx = adapter.submit_event(ref, digest, 0)
    receipt = adapter.get_receipt(tx, 30)

    assert receipt.status == 1
    assert receipt.verification_ref != ref


def test_fake_rpc_unavailable():
    with pytest.raises(ConnectionError):
        FakeBlockchainAdapter(mode="rpc_unavailable")


def test_privacy_payload_has_exactly_three_values():
    adapter = FakeBlockchainAdapter()

    ref = b"r" * 32
    digest = b"d" * 32
    outcome = 0

    adapter.submit_event(ref, digest, outcome)

    assert len(adapter.submissions) == 1

    submission = adapter.submissions[0]

    assert len(submission) == 3
    assert submission == (ref, digest, outcome)


def test_adapter_interface_exists():
    assert hasattr(BlockchainAdapter, "submit_event")
    assert hasattr(BlockchainAdapter, "get_receipt")
