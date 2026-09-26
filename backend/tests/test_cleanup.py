"""Tests for Task 12 retention cleanup."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from app.fixtures.cleanup_expired import cleanup_expired
from app.models.document import Document, DocumentCategory, ProcessingState
from app.models.extraction import ExtractionResult, ExtractionStatus


def _create_document(
    db_session,
    *,
    uploaded_at: datetime,
    storage_key: str,
) -> Document:
    """Create a minimal valid document for cleanup tests."""
    document = Document(
        id=f"doc-{storage_key.replace('.', '-').replace('/', '-')}",
        category=DocumentCategory.ACADEMIC_CERTIFICATE,
        original_filename="demo.pdf",
        storage_key=storage_key,
        sha256="a" * 64,
        mime_type="application/pdf",
        byte_size=100,
        page_count=1,
        processing_state=ProcessingState.OCR_DONE,
        uploaded_at=uploaded_at,
    )

    db_session.add(document)
    db_session.commit()

    return document


def _create_extraction(
    db_session,
    *,
    document_id: str,
    raw_ocr: str = '{"text":"raw OCR"}',
    extracted_fields: str = '{"student_id":"DEMO-STU-001"}',
) -> ExtractionResult:
    """Create a valid extraction result."""
    extraction = ExtractionResult(
        document_id=document_id,
        engine_name="fake",
        engine_version="1.0",
        raw_ocr_json=raw_ocr,
        extracted_fields_json=extracted_fields,
        warnings_json=json.dumps([]),
        status=ExtractionStatus.SUCCEEDED,
        created_at=datetime.utcnow(),
    )

    db_session.add(extraction)
    db_session.commit()

    return extraction


def test_dry_run_does_not_delete_file_or_modify_raw_ocr(
    db_session,
    temp_upload_dir: Path,
    monkeypatch,
    test_settings,
):
    """Default cleanup mode reports work without changing data."""
    import app.services.upload_service as upload_service

    monkeypatch.setattr(upload_service, "settings", test_settings)

    storage_key = "cleanup-dry-run.pdf"
    upload_file = temp_upload_dir / storage_key
    upload_file.write_bytes(b"demo document")

    document = _create_document(
        db_session,
        uploaded_at=datetime.utcnow() - timedelta(days=10),
        storage_key=storage_key,
    )

    extraction = _create_extraction(
        db_session,
        document_id=document.id,
    )

    summary = cleanup_expired(
        db_session,
        retention_days=7,
        delete=False,
    )

    assert summary.expired_documents == 1
    assert summary.files_deleted == 1
    assert summary.raw_ocr_cleared == 1

    assert upload_file.exists()

    db_session.refresh(extraction)
    assert extraction.raw_ocr_json == '{"text":"raw OCR"}'
    assert extraction.extracted_fields_json == '{"student_id":"DEMO-STU-001"}'


def test_delete_mode_removes_expired_file_and_blanks_raw_ocr(
    db_session,
    temp_upload_dir: Path,
    monkeypatch,
    test_settings,
):
    """Delete mode removes the upload and blanks only raw OCR."""
    import app.services.upload_service as upload_service

    monkeypatch.setattr(upload_service, "settings", test_settings)

    storage_key = "cleanup-delete.pdf"
    upload_file = temp_upload_dir / storage_key
    upload_file.write_bytes(b"demo document")

    document = _create_document(
        db_session,
        uploaded_at=datetime.utcnow() - timedelta(days=10),
        storage_key=storage_key,
    )

    extraction = _create_extraction(
        db_session,
        document_id=document.id,
    )

    summary = cleanup_expired(
        db_session,
        retention_days=7,
        delete=True,
    )

    assert summary.expired_documents == 1
    assert summary.files_deleted == 1
    assert summary.files_missing == 0
    assert summary.raw_ocr_cleared == 1

    assert not upload_file.exists()

    db_session.refresh(extraction)

    assert extraction.raw_ocr_json == ""
    assert extraction.extracted_fields_json == '{"student_id":"DEMO-STU-001"}'


def test_recent_document_is_not_cleaned(
    db_session,
    temp_upload_dir: Path,
    monkeypatch,
    test_settings,
):
    """Documents newer than the retention period remain untouched."""
    import app.services.upload_service as upload_service

    monkeypatch.setattr(upload_service, "settings", test_settings)

    storage_key = "recent-document.pdf"
    upload_file = temp_upload_dir / storage_key
    upload_file.write_bytes(b"recent document")

    document = _create_document(
        db_session,
        uploaded_at=datetime.utcnow() - timedelta(days=2),
        storage_key=storage_key,
    )

    extraction = _create_extraction(
        db_session,
        document_id=document.id,
    )

    summary = cleanup_expired(
        db_session,
        retention_days=7,
        delete=True,
    )

    assert summary.expired_documents == 0
    assert summary.files_deleted == 0
    assert summary.raw_ocr_cleared == 0

    assert upload_file.exists()

    db_session.refresh(document)
    db_session.refresh(extraction)

    assert document.storage_key == storage_key
    assert extraction.raw_ocr_json == '{"text":"raw OCR"}'
    assert extraction.extracted_fields_json == '{"student_id":"DEMO-STU-001"}'


def test_expired_document_row_is_preserved(
    db_session,
    temp_upload_dir: Path,
    monkeypatch,
    test_settings,
):
    """Retention cleanup does not delete the Document database row."""
    import app.services.upload_service as upload_service

    monkeypatch.setattr(upload_service, "settings", test_settings)

    storage_key = "preserve-document-row.pdf"
    upload_file = temp_upload_dir / storage_key
    upload_file.write_bytes(b"demo document")

    document = _create_document(
        db_session,
        uploaded_at=datetime.utcnow() - timedelta(days=10),
        storage_key=storage_key,
    )

    _create_extraction(
        db_session,
        document_id=document.id,
    )

    cleanup_expired(
        db_session,
        retention_days=7,
        delete=True,
    )

    preserved_document = db_session.get(Document, document.id)

    assert preserved_document is not None
    assert preserved_document.id == document.id
    assert preserved_document.storage_key == storage_key


def test_missing_uploaded_file_does_not_fail_cleanup(
    db_session,
    temp_upload_dir: Path,
    monkeypatch,
    test_settings,
):
    """Cleanup handles an already-missing upload file safely."""
    import app.services.upload_service as upload_service

    monkeypatch.setattr(upload_service, "settings", test_settings)

    storage_key = "already-missing.pdf"

    document = _create_document(
        db_session,
        uploaded_at=datetime.utcnow() - timedelta(days=10),
        storage_key=storage_key,
    )

    extraction = _create_extraction(
        db_session,
        document_id=document.id,
    )

    summary = cleanup_expired(
        db_session,
        retention_days=7,
        delete=True,
    )

    assert summary.expired_documents == 1
    assert summary.files_deleted == 0
    assert summary.files_missing == 1
    assert summary.raw_ocr_cleared == 1

    db_session.refresh(extraction)

    assert extraction.raw_ocr_json == ""
    assert extraction.extracted_fields_json == '{"student_id":"DEMO-STU-001"}'


def test_retention_days_can_be_overridden(
    db_session,
    temp_upload_dir: Path,
    monkeypatch,
    test_settings,
):
    """The cleanup function respects an explicit retention period."""
    import app.services.upload_service as upload_service

    monkeypatch.setattr(upload_service, "settings", test_settings)

    storage_key = "custom-retention.pdf"
    upload_file = temp_upload_dir / storage_key
    upload_file.write_bytes(b"demo document")

    document = _create_document(
        db_session,
        uploaded_at=datetime.utcnow() - timedelta(days=5),
        storage_key=storage_key,
    )

    _create_extraction(
        db_session,
        document_id=document.id,
    )

    summary = cleanup_expired(
        db_session,
        retention_days=3,
        delete=True,
    )

    assert summary.expired_documents == 1
    assert not upload_file.exists()