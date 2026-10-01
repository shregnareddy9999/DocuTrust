"""Tests for AI Academic Summary feature."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO

import pytest
from PIL import Image

from app.adapters.ai.fake_adapter import create_fake_adapter
from app.models.document import Document, DocumentCategory, ProcessingState
from app.models.extraction import ExtractionResult, ExtractionStatus
from app.repositories import documents_repo, extraction_repo
from app.services.academic_summary_service import (
    DocumentNotAcademicError,
    DocumentNotFoundError,
    ExtractionNotReadyError,
    NoExtractedTextError,
    generate_academic_summary,
)


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 64), color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _ocr_dump(text: str) -> str:
    return json.dumps({
        "text": text,
        "regions": [],
        "warnings": [],
    })


def _seed_academic_document(db_session, extracted_text: str, category=DocumentCategory.ACADEMIC_CERTIFICATE):
    """Create a document with successful extraction containing the given text."""
    document = documents_repo.create(db_session, Document(
        category=category,
        original_filename="certificate.png",
        storage_key="uploads/certificate.png",
        sha256="a" * 64,
        mime_type="image/png",
        byte_size=2048,
        page_count=1,
        processing_state=ProcessingState.OCR_DONE,
        uploaded_at=datetime.now(timezone.utc).replace(tzinfo=None),
    ))
    extraction = ExtractionResult(
        document_id=document.id,
        engine_name="fake",
        engine_version="1.0",
        raw_ocr_json=_ocr_dump(extracted_text),
        extracted_fields_json="{}",
        warnings_json="[]",
        status=ExtractionStatus.SUCCEEDED,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    extraction_repo.create(db_session, extraction)
    db_session.commit()
    return document.id


def _seed_non_academic_document(db_session, category=DocumentCategory.INSTITUTIONAL_ID):
    """Create a non-academic document with successful extraction."""
    document = documents_repo.create(db_session, Document(
        category=category,
        original_filename="id_card.png",
        storage_key="uploads/id_card.png",
        sha256="b" * 64,
        mime_type="image/png",
        byte_size=2048,
        page_count=1,
        processing_state=ProcessingState.OCR_DONE,
        uploaded_at=datetime.now(timezone.utc).replace(tzinfo=None),
    ))
    extraction = ExtractionResult(
        document_id=document.id,
        engine_name="fake",
        engine_version="1.0",
        raw_ocr_json=_ocr_dump("Holder Name: Priya Demo\nInstitution: Example Institute\nID Number: DEMO-ID-001"),
        extracted_fields_json="{}",
        warnings_json="[]",
        status=ExtractionStatus.SUCCEEDED,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    extraction_repo.create(db_session, extraction)
    db_session.commit()
    return document.id


def test_generate_academic_summary_success(db_session, monkeypatch):
    """Test successful academic summary generation from multiple documents."""
    # Seed two academic documents
    doc1_id = _seed_academic_document(db_session, "Student Name: Aarav Demo\nCourse: B.Tech CSE\nSemester: 1\nMarks: 85%")
    doc2_id = _seed_academic_document(db_session, "Student Name: Aarav Demo\nCourse: B.Tech CSE\nSemester: 2\nMarks: 88%")

    # Use fake AI adapter
    fake_adapter = create_fake_adapter(mode="success", custom_summary="Test summary")
    monkeypatch.setattr("app.services.academic_summary_service.get_ai_adapter", lambda: fake_adapter)

    result = generate_academic_summary([doc1_id, doc2_id], db_session)

    assert result.summary == "Test summary"
    assert result.documents_analyzed == 2
    assert result.model == "fake-model"


def test_generate_academic_summary_single_document(db_session, monkeypatch):
    """Test academic summary generation from a single document."""
    doc_id = _seed_academic_document(db_session, "Student Name: Aarav Demo\nSemester: 1\nSubject: Data Structures\nMarks: 85%")

    fake_adapter = create_fake_adapter(mode="success", custom_summary="Single doc summary")
    monkeypatch.setattr("app.services.academic_summary_service.get_ai_adapter", lambda: fake_adapter)

    result = generate_academic_summary([doc_id], db_session)

    assert result.summary == "Single doc summary"
    assert result.documents_analyzed == 1


def test_generate_academic_summary_document_not_found(db_session):
    """Test error when document doesn't exist."""
    fake_adapter = create_fake_adapter(mode="success")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("app.services.academic_summary_service.get_ai_adapter", lambda: fake_adapter)

    with pytest.raises(DocumentNotFoundError):
        generate_academic_summary(["ffffffffffffffffffffffffffffffff"], db_session)


