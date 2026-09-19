
"""Tests for DocuTrust SQLAlchemy models."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import event, inspect
from sqlalchemy.exc import IntegrityError, StatementError

from app.db import Base
from app.models import (
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


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def make_document(**overrides):
    values = {
        "category": DocumentCategory.ACADEMIC_CERTIFICATE,
        "original_filename": "certificate.pdf",
        "storage_key": "uploads/test-certificate.pdf",
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


def make_blockchain_record(verification, **overrides):
    values = {
        "verification": verification,
        "chain_id": 31337,
        "contract_address": "0x" + "1" * 40,
        "transaction_hash": None,
        "event_digest": "b" * 64,
        "recording_status": RecordingStatus.PENDING,
        "submitted_at": None,
        "confirmed_at": None,
        "error_code": None,
    }
    values.update(overrides)
    return BlockchainRecord(**values)


def enable_sqlite_foreign_keys(db_session):
    """Enable SQLite FK enforcement on this session's active connection."""
    connection = db_session.connection()
    raw_connection = connection.connection
    dbapi_connection = getattr(
        raw_connection, "driver_connection", raw_connection
    )

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys")
    enabled = cursor.fetchone()[0]
    cursor.close()

    assert enabled == 1


def test_all_six_tables_are_registered():
    expected = {
        "documents",
        "extraction_results",
        "registry_records",
        "verification_results",
        "review_actions",
        "blockchain_records",
    }
    assert expected.issubset(set(Base.metadata.tables))


@pytest.mark.parametrize(
    ("model", "expected_columns"),
    [
        (
            Document,
            {
                "id", "category", "original_filename", "storage_key",
                "sha256", "mime_type", "byte_size", "page_count",
                "processing_state", "uploaded_at",
            },
        ),
        (
            ExtractionResult,
            {
                "id", "document_id", "engine_name", "engine_version",
                "raw_ocr_json", "extracted_fields_json", "warnings_json",
                "status", "created_at",
            },
        ),
        (
            RegistryRecord,
            {
                "id", "category", "synthetic_record_key", "fields_json",
                "source_label", "active", "created_at", "updated_at",
            },
        ),
        (
            VerificationResult,
            {
                "id", "document_id", "registry_record_id", "status",
                "field_comparisons_json", "rule_results_json",
                "reason_codes_json", "supersedes_verification_id",
                "created_at",
            },
        ),
        (
            ReviewAction,
            {
                "id", "verification_id", "reviewer_ref", "action",
                "corrections_json", "comment", "created_at",
            },
        ),
        (
            BlockchainRecord,
            {
                "id", "verification_id", "chain_id", "contract_address",
                "transaction_hash", "event_digest", "recording_status",
                "submitted_at", "confirmed_at", "error_code",
            },
        ),
    ],
)
def test_model_has_expected_columns(model, expected_columns):
    assert expected_columns.issubset(set(model.__table__.columns.keys()))


@pytest.mark.parametrize(
    ("model", "field", "invalid_value"),
    [
        (Document, "category", "not_a_category"),
        (Document, "processing_state", "NOT_A_STATE"),
        (ExtractionResult, "status", "NOT_A_STATUS"),
        (RegistryRecord, "category", "not_a_category"),
        (VerificationResult, "status", "NOT_A_STATUS"),
        (ReviewAction, "action", "NOT_AN_ACTION"),
        (BlockchainRecord, "recording_status", "NOT_A_STATUS"),
        (BlockchainRecord, "error_code", "NOT_AN_ERROR"),
    ],
)
def test_enum_rejects_undocumented_value(
    db_session, model, field, invalid_value
):
    document = make_document()
    db_session.add(document)
    db_session.flush()

    verification = make_verification(document)
    db_session.add(verification)
    db_session.flush()

    if model is Document:
        instance = make_document(**{field: invalid_value})
    elif model is ExtractionResult:
        instance = make_extraction(document, **{field: invalid_value})
    elif model is RegistryRecord:
        instance = make_registry(**{field: invalid_value})
    elif model is VerificationResult:
        instance = make_verification(document, **{field: invalid_value})
    elif model is ReviewAction:
        instance = make_review(verification, **{field: invalid_value})
    else:
        instance = make_blockchain_record(
            verification, **{field: invalid_value}
        )

    db_session.add(instance)
    with pytest.raises((StatementError, IntegrityError, ValueError)):
        db_session.flush()

    db_session.rollback()


