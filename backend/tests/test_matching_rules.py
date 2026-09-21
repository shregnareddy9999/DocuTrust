"""Tests for Task 07 matching, rules, precedence, and verify endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

import app.models  # noqa: F401 — register tables for db_session.create_all

from app.domain.matching import find_applicable_record
from app.domain.normalization import normalize_date, normalize_for_comparison, normalize_text
from app.domain.rules import (
    date_consistency,
    evaluate,
)
from app.domain.schemas import get_schema
from app.domain.status import RecordingStatus, VerificationStatus
from app.fixtures.fixture_data import FIXTURES


ACADEMIC = "academic_certificate"
THRESHOLD = 0.70


def _entry(value, confidence=0.95, source="ocr"):
    return {"value": value, "confidence": confidence, "source": source}


def academic_fields(**overrides):
    base = {
        "student_name": _entry("Aarav Demo"),
        "institution_name": _entry("Example Technical Institute"),
        "student_id": _entry("DEMO-STU-001"),
        "course_name": _entry("B.Tech CSE"),
        "semester_or_year": _entry("5"),
        "certificate_or_marksheet_id": _entry("DEMO-MARK-001"),
        "issue_date": _entry(None, None),
    }
    for key, value in overrides.items():
        if isinstance(value, dict):
            base[key] = value
        else:
            base[key] = _entry(value)
    return base


def academic_candidate(record_id="reg-1", **field_overrides):
    fields = dict(FIXTURES[ACADEMIC]["fields"])
    fields.update(field_overrides)
    return {
        "id": record_id,
        "category": ACADEMIC,
        "active": True,
        "synthetic_record_key": fields.get("student_id", "DEMO-STU-001"),
        "fields": fields,
    }


def _serialize_outcome(outcome):
    return json.dumps(
        {
            "status": outcome.status.value,
            "comparisons": outcome.field_comparisons,
            "rules": [
                {"rule_id": r.rule_id, "passed": r.passed, "reason": r.reason}
                for r in outcome.rule_results
            ],
            "reason_codes": outcome.reason_codes,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


# --- Normalization ---


def test_normalize_text_whitespace_and_case():
    assert normalize_text("  Aarav   Demo ") == normalize_text("aarav demo")


def test_identifier_hyphens_and_letters_preserved():
    original, normalized = normalize_for_comparison("DEMO-STU-001", "text")
    assert original == "DEMO-STU-001"
    assert "-" in original
    assert "STU" in original
    assert normalize_text("DEMO-STU-001") == "demo-stu-001"


def test_letter_o_does_not_normalize_to_zero():
    _, oh = normalize_for_comparison("DEMO-STU-OO1", "text")
    _, zero = normalize_for_comparison("DEMO-STU-001", "text")
    assert oh != zero


def test_invalid_date_format_excluded():
    assert normalize_date("15-01-1999") is None
    original, normalized = normalize_for_comparison("15-01-1999", "date")
    assert original == "15-01-1999"
    assert normalized is None


def test_valid_iso_date_normalizes():
    assert normalize_date("1999-01-15") == "1999-01-15"


# --- Matching ---


def test_full_match_returns_record():
    extracted = academic_fields()
    result = find_applicable_record(
        ACADEMIC,
        extracted,
        [academic_candidate()],
        get_schema(ACADEMIC),
    )
    assert result.is_full_match is True
    assert result.record["synthetic_record_key"] == "DEMO-STU-001"
    assert all(row["matched"] for row in result.comparisons)
    assert len(result.comparisons) == 6


def test_identifying_key_mismatch_is_applicable_reference():
    extracted = academic_fields(semester_or_year="6")
    result = find_applicable_record(
        ACADEMIC,
        extracted,
        [academic_candidate()],
        get_schema(ACADEMIC),
    )
    assert result.is_full_match is False
    assert result.is_applicable_reference is True
    semester = next(row for row in result.comparisons if row["field"] == "semester_or_year")
    assert semester["matched"] is False
    assert semester["extracted_value"] == "6"
    assert semester["registry_value"] == "5"


def test_no_identifying_key_means_no_applicable_record():
    extracted = academic_fields(student_id="DEMO-STU-999")
    result = find_applicable_record(
        ACADEMIC,
        extracted,
        [academic_candidate()],
        get_schema(ACADEMIC),
    )
    assert result.record is None
    assert result.is_applicable_reference is False
    assert result.registry_data_error is False


def test_inactive_record_is_not_a_candidate():
    extracted = academic_fields()
    inactive = academic_candidate()
    inactive["active"] = False
    result = find_applicable_record(
        ACADEMIC,
        extracted,
        [inactive],
        get_schema(ACADEMIC),
    )
    assert result.record is None


def test_duplicate_full_matches_flag_registry_data_error():
    extracted = academic_fields()
    result = find_applicable_record(
        ACADEMIC,
        extracted,
        [academic_candidate("reg-a"), academic_candidate("reg-b")],
        get_schema(ACADEMIC),
    )
    assert result.registry_data_error is True
    assert result.is_full_match is False


def test_candidate_order_does_not_change_result():
    extracted = academic_fields(semester_or_year="6")
    extra = academic_candidate("reg-other", student_id="DEMO-STU-002", semester_or_year="6")
    extra["synthetic_record_key"] = "DEMO-STU-002"
    schema = get_schema(ACADEMIC)
    first = find_applicable_record(
        ACADEMIC,
        extracted,
        [extra, academic_candidate("reg-1")],
        schema,
    )
    second = find_applicable_record(
        ACADEMIC,
        extracted,
        [academic_candidate("reg-1"), extra],
        schema,
    )
    assert first.record["id"] == second.record["id"]
    assert first.comparisons == second.comparisons


# --- Statuses and precedence ---


def test_verified_match_status():
    extracted = academic_fields()
    match = find_applicable_record(
        ACADEMIC, extracted, [academic_candidate()], get_schema(ACADEMIC)
    )
    outcome = evaluate("SUCCEEDED", extracted, match, get_schema(ACADEMIC), THRESHOLD)
    assert outcome.status is VerificationStatus.VERIFIED_MATCH
    assert all(row["matched"] for row in outcome.field_comparisons)
    assert len(outcome.rule_results) == 5


def test_integrity_mismatch_names_field():
    extracted = academic_fields(semester_or_year="6")
    match = find_applicable_record(
        ACADEMIC, extracted, [academic_candidate()], get_schema(ACADEMIC)
    )
    outcome = evaluate("SUCCEEDED", extracted, match, get_schema(ACADEMIC), THRESHOLD)
    assert outcome.status is VerificationStatus.INTEGRITY_MISMATCH
    assert "FIELD_MISMATCH:semester_or_year" in outcome.reason_codes
    semester = next(
        row for row in outcome.field_comparisons if row["field"] == "semester_or_year"
    )
    assert semester["extracted_value"] == "6"
    assert semester["registry_value"] == "5"


def test_no_trusted_record_status():
    extracted = academic_fields(student_id="DEMO-STU-999")
    match = find_applicable_record(
        ACADEMIC, extracted, [academic_candidate()], get_schema(ACADEMIC)
    )
    outcome = evaluate("SUCCEEDED", extracted, match, get_schema(ACADEMIC), THRESHOLD)
    assert outcome.status is VerificationStatus.NO_TRUSTED_RECORD
    assert "NO_TRUSTED_RECORD" in outcome.reason_codes


def test_review_required_missing_required_field():
    extracted = academic_fields(student_name=_entry(None, None))
    match = find_applicable_record(
        ACADEMIC, extracted, [academic_candidate()], get_schema(ACADEMIC)
    )
    outcome = evaluate("SUCCEEDED", extracted, match, get_schema(ACADEMIC), THRESHOLD)
    assert outcome.status is VerificationStatus.REVIEW_REQUIRED
    assert "MISSING_REQUIRED:student_name" in outcome.reason_codes


def test_review_required_low_confidence():
    extracted = academic_fields(student_id=_entry("DEMO-STU-001", 0.69))
    match = find_applicable_record(
        ACADEMIC, extracted, [academic_candidate()], get_schema(ACADEMIC)
    )
    outcome = evaluate("SUCCEEDED", extracted, match, get_schema(ACADEMIC), THRESHOLD)
    assert outcome.status is VerificationStatus.REVIEW_REQUIRED
    assert "LOW_CONFIDENCE:student_id" in outcome.reason_codes


def test_processing_failed_via_failed_extraction():
    extracted = academic_fields(semester_or_year="6")
    match = find_applicable_record(
        ACADEMIC, extracted, [academic_candidate()], get_schema(ACADEMIC)
    )
    outcome = evaluate("FAILED", extracted, match, get_schema(ACADEMIC), THRESHOLD)
    assert outcome.status is VerificationStatus.PROCESSING_FAILED
    assert outcome.reason_codes == ["EXTRACTION_FAILED"]


def test_failed_extraction_wins_over_mismatch():
    extracted = academic_fields(semester_or_year="6")
    match = find_applicable_record(
        ACADEMIC, extracted, [academic_candidate()], get_schema(ACADEMIC)
    )
    outcome = evaluate("FAILED", extracted, match, get_schema(ACADEMIC), THRESHOLD)
    assert outcome.status is VerificationStatus.PROCESSING_FAILED
    assert outcome.status is not VerificationStatus.INTEGRITY_MISMATCH


def test_missing_required_beats_no_record():
    extracted = academic_fields(
        student_name=_entry(None, None),
        student_id="DEMO-STU-999",
    )
    match = find_applicable_record(
        ACADEMIC, extracted, [academic_candidate()], get_schema(ACADEMIC)
    )
    outcome = evaluate("SUCCEEDED", extracted, match, get_schema(ACADEMIC), THRESHOLD)
    assert outcome.status is VerificationStatus.REVIEW_REQUIRED
    assert outcome.status is not VerificationStatus.NO_TRUSTED_RECORD


def test_low_confidence_beats_verified_match():
    extracted = academic_fields(course_name=_entry("B.Tech CSE", 0.50))
    match = find_applicable_record(
        ACADEMIC, extracted, [academic_candidate()], get_schema(ACADEMIC)
    )
    outcome = evaluate("SUCCEEDED", extracted, match, get_schema(ACADEMIC), THRESHOLD)
    assert outcome.status is VerificationStatus.REVIEW_REQUIRED
    assert outcome.status is not VerificationStatus.VERIFIED_MATCH


def test_duplicate_matches_are_processing_failed_not_mismatch():
    extracted = academic_fields()
    match = find_applicable_record(
        ACADEMIC,
        extracted,
        [academic_candidate("a"), academic_candidate("b")],
        get_schema(ACADEMIC),
    )
    outcome = evaluate("SUCCEEDED", extracted, match, get_schema(ACADEMIC), THRESHOLD)
    assert outcome.status is VerificationStatus.PROCESSING_FAILED
    assert outcome.reason_codes == ["REGISTRY_DATA_ERROR"]
    assert outcome.status is not VerificationStatus.INTEGRITY_MISMATCH


def test_date_consistency_is_noop_pass():
    result = date_consistency({}, None, get_schema(ACADEMIC))
    assert result.passed is True
    assert result.rule_id == "date_consistency"


def test_evaluate_always_returns_five_rules():
    extracted = academic_fields()
    match = find_applicable_record(
        ACADEMIC, extracted, [academic_candidate()], get_schema(ACADEMIC)
    )
    outcome = evaluate("SUCCEEDED", extracted, match, get_schema(ACADEMIC), THRESHOLD)
    assert [r.rule_id for r in outcome.rule_results] == [
        "required_field_presence",
        "field_match",
        "category_schema_validity",
        "date_consistency",
        "known_fixture_duplicate",
    ]


def test_no_scores_on_rule_results():
    extracted = academic_fields()
    match = find_applicable_record(
        ACADEMIC, extracted, [academic_candidate()], get_schema(ACADEMIC)
    )
    outcome = evaluate("SUCCEEDED", extracted, match, get_schema(ACADEMIC), THRESHOLD)
    for result in outcome.rule_results:
        assert set(result.__dataclass_fields__) == {"rule_id", "passed", "reason"}
        assert isinstance(result.passed, bool)
        assert isinstance(result.reason, str)
        assert not isinstance(result.reason, (int, float))
        for name, value in vars(result).items():
            if name == "passed":
                continue
            assert not isinstance(value, (int, float))


def test_determinism_one_hundred_runs():
    extracted = academic_fields(semester_or_year="6")
    schema = get_schema(ACADEMIC)
    match = find_applicable_record(ACADEMIC, extracted, [academic_candidate()], schema)
    first = _serialize_outcome(evaluate("SUCCEEDED", extracted, match, schema, THRESHOLD))
    for _ in range(99):
        again = find_applicable_record(
            ACADEMIC, extracted, [academic_candidate()], schema
        )
        serialized = _serialize_outcome(
            evaluate("SUCCEEDED", extracted, again, schema, THRESHOLD)
        )
        assert serialized == first


def test_domain_matching_and_rules_are_pure():
    root = Path(__file__).resolve().parents[1] / "app" / "domain"
    forbidden = ("fastapi", "sqlalchemy", "paddleocr", "web3")
    for name in ("matching.py", "rules.py"):
        source = (root / name).read_text(encoding="utf-8")
        lowered = source.lower()
        for token in forbidden:
            assert f"import {token}" not in lowered
            assert f"from {token}" not in lowered


def test_recording_status_enum_exists():
    assert {item.value for item in RecordingStatus} == {
        "NOT_REQUESTED",
        "PENDING",
        "CONFIRMED",
        "FAILED",
    }


# --- Persistence and API ---


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_document(session, **overrides):
    from app.models.document import Document, DocumentCategory, ProcessingState
    from app.repositories import documents_repo

    values = {
        "category": DocumentCategory.ACADEMIC_CERTIFICATE,
        "original_filename": "academic_certificate_match.png",
        "storage_key": "uploads/academic_certificate_match.png",
        "sha256": "d" * 64,
        "mime_type": "image/png",
        "byte_size": 2048,
        "page_count": 1,
        "processing_state": ProcessingState.OCR_DONE,
        "uploaded_at": _now(),
    }
    values.update(overrides)
    return documents_repo.create(session, Document(**values))


def _ocr_dump_from_fields(fields: dict, confidence: float = 0.95) -> str:
    regions = []
    y = 80
    labels = {
        "student_name": "Student Name",
        "institution_name": "Institution Name",
        "student_id": "Student ID",
        "course_name": "Course Name",
        "semester_or_year": "Semester",
        "certificate_or_marksheet_id": "Certificate ID",
        "issue_date": "Issue Date",
    }
    for name, label in labels.items():
        entry = fields.get(name) or {}
        value = entry.get("value")
        if value is None:
            continue
        conf = entry.get("confidence")
        if conf is None:
            conf = confidence
        regions.append(
            {
                "text": f"{label}: {value}",
                "confidence": conf,
                "bbox": [60, y, 700, y + 20],
                "page": 1,
            }
        )
        y += 55
    return json.dumps({"text": " ".join(r["text"] for r in regions), "regions": regions, "warnings": []})


def _make_extraction(session, document, fields, status=None):
    from app.models.extraction import ExtractionResult, ExtractionStatus
    from app.repositories import extraction_repo

    row = ExtractionResult(
        document_id=document.id,
        engine_name="fake",
        engine_version="1.0",
        raw_ocr_json=_ocr_dump_from_fields(fields),
        extracted_fields_json=json.dumps(fields),
        warnings_json="[]",
        status=status or ExtractionStatus.SUCCEEDED,
        created_at=_now(),
    )
    return extraction_repo.create(session, row)


def test_registry_error_is_not_no_trusted_record(db_session, monkeypatch):
    from app.fixtures import seed_registry
    from app.models.extraction import ExtractionStatus
    from app.services.verification_service import verify_document
    import app.repositories.registry_repo as registry_mod

    seed_registry.seed(db_session)
    document = _make_document(db_session)
    _make_extraction(db_session, document, academic_fields())
    db_session.commit()

    def _boom(*args, **kwargs):
        raise RuntimeError("database stopped")

    monkeypatch.setattr(registry_mod, "list_active_by_category", _boom)
    row = verify_document(document.id, db_session)
    assert row.status.value == VerificationStatus.PROCESSING_FAILED.value
    assert json.loads(row.reason_codes_json) == ["REGISTRY_ERROR"]
    assert row.status.value != VerificationStatus.NO_TRUSTED_RECORD.value


def test_failed_extraction_persists_processing_failed(db_session):
    from app.models.document import ProcessingState
    from app.models.extraction import ExtractionStatus
    from app.services.verification_service import verify_document

    document = _make_document(db_session, processing_state=ProcessingState.OCR_FAILED)
    _make_extraction(
        db_session,
        document,
        academic_fields(semester_or_year="6"),
        status=ExtractionStatus.FAILED,
    )
    db_session.commit()
    row = verify_document(document.id, db_session)
    assert row.status.value == VerificationStatus.PROCESSING_FAILED.value
    assert json.loads(row.reason_codes_json) == ["EXTRACTION_FAILED"]
    assert row.supersedes_verification_id is None


def _seed_client_document(fields, processing_state=None, extraction_status=None, filename="match.png"):
    from app.db import SessionLocal
    from app.fixtures import seed_registry
    from app.models.document import DocumentCategory, ProcessingState
    from app.models.extraction import ExtractionStatus

    session = SessionLocal()
    try:
        seed_registry.seed(session)
        document = _make_document(
            session,
            processing_state=processing_state or ProcessingState.OCR_DONE,
            original_filename=filename,
            storage_key=f"uploads/{filename}",
            sha256=uuid4().hex + uuid4().hex,
        )
        _make_extraction(
            session,
            document,
            fields,
            status=extraction_status or ExtractionStatus.SUCCEEDED,
        )
        session.commit()
        return document.id
    finally:
        session.close()


def test_post_verify_200_shape(client):
    document_id = _seed_client_document(academic_fields())
    response = client.post(f"/api/v1/documents/{document_id}/verify")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"verification_id", "status", "document_id"}
    assert body["document_id"] == document_id
    assert body["status"] == VerificationStatus.VERIFIED_MATCH.value
    assert body["status"] != VerificationStatus.PENDING.value


def test_no_trusted_record_is_http_200(client):
    document_id = _seed_client_document(academic_fields(student_id="DEMO-STU-999"))
    response = client.post(f"/api/v1/documents/{document_id}/verify")
    assert response.status_code == 200
    assert response.json()["status"] == VerificationStatus.NO_TRUSTED_RECORD.value


def test_review_required_is_http_200(client):
    fields = academic_fields(student_name=_entry(None, None))
    document_id = _seed_client_document(fields)
    response = client.post(f"/api/v1/documents/{document_id}/verify")
    assert response.status_code == 200
    assert response.json()["status"] == VerificationStatus.REVIEW_REQUIRED.value


def test_get_verification_full_shape(client):
    document_id = _seed_client_document(academic_fields(semester_or_year="6"))
    created = client.post(f"/api/v1/documents/{document_id}/verify").json()
    response = client.get(f"/api/v1/verifications/{created['verification_id']}")
    assert response.status_code == 200
    body = response.json()
    for key in (
        "verification_id",
        "document_id",
        "status",
        "registry_record_key",
        "field_comparisons",
        "rule_results",
        "reason_codes",
        "is_current",
        "supersedes_verification_id",
        "review_actions",
        "created_at",
    ):
        assert key in body
    assert body["status"] == VerificationStatus.INTEGRITY_MISMATCH.value
    assert body["registry_record_key"] == "DEMO-STU-001"
    assert body["is_current"] is True
    assert body["supersedes_verification_id"] is None
    assert body["review_actions"] == []
    assert len(body["rule_results"]) == 5
    assert "FIELD_MISMATCH:semester_or_year" in body["reason_codes"]
    semester = next(row for row in body["field_comparisons"] if row["field"] == "semester_or_year")
    assert semester["extracted_value"] == "6"
    assert semester["registry_value"] == "5"
    assert semester["matched"] is False


def test_verify_404(client):
    response = client.post("/api/v1/documents/ffffffffffffffffffffffffffffffff/verify")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_verify_409_when_extraction_not_ready(client):
    from app.db import SessionLocal
    from app.models.document import ProcessingState

    session = SessionLocal()
    try:
        document = _make_document(session, processing_state=ProcessingState.OCR_IN_PROGRESS)
        session.commit()
        document_id = document.id
    finally:
        session.close()
    response = client.post(f"/api/v1/documents/{document_id}/verify")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EXTRACTION_NOT_READY"


def test_get_verification_404(client):
    response = client.get("/api/v1/verifications/ffffffffffffffffffffffffffffffff")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VERIFICATION_NOT_FOUND"


def test_two_verify_calls_create_two_rows_first_unchanged(client):
    from app.db import SessionLocal
    from app.repositories import verification_repo

    document_id = _seed_client_document(academic_fields())
    first = client.post(f"/api/v1/documents/{document_id}/verify").json()
    session = SessionLocal()
    try:
        row = verification_repo.get_by_id(session, first["verification_id"])
        snapshot = (
            row.status.value,
            row.field_comparisons_json,
            row.rule_results_json,
            row.reason_codes_json,
            row.supersedes_verification_id,
        )
    finally:
        session.close()

    second = client.post(f"/api/v1/documents/{document_id}/verify").json()
    assert first["verification_id"] != second["verification_id"]

    session = SessionLocal()
    try:
        rows = verification_repo.list_for_document(session, document_id)
        assert len(rows) == 2
        original = verification_repo.get_by_id(session, first["verification_id"])
        assert (
            original.status.value,
            original.field_comparisons_json,
            original.rule_results_json,
            original.reason_codes_json,
            original.supersedes_verification_id,
        ) == snapshot
        latest = verification_repo.get_latest_for_document(session, document_id)
        assert latest.id == second["verification_id"]
    finally:
        session.close()


def test_manual_fixture_match_mismatch_unregistered(db_session):
    from app.fixtures import seed_registry
    from app.services.verification_service import verify_document

    seed_registry.seed(db_session)

    match_doc = _make_document(db_session, original_filename="academic_certificate_match.png")
    _make_extraction(db_session, match_doc, academic_fields())
    match_row = verify_document(match_doc.id, db_session)
    assert match_row.status.value == VerificationStatus.VERIFIED_MATCH.value
    comparisons = json.loads(match_row.field_comparisons_json)
    assert len(comparisons) == 6
    assert all(row["matched"] for row in comparisons)

    mismatch_doc = _make_document(
        db_session,
        original_filename="academic_certificate_mismatch.png",
        sha256="e" * 64,
        storage_key="uploads/mismatch.png",
    )
    _make_extraction(db_session, mismatch_doc, academic_fields(semester_or_year="6"))
    mismatch_row = verify_document(mismatch_doc.id, db_session)
    assert mismatch_row.status.value == VerificationStatus.INTEGRITY_MISMATCH.value
    codes = json.loads(mismatch_row.reason_codes_json)
    assert "FIELD_MISMATCH:semester_or_year" in codes

    unreg = _make_document(
        db_session,
        original_filename="academic_certificate_unregistered.png",
        sha256="f" * 64,
        storage_key="uploads/unregistered.png",
    )
    _make_extraction(db_session, unreg, academic_fields(student_id="DEMO-STU-999"))
    unreg_row = verify_document(unreg.id, db_session)
    assert unreg_row.status.value == VerificationStatus.NO_TRUSTED_RECORD.value


def _png_bytes() -> bytes:
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (32, 32), color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_upload_then_verify_runs_ocr_and_returns_terminal_status(client):
    from app.db import SessionLocal
    from app.fixtures import seed_registry

    session = SessionLocal()
    try:
        seed_registry.seed(session)
        session.commit()
    finally:
        session.close()

    upload = client.post(
        "/api/v1/documents",
        files={"file": ("sample.png", _png_bytes(), "image/png")},
        data={"category": "academic_certificate"},
    )
    assert upload.status_code == 201
    assert upload.json()["processing_state"] == "UPLOADED"
    document_id = upload.json()["document_id"]

    verify = client.post(f"/api/v1/documents/{document_id}/verify")
    assert verify.status_code == 200
    body = verify.json()
    assert body["document_id"] == document_id
    assert body["status"] != VerificationStatus.PENDING.value
    assert body["status"] in {item.value for item in VerificationStatus if item is not VerificationStatus.PENDING}
    assert body["status"] == VerificationStatus.VERIFIED_MATCH.value

    meta = client.get(f"/api/v1/documents/{document_id}")
    assert meta.status_code == 200
    assert meta.json()["processing_state"] in {"OCR_DONE", "OCR_FAILED"}

    extraction = client.get(f"/api/v1/documents/{document_id}/extraction")
    assert extraction.status_code == 200
    assert extraction.json()["status"] in {"SUCCEEDED", "FAILED"}
    assert extraction.json()["status"] != "PENDING"
    fields = extraction.json()["extracted_fields"]
    assert fields["student_name"]["value"] == "Aarav Demo"
    assert fields["student_id"]["value"] == "DEMO-STU-001"


def test_verify_skips_ocr_when_successful_extraction_exists(client, monkeypatch):
    document_id = _seed_client_document(academic_fields())
    calls = {"n": 0}

    def _should_not_run(*args, **kwargs):
        calls["n"] += 1
        raise AssertionError("process_document must not run when extraction already succeeded")

    monkeypatch.setattr(
        "app.services.verification_service.process_document",
        _should_not_run,
    )
    response = client.post(f"/api/v1/documents/{document_id}/verify")
    assert response.status_code == 200
    assert calls["n"] == 0
