"""Tests for Task 08 human review and additive verification corrections."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

import app.models  # noqa: F401

from app.models.review import ReviewActionType
from app.models.verification import VerificationStatus
from app.repositories import review_repo, verification_repo
from app.services.review_service import review_verification


ACADEMIC = "academic_certificate"


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _entry(value, confidence=0.95, source="ocr"):
    return {
        "value": value,
        "confidence": confidence,
        "source": source,
    }


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


def _make_document(session, **overrides):
    from app.models.document import Document, DocumentCategory, ProcessingState
    from app.repositories import documents_repo

    values = {
        "category": DocumentCategory.ACADEMIC_CERTIFICATE,
        "original_filename": "academic_certificate_review.png",
        "storage_key": "uploads/academic_certificate_review.png",
        "sha256": "r" * 64,
        "mime_type": "image/png",
        "byte_size": 2048,
        "page_count": 1,
        "processing_state": ProcessingState.OCR_DONE,
        "uploaded_at": _now(),
    }

    values.update(overrides)

    return documents_repo.create(
        session,
        Document(**values),
    )


def _ocr_dump_from_fields(fields: dict) -> str:
    regions = []

    labels = {
        "student_name": "Student Name",
        "institution_name": "Institution Name",
        "student_id": "Student ID",
        "course_name": "Course Name",
        "semester_or_year": "Semester",
        "certificate_or_marksheet_id": "Certificate ID",
        "issue_date": "Issue Date",
    }

    y = 80

    for name, label in labels.items():
        entry = fields.get(name) or {}

        if not isinstance(entry, dict):
            continue

        value = entry.get("value")

        if value is None:
            continue

        confidence = entry.get("confidence")

        if confidence is None:
            confidence = 0.95

        regions.append(
            {
                "text": f"{label}: {value}",
                "confidence": confidence,
                "bbox": [60, y, 700, y + 20],
                "page": 1,
            }
        )

        y += 55

    return json.dumps(
        {
            "text": " ".join(row["text"] for row in regions),
            "regions": regions,
            "warnings": [],
        }
    )


def _make_extraction(session, document, fields):
    from app.models.extraction import ExtractionResult, ExtractionStatus
    from app.repositories import extraction_repo

    row = ExtractionResult(
        document_id=document.id,
        engine_name="fake",
        engine_version="1.0",
        raw_ocr_json=_ocr_dump_from_fields(fields),
        extracted_fields_json=json.dumps(fields),
        warnings_json="[]",
        status=ExtractionStatus.SUCCEEDED,
        created_at=_now(),
    )

    return extraction_repo.create(session, row)


def _seed_document(session, fields):
    from app.fixtures import seed_registry

    seed_registry.seed(session)

    document = _make_document(
        session,
        sha256="r" * 64,
        storage_key="uploads/review.png",
    )

    _make_extraction(
        session,
        document,
        fields,
    )

    session.commit()

    return document


def _verify(session, document):
    from app.services.verification_service import verify_document

    return verify_document(
        document.id,
        session,
    )


# ---------------------------------------------------------------------------
# ACCEPT
# ---------------------------------------------------------------------------


def test_accept_creates_review_row(db_session):
    document = _seed_document(
        db_session,
        academic_fields(
            student_id=_entry(
                "DEMO-STU-001",
                0.69,
            )
        ),
    )

    verification = _verify(
        db_session,
        document,
    )

    assert verification.status is VerificationStatus.REVIEW_REQUIRED

    review, new_verification = review_verification(
        db_session,
        verification.id,
        "reviewer-001",
        "ACCEPT",
    )

    assert review.action is ReviewActionType.ACCEPT
    assert review.verification_id == verification.id
    assert review.reviewer_ref == "reviewer-001"

    assert new_verification is not None
    assert new_verification.id != verification.id
    assert new_verification.status is VerificationStatus.VERIFIED_MATCH
    assert new_verification.supersedes_verification_id == verification.id


def test_accept_low_confidence_does_not_mutate_original_confidence(
    db_session,
):
    from app.repositories.extraction_repo import get_latest_successful_for_document

    fields = academic_fields(
        student_id=_entry(
            "DEMO-STU-001",
            0.69,
        )
    )
    document = _seed_document(db_session, fields)
    verification = _verify(db_session, document)

    extraction_before = get_latest_successful_for_document(
        db_session,
        document.id,
    )
    stored_before = json.loads(extraction_before.extracted_fields_json)
    assert stored_before["student_id"]["confidence"] == 0.69
    assert stored_before["student_id"]["source"] == "ocr"

    review, new_verification = review_verification(
        db_session,
        verification.id,
        "reviewer-001",
        "ACCEPT",
    )

    assert review.action is ReviewActionType.ACCEPT
    assert new_verification.status is VerificationStatus.VERIFIED_MATCH

    original = verification_repo.get_by_id(
        db_session,
        verification.id,
    )
    assert original.status is VerificationStatus.REVIEW_REQUIRED

    extraction_after = get_latest_successful_for_document(
        db_session,
        document.id,
    )
    stored_after = json.loads(extraction_after.extracted_fields_json)
    student_id = stored_after["student_id"]
    if isinstance(student_id, list):
        ocr_entry = next(
            item for item in student_id if item.get("source") == "ocr"
        )
    else:
        ocr_entry = student_id
    assert ocr_entry["confidence"] == 0.69
    assert ocr_entry["source"] == "ocr"
    assert ocr_entry["value"] == "DEMO-STU-001"


def test_accept_missing_required_field_stays_review_required(
    db_session,
):
    document = _seed_document(
        db_session,
        academic_fields(
            student_name=_entry(
                None,
                None,
            )
        ),
    )

    verification = _verify(
        db_session,
        document,
    )

    assert verification.status is VerificationStatus.REVIEW_REQUIRED

    review, result = review_verification(
        db_session,
        verification.id,
        "reviewer-001",
        "ACCEPT",
    )

    assert review.action is ReviewActionType.ACCEPT
    assert result is not None
    assert result.id != verification.id
    assert result.supersedes_verification_id == verification.id
    assert result.status is VerificationStatus.REVIEW_REQUIRED

    original = verification_repo.get_by_id(db_session, verification.id)
    assert original.status is VerificationStatus.REVIEW_REQUIRED


def test_accept_genuine_mismatch_stays_integrity_mismatch(
    db_session,
):
    document = _seed_document(
        db_session,
        academic_fields(
            semester_or_year="6",
        ),
    )

    verification = _verify(
        db_session,
        document,
    )

    assert verification.status is VerificationStatus.INTEGRITY_MISMATCH

    review, result = review_verification(
        db_session,
        verification.id,
        "reviewer-001",
        "ACCEPT",
    )

    assert review.action is ReviewActionType.ACCEPT
    assert result is not None
    assert result.id != verification.id
    assert result.supersedes_verification_id == verification.id
    assert result.status is VerificationStatus.INTEGRITY_MISMATCH

    original = verification_repo.get_by_id(db_session, verification.id)
    assert original.status is VerificationStatus.INTEGRITY_MISMATCH


# ---------------------------------------------------------------------------
# UNRESOLVED
# ---------------------------------------------------------------------------


def test_unresolved_creates_review_without_new_verification(
    db_session,
):
    document = _seed_document(
        db_session,
        academic_fields(
            student_id=_entry(
                "DEMO-STU-001",
                0.69,
            )
        ),
    )

    verification = _verify(
        db_session,
        document,
    )

    review, new_verification = review_verification(
        db_session,
        verification.id,
        "reviewer-001",
        "UNRESOLVED",
        comment="Unable to confirm the student ID.",
    )

    assert review.action is ReviewActionType.UNRESOLVED
    assert review.comment == "Unable to confirm the student ID."
    assert review.verification_id == verification.id

    assert new_verification is None

    latest = verification_repo.get_latest_for_document(
        db_session,
        document.id,
    )

    assert latest.id == verification.id
    assert latest.status is VerificationStatus.REVIEW_REQUIRED


# ---------------------------------------------------------------------------
# CORRECT — central Task 08 scenario
# ---------------------------------------------------------------------------


def test_correct_ocr_misread_creates_new_verified_row(
    db_session,
):
    document = _seed_document(
        db_session,
        academic_fields(
            student_id=_entry(
                "DEMO-STU-OO1",
                0.69,
            )
        ),
    )

    original = _verify(
        db_session,
        document,
    )

    assert original.status is VerificationStatus.REVIEW_REQUIRED

    original_comparisons = original.field_comparisons_json
    original_reason_codes = original.reason_codes_json

    review, corrected = review_verification(
        db_session,
        original.id,
        "reviewer-001",
        "CORRECT",
        corrections={
            "student_id": "DEMO-STU-001",
        },
        comment="OCR misread O as zero.",
    )

    assert review.action is ReviewActionType.CORRECT
    assert review.verification_id == original.id
    assert review.reviewer_ref == "reviewer-001"

    assert corrected is not None
    assert corrected.id != original.id

    assert corrected.status is VerificationStatus.VERIFIED_MATCH

    assert corrected.supersedes_verification_id == original.id

    # Original verification remains unchanged.
    old = verification_repo.get_by_id(
        db_session,
        original.id,
    )

    assert old.status is VerificationStatus.REVIEW_REQUIRED
    assert old.field_comparisons_json == original_comparisons
    assert old.reason_codes_json == original_reason_codes

    # Latest verification is the new row.
    latest = verification_repo.get_latest_for_document(
        db_session,
        document.id,
    )

    assert latest.id == corrected.id

    rows = verification_repo.list_for_document(
        db_session,
        document.id,
    )

    assert len(rows) == 2
    assert {row.id for row in rows} == {
        original.id,
        corrected.id,
    }


def test_correct_preserves_ocr_and_adds_corrected_value(
    db_session,
):
    document = _seed_document(
        db_session,
        academic_fields(
            student_id=_entry(
                "DEMO-STU-OO1",
                0.69,
            )
        ),
    )

    original = _verify(
        db_session,
        document,
    )

    review_verification(
        db_session,
        original.id,
        "reviewer-001",
        "CORRECT",
        corrections={
            "student_id": "DEMO-STU-001",
        },
    )

    extraction = document.extractions[0]

    stored = json.loads(
        extraction.extracted_fields_json,
    )

    student_id = stored["student_id"]

    assert isinstance(student_id, list)
    assert len(student_id) == 2

    ocr_entry = student_id[0]
    corrected_entry = student_id[1]

    assert ocr_entry["value"] == "DEMO-STU-OO1"
    assert ocr_entry["confidence"] == 0.69
    assert ocr_entry["source"] == "ocr"

    assert corrected_entry["value"] == "DEMO-STU-001"
    assert corrected_entry["confidence"] is None
    assert corrected_entry["source"] == "corrected"


def test_correct_does_not_modify_original_verification_status(
    db_session,
):
    document = _seed_document(
        db_session,
        academic_fields(
            student_id=_entry(
                "DEMO-STU-OO1",
                0.69,
            )
        ),
    )

    original = _verify(
        db_session,
        document,
    )

    review_verification(
        db_session,
        original.id,
        "reviewer-001",
        "CORRECT",
        corrections={
            "student_id": "DEMO-STU-001",
        },
    )

    refreshed = verification_repo.get_by_id(
        db_session,
        original.id,
    )

    assert refreshed.status is VerificationStatus.REVIEW_REQUIRED


def test_two_successive_corrections_preserve_history(
    db_session,
):
    document = _seed_document(
        db_session,
        academic_fields(
            student_id=_entry(
                "DEMO-STU-OO1",
                0.69,
            )
        ),
    )

    first = _verify(
        db_session,
        document,
    )

    _, second = review_verification(
        db_session,
        first.id,
        "reviewer-001",
        "CORRECT",
        corrections={
            "student_id": "DEMO-STU-002",
        },
    )

    assert second.supersedes_verification_id == first.id

    _, third = review_verification(
        db_session,
        second.id,
        "reviewer-002",
        "CORRECT",
        corrections={
            "student_id": "DEMO-STU-001",
        },
    )

    assert third.id != second.id
    assert third.supersedes_verification_id == second.id

    rows = verification_repo.list_for_document(
        db_session,
        document.id,
    )

    assert len(rows) == 3

    assert {
        rows[0].id,
        rows[1].id,
        rows[2].id,
    } == {
        first.id,
        second.id,
        third.id,
    }

    latest = verification_repo.get_latest_for_document(
        db_session,
        document.id,
    )

    assert latest.id == third.id
    assert latest.status is VerificationStatus.VERIFIED_MATCH


# ---------------------------------------------------------------------------
# Review history
# ---------------------------------------------------------------------------


def test_multiple_review_actions_are_preserved(
    db_session,
):
    document = _seed_document(
        db_session,
        academic_fields(
            student_id=_entry(
                "DEMO-STU-001",
                0.69,
            )
        ),
    )

    verification = _verify(
        db_session,
        document,
    )

    review_verification(
        db_session,
        verification.id,
        "reviewer-001",
        "UNRESOLVED",
        comment="First review.",
    )

    review_verification(
        db_session,
        verification.id,
        "reviewer-002",
        "ACCEPT",
        comment="Second review.",
    )

    reviews = review_repo.list_for_verification(
        db_session,
        verification.id,
    )

    assert len(reviews) == 2
    assert {review.reviewer_ref for review in reviews} == {
        "reviewer-001",
        "reviewer-002",
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_invalid_action_is_rejected(db_session):
    document = _seed_document(
        db_session,
        academic_fields(),
    )

    verification = _verify(
        db_session,
        document,
    )

    from app.services.review_service import InvalidReviewActionError

    with pytest.raises(InvalidReviewActionError):
        review_verification(
            db_session,
            verification.id,
            "reviewer-001",
            "INVALID",
        )


def test_empty_reviewer_ref_is_rejected(db_session):
    document = _seed_document(
        db_session,
        academic_fields(),
    )

    verification = _verify(
        db_session,
        document,
    )

    from app.services.review_service import EmptyReviewerRefError

    with pytest.raises(EmptyReviewerRefError):
        review_verification(
            db_session,
            verification.id,
            "   ",
            "ACCEPT",
        )


def test_correct_requires_corrections(db_session):
    document = _seed_document(
        db_session,
        academic_fields(),
    )

    verification = _verify(
        db_session,
        document,
    )

    from app.services.review_service import MissingCorrectionsError

    with pytest.raises(MissingCorrectionsError):
        review_verification(
            db_session,
            verification.id,
            "reviewer-001",
            "CORRECT",
        )


def test_correct_rejects_unknown_field(db_session):
    document = _seed_document(
        db_session,
        academic_fields(),
    )

    verification = _verify(
        db_session,
        document,
    )

    from app.services.review_service import UnknownCorrectionFieldError

    with pytest.raises(UnknownCorrectionFieldError):
        review_verification(
            db_session,
            verification.id,
            "reviewer-001",
            "CORRECT",
            corrections={
                "does_not_exist": "something",
            },
        )


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def _seed_client_document(client, fields):
    from app.db import SessionLocal
    from app.fixtures import seed_registry

    session = SessionLocal()

    try:
        seed_registry.seed(session)

        document = _make_document(
            session,
            sha256="c" * 64,
            storage_key="uploads/client-review.png",
        )

        _make_extraction(
            session,
            document,
            fields,
        )

        session.commit()

        return document.id

    finally:
        session.close()


def test_review_api_accept(client):
    document_id = _seed_client_document(
        client,
        academic_fields(
            student_id=_entry(
                "DEMO-STU-001",
                0.69,
            )
        ),
    )

    verification = client.post(
        f"/api/v1/documents/{document_id}/verify",
    )

    assert verification.status_code == 200
    verification_id = verification.json()["verification_id"]

    response = client.post(
        f"/api/v1/verifications/{verification_id}/review",
        json={
            "reviewer_ref": "reviewer-001",
            "action": "ACCEPT",
            "comment": "Reviewed.",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert set(body) == {
        "review_action_id",
        "new_verification_id",
        "new_status",
    }

    assert body["new_verification_id"] is not None
    assert body["new_status"] == VerificationStatus.VERIFIED_MATCH.value


def test_review_api_correct_central_scenario(client):
    document_id = _seed_client_document(
        client,
        academic_fields(
            student_id=_entry(
                "DEMO-STU-OO1",
                0.69,
            )
        ),
    )

    verification = client.post(
        f"/api/v1/documents/{document_id}/verify",
    )

    assert verification.status_code == 200

    original_id = verification.json()["verification_id"]

    assert verification.json()["status"] == (
        VerificationStatus.REVIEW_REQUIRED.value
    )

    response = client.post(
        f"/api/v1/verifications/{original_id}/review",
        json={
            "reviewer_ref": "reviewer-001",
            "action": "CORRECT",
            "corrections": {
                "student_id": "DEMO-STU-001",
            },
            "comment": "Corrected OCR student ID.",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["review_action_id"]
    assert body["new_verification_id"]
    assert body["new_verification_id"] != original_id
    assert body["new_status"] == VerificationStatus.VERIFIED_MATCH.value

    original = client.get(
        f"/api/v1/verifications/{original_id}",
    )

    assert original.status_code == 200
    assert original.json()["status"] == (
        VerificationStatus.REVIEW_REQUIRED.value
    )

    corrected_id = body["new_verification_id"]

    corrected = client.get(
        f"/api/v1/verifications/{corrected_id}",
    )

    assert corrected.status_code == 200
    assert corrected.json()["status"] == (
        VerificationStatus.VERIFIED_MATCH.value
    )

    extraction = client.get(
        f"/api/v1/documents/{document_id}/extraction",
    )

    assert extraction.status_code == 200

    student_id = extraction.json()["extracted_fields"]["student_id"]

    assert isinstance(student_id, list)
    assert student_id[0]["value"] == "DEMO-STU-OO1"
    assert student_id[0]["source"] == "ocr"
    assert student_id[1]["value"] == "DEMO-STU-001"
    assert student_id[1]["source"] == "corrected"


def test_review_api_unresolved(client):
    document_id = _seed_client_document(
        client,
        academic_fields(
            student_id=_entry(
                "DEMO-STU-001",
                0.69,
            )
        ),
    )

    verification = client.post(
        f"/api/v1/documents/{document_id}/verify",
    )

    verification_id = verification.json()["verification_id"]

    response = client.post(
        f"/api/v1/verifications/{verification_id}/review",
        json={
            "reviewer_ref": "reviewer-001",
            "action": "UNRESOLVED",
            "comment": "Needs further evidence.",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["review_action_id"]
    assert body["new_verification_id"] is None
    assert body["new_status"] == VerificationStatus.REVIEW_REQUIRED.value


def test_review_api_404(client):
    response = client.post(
        "/api/v1/verifications/ffffffffffffffffffffffffffffffff/review",
        json={
            "reviewer_ref": "reviewer-001",
            "action": "ACCEPT",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VERIFICATION_NOT_FOUND"


def test_review_api_invalid_action(client):
    document_id = _seed_client_document(
        client,
        academic_fields(),
    )

    verification = client.post(
        f"/api/v1/documents/{document_id}/verify",
    )

    verification_id = verification.json()["verification_id"]

    response = client.post(
        f"/api/v1/verifications/{verification_id}/review",
        json={
            "reviewer_ref": "reviewer-001",
            "action": "INVALID",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ACTION"


def test_review_api_missing_corrections(client):
    document_id = _seed_client_document(
        client,
        academic_fields(),
    )

    verification = client.post(
        f"/api/v1/documents/{document_id}/verify",
    )

    verification_id = verification.json()["verification_id"]

    response = client.post(
        f"/api/v1/verifications/{verification_id}/review",
        json={
            "reviewer_ref": "reviewer-001",
            "action": "CORRECT",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MISSING_CORRECTIONS"


def test_review_api_empty_reviewer(client):
    document_id = _seed_client_document(
        client,
        academic_fields(),
    )

    verification = client.post(
        f"/api/v1/documents/{document_id}/verify",
    )

    verification_id = verification.json()["verification_id"]

    response = client.post(
        f"/api/v1/verifications/{verification_id}/review",
        json={
            "reviewer_ref": "   ",
            "action": "ACCEPT",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_REVIEWER_REF"


def test_review_api_unknown_correction_field(client):
    document_id = _seed_client_document(
        client,
        academic_fields(),
    )

    verification = client.post(
        f"/api/v1/documents/{document_id}/verify",
    )

    verification_id = verification.json()["verification_id"]

    response = client.post(
        f"/api/v1/verifications/{verification_id}/review",
        json={
            "reviewer_ref": "reviewer-001",
            "action": "CORRECT",
            "corrections": {
                "not_a_real_field": "value",
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNKNOWN_CORRECTION_FIELD"


def _registry_snapshot(session):
    from app.models.registry import RegistryRecord

    return {
        row.id: (row.fields_json, row.active, row.synthetic_record_key)
        for row in session.query(RegistryRecord).all()
    }


def test_review_actions_on_get_verification_are_oldest_first(client):
    document_id = _seed_client_document(
        client,
        academic_fields(
            student_id=_entry("DEMO-STU-001", 0.69),
        ),
    )
    verification_id = client.post(
        f"/api/v1/documents/{document_id}/verify",
    ).json()["verification_id"]

    first = client.post(
        f"/api/v1/verifications/{verification_id}/review",
        json={
            "reviewer_ref": "reviewer-001",
            "action": "UNRESOLVED",
            "comment": "First look.",
        },
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/verifications/{verification_id}/review",
        json={
            "reviewer_ref": "reviewer-002",
            "action": "ACCEPT",
            "comment": "Second look.",
        },
    )
    assert second.status_code == 201

    body = client.get(f"/api/v1/verifications/{verification_id}").json()
    actions = body["review_actions"]
    assert len(actions) == 2
    assert actions[0]["action"] == "UNRESOLVED"
    assert actions[0]["reviewer_ref"] == "reviewer-001"
    assert actions[1]["action"] == "ACCEPT"
    assert actions[1]["reviewer_ref"] == "reviewer-002"
    assert actions[0]["created_at"] <= actions[1]["created_at"]


def test_document_verifications_history_newest_first_and_one_current(client):
    document_id = _seed_client_document(
        client,
        academic_fields(
            student_id=_entry("DEMO-STU-OO1", 0.69),
        ),
    )
    original_id = client.post(
        f"/api/v1/documents/{document_id}/verify",
    ).json()["verification_id"]

    corrected = client.post(
        f"/api/v1/verifications/{original_id}/review",
        json={
            "reviewer_ref": "reviewer-001",
            "action": "CORRECT",
            "corrections": {"student_id": "DEMO-STU-001"},
        },
    )
    assert corrected.status_code == 201
    new_id = corrected.json()["new_verification_id"]

    response = client.get(f"/api/v1/documents/{document_id}/verifications")
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    rows = body["verifications"]
    assert len(rows) == 2
    for row in rows:
        assert set(row) == {
            "verification_id",
            "status",
            "is_current",
            "supersedes_verification_id",
            "review_action_count",
            "created_at",
        }
    assert rows[0]["created_at"] >= rows[1]["created_at"]
    assert rows[0]["verification_id"] == new_id
    assert rows[0]["is_current"] is True
    assert rows[0]["supersedes_verification_id"] == original_id
    assert rows[1]["verification_id"] == original_id
    assert rows[1]["is_current"] is False
    assert sum(1 for row in rows if row["is_current"] is True) == 1
    assert rows[1]["review_action_count"] == 1
    assert rows[0]["review_action_count"] == 0


def test_document_verifications_unknown_document_404(client):
    response = client.get(
        "/api/v1/documents/ffffffffffffffffffffffffffffffff/verifications",
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_review_action_survives_reevaluation_failure(db_session, monkeypatch):
    document = _seed_document(
        db_session,
        academic_fields(student_id=_entry("DEMO-STU-001", 0.69)),
    )
    original = _verify(db_session, document)
    original_status = original.status
    original_reasons = original.reason_codes_json
    original_id = original.id

    def _boom(*args, **kwargs):
        raise RuntimeError("forced re-evaluation failure")

    monkeypatch.setattr("app.services.review_service.evaluate", _boom)

    with pytest.raises(RuntimeError, match="forced re-evaluation failure"):
        review_verification(
            db_session,
            original_id,
            "reviewer-001",
            "ACCEPT",
        )

    reviews = review_repo.list_for_verification(db_session, original_id)
    assert len(reviews) == 1
    assert reviews[0].action is ReviewActionType.ACCEPT

    refreshed = verification_repo.get_by_id(db_session, original_id)
    assert refreshed.status is original_status
    assert refreshed.reason_codes_json == original_reasons
    assert len(verification_repo.list_for_document(db_session, document.id)) == 1


def test_correct_reevaluation_failure_does_not_mutate_extraction(db_session, monkeypatch):
    from app.repositories.extraction_repo import get_latest_successful_for_document

    document = _seed_document(
        db_session,
        academic_fields(student_id=_entry("DEMO-STU-OO1", 0.69)),
    )
    original = _verify(db_session, document)
    fields_before = get_latest_successful_for_document(
        db_session, document.id
    ).extracted_fields_json

    monkeypatch.setattr(
        "app.services.review_service.evaluate",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("eval failed")),
    )

    with pytest.raises(RuntimeError, match="eval failed"):
        review_verification(
            db_session,
            original.id,
            "reviewer-001",
            "CORRECT",
            corrections={"student_id": "DEMO-STU-001"},
        )

    assert review_repo.list_for_verification(db_session, original.id)
    extraction = get_latest_successful_for_document(db_session, document.id)
    assert extraction.extracted_fields_json == fields_before
    stored = json.loads(extraction.extracted_fields_json)
    assert stored["student_id"]["source"] == "ocr"
    assert stored["student_id"]["confidence"] == 0.69
    assert verification_repo.get_by_id(db_session, original.id).status is (
        VerificationStatus.REVIEW_REQUIRED
    )


def test_registry_unchanged_after_accept_correct_unresolved(db_session):
    document = _seed_document(db_session, academic_fields())
    original = _verify(db_session, document)
    before = _registry_snapshot(db_session)

    review_verification(db_session, original.id, "r1", "UNRESOLVED")
    _, accepted = review_verification(db_session, original.id, "r2", "ACCEPT")
    review_verification(
        db_session,
        accepted.id,
        "r3",
        "CORRECT",
        corrections={"semester_or_year": "5"},
    )

    assert _registry_snapshot(db_session) == before