def test_generate_academic_summary_non_academic_document(db_session, monkeypatch):
    """Test error when document is not an academic certificate."""
    doc_id = _seed_non_academic_document(db_session)

    fake_adapter = create_fake_adapter(mode="success")
    monkeypatch.setattr("app.services.academic_summary_service.get_ai_adapter", lambda: fake_adapter)

    with pytest.raises(DocumentNotAcademicError):
        generate_academic_summary([doc_id], db_session)


def test_generate_academic_summary_mixed_documents(db_session, monkeypatch):
    """Test error when mixing academic and non-academic documents."""
    academic_id = _seed_academic_document(db_session, "Student Name: Aarav Demo")
    non_academic_id = _seed_non_academic_document(db_session)

    fake_adapter = create_fake_adapter(mode="success")
    monkeypatch.setattr("app.services.academic_summary_service.get_ai_adapter", lambda: fake_adapter)

    with pytest.raises(DocumentNotAcademicError):
        generate_academic_summary([academic_id, non_academic_id], db_session)


def test_generate_academic_summary_no_extraction(db_session, monkeypatch):
    """Test error when document has no successful extraction."""
    from app.models.document import Document, DocumentCategory, ProcessingState
    from app.repositories import documents_repo

    document = documents_repo.create(db_session, Document(
        category=DocumentCategory.ACADEMIC_CERTIFICATE,
        original_filename="certificate.png",
        storage_key="uploads/certificate.png",
        sha256="c" * 64,
        mime_type="image/png",
        byte_size=2048,
        page_count=1,
        processing_state=ProcessingState.OCR_DONE,
        uploaded_at=datetime.now(timezone.utc).replace(tzinfo=None),
    ))
    db_session.commit()

    fake_adapter = create_fake_adapter(mode="success")
    monkeypatch.setattr("app.services.academic_summary_service.get_ai_adapter", lambda: fake_adapter)

    with pytest.raises(ExtractionNotReadyError):
        generate_academic_summary([document.id], db_session)


def test_generate_academic_summary_empty_ocr_text(db_session, monkeypatch):
    """Test error when document has empty OCR text."""
    doc_id = _seed_academic_document(db_session, "")  # Empty text

    fake_adapter = create_fake_adapter(mode="success")
    monkeypatch.setattr("app.services.academic_summary_service.get_ai_adapter", lambda: fake_adapter)

    with pytest.raises(NoExtractedTextError):
        generate_academic_summary([doc_id], db_session)


def test_generate_academic_summary_empty_request(db_session, monkeypatch):
    """Test error when no document IDs provided."""
    fake_adapter = create_fake_adapter(mode="success")
    monkeypatch.setattr("app.services.academic_summary_service.get_ai_adapter", lambda: fake_adapter)

    with pytest.raises(ValueError, match="At least one document ID is required"):
        generate_academic_summary([], db_session)


# API endpoint tests
def _upload_academic(client):
    """Upload an academic certificate document."""
    return client.post(
        "/api/v1/documents",
        files={"file": ("sample.png", _png_bytes(), "image/png")},
        data={"category": "academic_certificate"},
    ).json()["document_id"]


def _upload_non_academic(client):
    """Upload a non-academic document."""
    return client.post(
        "/api/v1/documents",
        files={"file": ("sample.png", _png_bytes(), "image/png")},
        data={"category": "institutional_id"},
    ).json()["document_id"]


def _seed_registry_and_ocr(client, monkeypatch, document_id, ocr_text):
    """Seed registry and set up OCR for a document."""
    from app.db import SessionLocal
    from app.fixtures import seed_registry

    session = SessionLocal()
    try:
        seed_registry.seed(session)
        session.commit()
    finally:
        session.close()

    # Configure OCR to return specific text
    from app.adapters.ocr.fake_adapter import create_fake_adapter as create_fake_ocr_adapter
    adapter = create_fake_ocr_adapter(mode="clean", custom_text=ocr_text)
    monkeypatch.setattr("app.services.ocr_service.get_ocr_adapter", lambda: adapter)