def test_document_required_fields_are_non_nullable():
    required = [
        "category",
        "original_filename",
        "storage_key",
        "sha256",
        "mime_type",
        "byte_size",
        "page_count",
        "processing_state",
        "uploaded_at",
    ]
    for field in required:
        assert Document.__table__.columns[field].nullable is False


def test_document_id_is_generated_as_32_character_hex(db_session):
    document = make_document()
    db_session.add(document)
    db_session.flush()

    assert document.id is not None
    assert len(document.id) == 32
    int(document.id, 16)


def test_document_category_accepts_documented_values(db_session):
    for index, category in enumerate(DocumentCategory):
        db_session.add(
            make_document(
                category=category,
                storage_key=f"uploads/{index}.pdf",
                sha256=str(index) * 64,
            )
        )

    db_session.flush()
    assert db_session.query(Document).count() == len(DocumentCategory)


def test_verification_registry_reference_is_nullable(db_session):
    document = make_document()
    verification = make_verification(document)

    db_session.add_all([document, verification])
    db_session.flush()

    assert verification.registry_record_id is None
    assert verification.registry_record is None


def test_verification_can_reference_registry_record(db_session):
    document = make_document()
    registry = make_registry()
    verification = make_verification(
        document,
        registry_record=registry,
    )

    db_session.add_all([document, registry, verification])
    db_session.flush()

    assert verification.registry_record_id == registry.id
    assert verification.registry_record is registry
    assert verification in registry.verifications


def test_document_extraction_relationships_both_directions(db_session):
    document = make_document()
    extraction = make_extraction(document)

    db_session.add(document)
    db_session.flush()

    assert extraction.document is document
    assert extraction in document.extractions


def test_document_verification_relationships_both_directions(db_session):
    document = make_document()
    verification = make_verification(document)

    db_session.add(document)
    db_session.flush()

    assert verification.document is document
    assert verification in document.verifications


def test_verification_self_reference_relationships(db_session):
    document = make_document()
    original = make_verification(document)
    corrected = make_verification(
        document,
        supersedes_verification=original,
        status=VerificationStatus.REVIEW_REQUIRED,
    )

    db_session.add_all([document, original, corrected])
    db_session.flush()

    assert corrected.supersedes_verification is original
    assert corrected.supersedes_verification_id == original.id
    assert corrected in original.superseded_by


def test_review_action_relationship(db_session):
    document = make_document()
    verification = make_verification(document)
    review = make_review(verification)

    db_session.add_all([document, verification, review])
    db_session.flush()

    assert review.verification is verification
    assert review in verification.review_actions


def test_blockchain_record_relationship(db_session):
    document = make_document()
    verification = make_verification(document)
    record = make_blockchain_record(verification)

    db_session.add_all([document, verification, record])
    db_session.flush()

    assert record.verification is verification
    assert record in verification.blockchain_records


def test_registry_category_and_key_are_unique(db_session):
    first = make_registry()
    second = make_registry()

    db_session.add(first)
    db_session.flush()

    db_session.add(second)
    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_missing_document_foreign_key_is_rejected(db_session):
    enable_sqlite_foreign_keys(db_session)

    extraction = ExtractionResult(
        document_id="missing-document",
        engine_name="test-engine",
        engine_version="1.0",
        raw_ocr_json="{}",
        extracted_fields_json="{}",
        warnings_json="[]",
        status=ExtractionStatus.SUCCEEDED,
        created_at=now(),
    )

    db_session.add(extraction)
    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_registry_foreign_key_can_be_null(db_session):
    document = make_document()
    verification = make_verification(document, registry_record_id=None)

    db_session.add_all([document, verification])
    db_session.flush()

    assert verification.registry_record_id is None


def test_model_relationships_are_configured():
    mapper = inspect(VerificationResult)
    assert "document" in mapper.relationships
    assert "registry_record" in mapper.relationships
    assert "supersedes_verification" in mapper.relationships
    assert "superseded_by" in mapper.relationships
    assert "review_actions" in mapper.relationships
    assert "blockchain_records" in mapper.relationships