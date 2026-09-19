
"""Repository tests for DocuTrust Task 02."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    BlockchainErrorCode,
    BlockchainRecord,
    Document,
    DocumentCategory,
    ExtractionResult,
    ExtractionStatus,
    ProcessingState,
    RecordingStatus,
    RegistryRecord,
    ReviewAction,
    ReviewActionType,
    VerificationResult,
    VerificationStatus,
)
from app.repositories import (
    blockchain_repo,
    documents_repo,
    extraction_repo,
    registry_repo,
    review_repo,
    verification_repo,
)


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def make_document(**overrides):
    values = {
        "category": DocumentCategory.ACADEMIC_CERTIFICATE,
        "original_filename": "certificate.pdf",
        "storage_key": "uploads/certificate.pdf",
        "sha256": "a" * 64,
        "mime_type": "application/pdf",
        "byte_size": 1024,
        "page_count": 1,
        "processing_state": ProcessingState.UPLOADED,
        "uploaded_at": now(),
    }
    values.update(overrides)
    return Document(**values)


def make_extraction(document, **overrides):
    values = {
        "document": document,
        "engine_name": "test-engine",
        "engine_version": "1.0",
        "raw_ocr_json": '{"text": "sample"}',
        "extracted_fields_json": '{"name": "Test"}',
        "warnings_json": "[]",
        "status": ExtractionStatus.SUCCEEDED,
        "created_at": now(),
    }
    values.update(overrides)
    return ExtractionResult(**values)


def make_registry(**overrides):
    values = {
        "category": DocumentCategory.ACADEMIC_CERTIFICATE,
        "synthetic_record_key": "SYN-001",
        "fields_json": '{"name": "Test"}',
        "source_label": "synthetic-test-data",
        "active": True,
        "created_at": now(),
        "updated_at": now(),
    }
    values.update(overrides)
    return RegistryRecord(**values)


def make_verification(document, **overrides):
    values = {
        "document": document,
        "status": VerificationStatus.PENDING,
        "field_comparisons_json": "[]",
        "rule_results_json": "[]",
        "reason_codes_json": "[]",
        "created_at": now(),
    }
    values.update(overrides)
    return VerificationResult(**values)


def make_review(verification, **overrides):
    values = {
        "verification": verification,
        "reviewer_ref": "reviewer-test",
        "action": ReviewActionType.ACCEPT,
        "corrections_json": None,
        "comment": None,
        "created_at": now(),
    }
    values.update(overrides)
    return ReviewAction(**values)


def make_blockchain(verification, **overrides):
    values = {
        "verification": verification,
        "chain_id": 31337,
        "contract_address": "0x" + "1" * 40,
        "transaction_hash": None,
        "event_digest": "b" * 64,
        "recording_status": RecordingStatus.PENDING,
        "submitted_at": now(),
        "confirmed_at": None,
        "error_code": None,
    }
    values.update(overrides)
    return BlockchainRecord(**values)


def test_documents_create_and_get_by_id(db_session):
    document = make_document()

    created = documents_repo.create(db_session, document)

    assert created.id is not None
    assert documents_repo.get_by_id(db_session, created.id) is created
    assert documents_repo.get_by_id(db_session, "missing") is None


def test_documents_update_processing_state(db_session):
    document = documents_repo.create(db_session, make_document())

    updated = documents_repo.update_processing_state(
        db_session,
        document.id,
        ProcessingState.OCR_IN_PROGRESS,
    )

    assert updated is document
    assert updated.processing_state == ProcessingState.OCR_IN_PROGRESS
    assert (
        documents_repo.update_processing_state(
            db_session, "missing", ProcessingState.OCR_DONE
        )
        is None
    )


def test_documents_list_recent_newest_first(db_session):
    base = now()
    older = make_document(
        storage_key="uploads/older.pdf",
        uploaded_at=base - timedelta(minutes=2),
    )
    newer = make_document(
        storage_key="uploads/newer.pdf",
        uploaded_at=base - timedelta(minutes=1),
    )

    documents_repo.create(db_session, older)
    documents_repo.create(db_session, newer)

    result = documents_repo.list_recent(db_session, limit=10)

    assert result[:2] == [newer, older]


def test_documents_list_recent_respects_limit(db_session):
    for index in range(3):
        documents_repo.create(
            db_session,
            make_document(
                storage_key=f"uploads/{index}.pdf",
                uploaded_at=now() + timedelta(seconds=index),
            ),
        )

    assert len(documents_repo.list_recent(db_session, limit=2)) == 2


def test_extraction_create_and_latest_queries(db_session):
    document = documents_repo.create(db_session, make_document())
    base = now()

    older = make_extraction(
        document,
        created_at=base - timedelta(minutes=2),
    )
    newer = make_extraction(
        document,
        created_at=base - timedelta(minutes=1),
        engine_version="2.0",
    )

    extraction_repo.create(db_session, older)
    extraction_repo.create(db_session, newer)

    assert extraction_repo.get_latest_for_document(
        db_session, document.id
    ) is newer
    assert extraction_repo.get_latest_successful_for_document(
        db_session, document.id
    ) is newer
    assert extraction_repo.get_latest_for_document(
        db_session, "missing"
    ) is None


def test_extraction_latest_successful_skips_failed(db_session):
    document = documents_repo.create(db_session, make_document())
    base = now()

    successful = make_extraction(
        document,
        status=ExtractionStatus.SUCCEEDED,
        created_at=base - timedelta(minutes=1),
    )
    failed = make_extraction(
        document,
        status=ExtractionStatus.FAILED,
        created_at=base,
        engine_version="2.0",
    )

    extraction_repo.create(db_session, successful)
    extraction_repo.create(db_session, failed)

    assert extraction_repo.get_latest_for_document(
        db_session, document.id
    ) is failed
    assert extraction_repo.get_latest_successful_for_document(
        db_session, document.id
    ) is successful


def test_extraction_latest_successful_returns_none_if_no_success(db_session):
    document = documents_repo.create(db_session, make_document())

    extraction_repo.create(
        db_session,
        make_extraction(document, status=ExtractionStatus.FAILED),
    )

    assert extraction_repo.get_latest_successful_for_document(
        db_session, document.id
    ) is None


def test_registry_create_and_get_queries(db_session):
    record = registry_repo.create(db_session, make_registry())

    assert record.id is not None
    assert registry_repo.get_by_id(db_session, record.id) is record
    assert registry_repo.get_by_id(db_session, "missing") is None
    assert (
        registry_repo.get_by_category_and_key(
            db_session,
            DocumentCategory.ACADEMIC_CERTIFICATE,
            "SYN-001",
        )
        is record
    )


def test_registry_lookup_missing_key_returns_none(db_session):
    assert (
        registry_repo.get_by_category_and_key(
            db_session,
            DocumentCategory.ACADEMIC_CERTIFICATE,
            "UNKNOWN",
        )
        is None
    )


def test_registry_list_active_by_category_filters_and_orders(db_session):
    base = now()

    first = make_registry(
        synthetic_record_key="SYN-001",
        created_at=base - timedelta(minutes=2),
    )
    second = make_registry(
        synthetic_record_key="SYN-002",
        created_at=base - timedelta(minutes=1),
    )
    inactive = make_registry(
        synthetic_record_key="SYN-003",
        active=False,
        created_at=base,
    )
    other_category = make_registry(
        category=DocumentCategory.INSTITUTIONAL_ID,
        synthetic_record_key="SYN-004",
    )

    for record in (first, second, inactive, other_category):
        registry_repo.create(db_session, record)

    result = registry_repo.list_active_by_category(
        db_session,
        DocumentCategory.ACADEMIC_CERTIFICATE,
    )

    assert result == [first, second]


def test_registry_duplicate_category_and_key_raises(db_session):
    registry_repo.create(db_session, make_registry())

    duplicate = make_registry()
    with pytest.raises(IntegrityError):
        registry_repo.create(db_session, duplicate)

    db_session.rollback()


def test_verification_create_and_get_by_id(db_session):
    document = documents_repo.create(db_session, make_document())
    verification = verification_repo.create(
        db_session, make_verification(document)
    )

    assert verification.id is not None
    assert verification_repo.get_by_id(
        db_session, verification.id
    ) is verification
    assert verification_repo.get_by_id(db_session, "missing") is None


def test_verification_latest_and_list_newest_first(db_session):
    document = documents_repo.create(db_session, make_document())
    base = now()

    first = make_verification(
        document,
        created_at=base - timedelta(minutes=2),
    )
    second = make_verification(
        document,
        created_at=base - timedelta(minutes=1),
    )
    third = make_verification(document, created_at=base)

    for item in (first, second, third):
        verification_repo.create(db_session, item)

    assert verification_repo.get_latest_for_document(
        db_session, document.id
    ) is third
    assert verification_repo.list_for_document(
        db_session, document.id
    ) == [third, second, first]
    assert verification_repo.get_latest_for_document(
        db_session, "missing"
    ) is None


def test_review_create_and_list_newest_first(db_session):
    document = documents_repo.create(db_session, make_document())
    verification = verification_repo.create(
        db_session, make_verification(document)
    )
    base = now()

    older = make_review(
        verification,
        created_at=base - timedelta(minutes=1),
    )
    newer = make_review(
        verification,
        created_at=base,
        action=ReviewActionType.CORRECT,
    )

    review_repo.create(db_session, older)
    review_repo.create(db_session, newer)

    assert review_repo.list_for_verification(
        db_session, verification.id
    ) == [newer, older]
    assert review_repo.list_for_verification(
        db_session, "missing"
    ) == []


def test_blockchain_create_and_get_by_verification_id(db_session):
    document = documents_repo.create(db_session, make_document())
    verification = verification_repo.create(
        db_session, make_verification(document)
    )
    record = blockchain_repo.create(
        db_session, make_blockchain(verification)
    )

    assert record.id is not None
    assert blockchain_repo.get_by_verification_id(
        db_session, verification.id
    ) == [record]


def test_blockchain_active_returns_newest_nonfailed(db_session):
    document = documents_repo.create(db_session, make_document())
    verification = verification_repo.create(
        db_session, make_verification(document)
    )
    base = now()

    old_pending = make_blockchain(
        verification,
        submitted_at=base - timedelta(minutes=2),
    )
    newer_failed = make_blockchain(
        verification,
        submitted_at=base,
        recording_status=RecordingStatus.FAILED,
        error_code=BlockchainErrorCode.RPC_UNAVAILABLE,
    )
    newer_pending = make_blockchain(
        verification,
        submitted_at=base - timedelta(minutes=1),
        event_digest="c" * 64,
    )

    for record in (old_pending, newer_failed, newer_pending):
        blockchain_repo.create(db_session, record)

    assert blockchain_repo.get_active_for_verification(
        db_session, verification.id
    ) is newer_pending


def test_blockchain_active_returns_none_when_all_failed(db_session):
    document = documents_repo.create(db_session, make_document())
    verification = verification_repo.create(
        db_session, make_verification(document)
    )

    blockchain_repo.create(
        db_session,
        make_blockchain(
            verification,
            recording_status=RecordingStatus.FAILED,
            error_code=BlockchainErrorCode.RPC_UNAVAILABLE,
        ),
    )

    assert blockchain_repo.get_active_for_verification(
        db_session, verification.id
    ) is None


def test_blockchain_mark_confirmed_only_from_pending(db_session):
    document = documents_repo.create(db_session, make_document())
    verification = verification_repo.create(
        db_session, make_verification(document)
    )
    record = blockchain_repo.create(
        db_session, make_blockchain(verification)
    )
    confirmed_at = now()

    updated = blockchain_repo.mark_confirmed(
        db_session, record.id, confirmed_at
    )

    assert updated is record
    assert record.recording_status == RecordingStatus.CONFIRMED
    assert record.confirmed_at == confirmed_at

    assert blockchain_repo.mark_confirmed(
        db_session, "missing", confirmed_at
    ) is None
    assert blockchain_repo.mark_confirmed(
        db_session, record.id, now()
    ) is None


def test_blockchain_mark_failed_only_from_pending(db_session):
    document = documents_repo.create(db_session, make_document())
    verification = verification_repo.create(
        db_session, make_verification(document)
    )
    record = blockchain_repo.create(
        db_session, make_blockchain(verification)
    )

    updated = blockchain_repo.mark_failed(
        db_session,
        record.id,
        BlockchainErrorCode.RPC_UNAVAILABLE,
    )

    assert updated is record
    assert record.recording_status == RecordingStatus.FAILED
    assert record.error_code == BlockchainErrorCode.RPC_UNAVAILABLE

    assert blockchain_repo.mark_failed(
        db_session,
        "missing",
        BlockchainErrorCode.RPC_UNAVAILABLE,
    ) is None
    assert blockchain_repo.mark_failed(
        db_session,
        record.id,
        BlockchainErrorCode.TX_REVERTED,
    ) is None


def test_failed_blockchain_record_cannot_be_resurrected(db_session):
    document = documents_repo.create(db_session, make_document())
    verification = verification_repo.create(
        db_session, make_verification(document)
    )
    record = blockchain_repo.create(
        db_session,
        make_blockchain(
            verification,
            recording_status=RecordingStatus.FAILED,
            error_code=BlockchainErrorCode.RPC_UNAVAILABLE,
        ),
    )

    assert blockchain_repo.mark_confirmed(
        db_session, record.id, now()
    ) is None
    assert blockchain_repo.mark_failed(
        db_session, record.id, BlockchainErrorCode.TX_REVERTED
    ) is None
    assert record.recording_status == RecordingStatus.FAILED


def test_blockchain_retry_is_a_new_record(db_session):
    document = documents_repo.create(db_session, make_document())
    verification = verification_repo.create(
        db_session, make_verification(document)
    )

    failed = blockchain_repo.create(
        db_session,
        make_blockchain(
            verification,
            recording_status=RecordingStatus.FAILED,
            error_code=BlockchainErrorCode.RPC_UNAVAILABLE,
        ),
    )
    retry = blockchain_repo.create(
        db_session,
        make_blockchain(
            verification,
            event_digest="c" * 64,
        ),
    )

    assert retry.id != failed.id
    assert retry.recording_status == RecordingStatus.PENDING
    assert blockchain_repo.get_active_for_verification(
        db_session, verification.id
    ) is retry


def test_repositories_do_not_expose_verification_status_mutator():
    assert not hasattr(verification_repo, "update_status")
    assert not hasattr(verification_repo, "set_status")