def test_academic_summary_api_success(client, monkeypatch):
    """Test successful academic summary API call."""
    doc1_id = _upload_academic(client)
    doc2_id = _upload_academic(client)

    _seed_registry_and_ocr(client, monkeypatch, doc1_id, "Student Name: Aarav Demo\nSemester: 1\nCourse: B.Tech CSE")
    _seed_registry_and_ocr(client, monkeypatch, doc2_id, "Student Name: Aarav Demo\nSemester: 2\nCourse: B.Tech CSE")

    # Run verification to create extractions
    client.post(f"/api/v1/documents/{doc1_id}/verify")
    client.post(f"/api/v1/documents/{doc2_id}/verify")

    from app.adapters.ai.fake_adapter import create_fake_adapter as create_fake_ai_adapter
    fake_adapter = create_fake_ai_adapter(mode="success", custom_summary="API test summary")
    monkeypatch.setattr("app.services.academic_summary_service.get_ai_adapter", lambda: fake_adapter)

    response = client.post(
        "/api/v1/academic-summary",
        json={"document_ids": [doc1_id, doc2_id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == "API test summary"
    assert body["documents_analyzed"] == 2
    assert body["model"] == "fake-model"


def test_academic_summary_api_document_not_found(client, monkeypatch):
    """Test API error for non-existent document."""
    from app.adapters.ai.fake_adapter import create_fake_adapter as create_fake_ai_adapter
    fake_adapter = create_fake_ai_adapter(mode="success")
    monkeypatch.setattr("app.adapters.ai.get_ai_adapter", lambda: fake_adapter)

    response = client.post(
        "/api/v1/academic-summary",
        json={"document_ids": ["ffffffffffffffffffffffffffffffff"]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_academic_summary_api_non_academic_document(client, monkeypatch):
    """Test API error for non-academic document."""
    doc_id = _upload_non_academic(client)

    from app.db import SessionLocal
    from app.fixtures import seed_registry
    from app.adapters.ocr.fake_adapter import create_fake_adapter as create_fake_ocr_adapter

    session = SessionLocal()
    try:
        seed_registry.seed(session)
        session.commit()
    finally:
        session.close()

    adapter = create_fake_ocr_adapter(mode="clean", custom_text="Holder Name: Priya Demo\nInstitution: Example\nID: DEMO-ID-001")
    monkeypatch.setattr("app.services.ocr_service.get_ocr_adapter", lambda: adapter)

    from app.adapters.ai.fake_adapter import create_fake_adapter as create_fake_ai_adapter
    fake_adapter = create_fake_ai_adapter(mode="success")
    monkeypatch.setattr("app.adapters.ai.get_ai_adapter", lambda: fake_adapter)

    # Run verification to create extraction
    client.post(f"/api/v1/documents/{doc_id}/verify")

    response = client.post(
        "/api/v1/academic-summary",
        json={"document_ids": [doc_id]},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_DOCUMENT_TYPE"


def test_academic_summary_api_runs_ocr_when_extraction_is_missing(client, monkeypatch):
    """Test API runs OCR on demand when extraction is missing."""
    doc_id = _upload_academic(client)

    from app.adapters.ai.fake_adapter import create_fake_adapter as create_fake_ai_adapter
    fake_adapter = create_fake_ai_adapter(mode="success", custom_summary="OCR on demand summary")
    monkeypatch.setattr("app.services.academic_summary_service.get_ai_adapter", lambda: fake_adapter)

    response = client.post(
        "/api/v1/academic-summary",
        json={"document_ids": [doc_id]},
    )

    assert response.status_code == 200
    assert response.json()["summary"] == "OCR on demand summary"


def test_academic_summary_api_empty_document_ids(client):
    """Test API error for empty document_ids list."""
    response = client.post(
        "/api/v1/academic-summary",
        json={"document_ids": []},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_academic_summary_api_ai_connection_error(client, monkeypatch):
    """Test API response when AI adapter returns connection error."""
    doc_id = _upload_academic(client)

    from app.db import SessionLocal
    from app.fixtures import seed_registry
    from app.adapters.ocr.fake_adapter import create_fake_adapter as create_fake_ocr_adapter

    session = SessionLocal()
    try:
        seed_registry.seed(session)
        session.commit()
    finally:
        session.close()

    adapter = create_fake_ocr_adapter(mode="clean", custom_text="Student Name: Aarav Demo\nSemester: 1")
    monkeypatch.setattr("app.services.ocr_service.get_ocr_adapter", lambda: adapter)

    # Run verification to create extraction
    client.post(f"/api/v1/documents/{doc_id}/verify")

    # Use AI adapter that simulates connection error
    from app.adapters.ai.fake_adapter import create_fake_adapter as create_fake_ai_adapter
    fake_adapter = create_fake_ai_adapter(mode="connection_error")
    monkeypatch.setattr("app.services.academic_summary_service.get_ai_adapter", lambda: fake_adapter)

    response = client.post(
        "/api/v1/academic-summary",
        json={"document_ids": [doc_id]},
    )

    assert response.status_code == 200  # Still 200, but summary contains error message
    body = response.json()
    assert "Could not connect" in body["summary"]
    assert body["documents_analyzed"] == 1
