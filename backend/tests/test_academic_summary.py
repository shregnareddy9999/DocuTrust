"""Tests for AI academic summary generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO

import app.db as app_db
import app.adapters.ai as ai_adapters
from app.adapters.ai.fake_adapter import FakeAcademicSummaryAdapter
from app.models.document import Document, DocumentCategory, ProcessingState
from app.models.extraction import ExtractionResult, ExtractionStatus
from PIL import Image


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 64), color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _create_document(
    category: DocumentCategory = DocumentCategory.ACADEMIC_CERTIFICATE,
    raw_text: str = "Student Name: Aarav Demo\nSemester / Year: 1\nCourse: B.Tech Computer Science and Engineering",
) -> str:
    session = app_db.SessionLocal()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        document = Document(
            category=category,
            original_filename="academic-summary-demo.png",
            storage_key="academic-summary-demo.png",
            sha256="0" * 64,
            mime_type="image/png",
            byte_size=1234,
            page_count=1,
            processing_state=ProcessingState.OCR_DONE,
            uploaded_at=now,
        )
        session.add(document)
        session.flush()
        extraction = ExtractionResult(
            document_id=document.id,
            engine_name="fake",
            engine_version="0.0.0-test",
            raw_ocr_json=json.dumps({"text": raw_text, "regions": [], "warnings": []}),
            extracted_fields_json=json.dumps(
                {
                    "student_name": {
                        "value": "Aarav Demo",
                        "confidence": 0.95,
                        "source": "ocr",
                    }
                }
            ),
            warnings_json="[]",
            status=ExtractionStatus.SUCCEEDED,
            created_at=now,
        )
        session.add(extraction)
        session.commit()
        return document.id
    finally:
        session.close()


def test_academic_summary_success(client, monkeypatch):
    fake = FakeAcademicSummaryAdapter(
        summary="Aarav Demo has submitted synthetic academic documents for semester 1.",
        model="llama3.2:latest",
    )
    monkeypatch.setattr(ai_adapters, "get_academic_summary_adapter", lambda: fake)
    document_id = _create_document()

    response = client.post(
        "/api/v1/academic-summary",
        json={"document_ids": [document_id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "summary": "Aarav Demo has submitted synthetic academic documents for semester 1.",
        "documents_analyzed": 1,
        "model": "llama3.2:latest",
    }
    assert "Use only the supplied OCR/extracted text" in fake.prompts[0]
    assert "Aarav Demo" in fake.prompts[0]


def test_academic_summary_multiple_documents_uses_compact_comparison_prompt(client, monkeypatch):
    fake = FakeAcademicSummaryAdapter(
        summary="Document 1 and Document 2 both describe synthetic academic records, with different semester details.",
        model="llama3.2:latest",
    )
    monkeypatch.setattr(ai_adapters, "get_academic_summary_adapter", lambda: fake)
    first_id = _create_document(
        raw_text=(
            "Student Name: Aarav Demo\n"
            "Semester / Year: 1\n"
            "Course: B.Tech Computer Science and Engineering\n"
            + ("Repeated OCR filler. " * 200)
        )
    )
    second_id = _create_document(
        raw_text=(
            "Student Name: Aarav Demo\n"
            "Semester / Year: 2\n"
            "Course: B.Tech Computer Science and Engineering\n"
            + ("Second repeated OCR filler. " * 200)
        )
    )

    response = client.post(
        "/api/v1/academic-summary",
        json={"document_ids": [first_id, second_id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["documents_analyzed"] == 2
    prompt = fake.prompts[0]
    assert "Task: multi-document comparison" in prompt
    assert "Document 1" in prompt
    assert "Document 2" in prompt
    assert "student_name (ocr): Aarav Demo" in prompt
    assert "ocr_excerpt:" in prompt
    assert len(prompt) < 4000


def test_academic_summary_processes_uploaded_document_once(client, monkeypatch):
    fake = FakeAcademicSummaryAdapter(summary="One uploaded academic document was summarized.")
    monkeypatch.setattr(ai_adapters, "get_academic_summary_adapter", lambda: fake)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("summary.png", _png_bytes(), "image/png")},
        data={"category": "academic_certificate"},
    )
    assert response.status_code == 201
    document_id = response.json()["document_id"]

    first = client.post("/api/v1/academic-summary", json={"document_ids": [document_id]})
    second = client.post("/api/v1/academic-summary", json={"document_ids": [document_id]})

    assert first.status_code == 200
    assert second.status_code == 200
    session = app_db.SessionLocal()
    try:
        rows = session.query(ExtractionResult).filter_by(document_id=document_id).all()
        assert len(rows) == 1
        assert rows[0].status == ExtractionStatus.SUCCEEDED
    finally:
        session.close()


def test_academic_summary_missing_document_404(client, monkeypatch):
    monkeypatch.setattr(
        ai_adapters,
        "get_academic_summary_adapter",
        lambda: FakeAcademicSummaryAdapter(),
    )

    response = client.post(
        "/api/v1/academic-summary",
        json={"document_ids": ["ffffffffffffffffffffffffffffffff"]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_academic_summary_rejects_non_academic_document(client, monkeypatch):
    monkeypatch.setattr(
        ai_adapters,
        "get_academic_summary_adapter",
        lambda: FakeAcademicSummaryAdapter(),
    )
    document_id = _create_document(category=DocumentCategory.INSTITUTIONAL_ID)

    response = client.post(
        "/api/v1/academic-summary",
        json={"document_ids": [document_id]},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "NON_ACADEMIC_DOCUMENT"


def test_academic_summary_requires_successful_extraction(client, monkeypatch):
    monkeypatch.setattr(
        ai_adapters,
        "get_academic_summary_adapter",
        lambda: FakeAcademicSummaryAdapter(),
    )
    session = app_db.SessionLocal()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        document = Document(
            category=DocumentCategory.ACADEMIC_CERTIFICATE,
            original_filename="not-processed.png",
            storage_key="not-processed.png",
            sha256="1" * 64,
            mime_type="image/png",
            byte_size=1234,
            page_count=1,
            processing_state=ProcessingState.UPLOADED,
            uploaded_at=now,
        )
        session.add(document)
        session.commit()
        document_id = document.id
    finally:
        session.close()

    response = client.post(
        "/api/v1/academic-summary",
        json={"document_ids": [document_id]},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EXTRACTION_NOT_READY"


def test_academic_summary_ai_failure(client, monkeypatch):
    monkeypatch.setattr(
        ai_adapters,
        "get_academic_summary_adapter",
        lambda: FakeAcademicSummaryAdapter(should_fail=True),
    )
    document_id = _create_document()

    response = client.post(
        "/api/v1/academic-summary",
        json={"document_ids": [document_id]},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_SUMMARY_UNAVAILABLE"
