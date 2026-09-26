"""Task 12 end-to-end scenario tests.

These tests use the project's fake OCR and fake blockchain adapters.
No live PaddleOCR or blockchain node is required.
"""

from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.adapters.blockchain.fake_adapter import FakeBlockchainAdapter
from app.adapters.ocr.fake_adapter import create_fake_adapter


def _png_bytes(tint: int = 255) -> bytes:
    """Create a real PNG accepted by the project's upload validation."""
    buffer = BytesIO()

    Image.new(
        "RGB",
        (64, 64),
        color=(tint, tint, tint),
    ).save(
        buffer,
        format="PNG",
    )

    return buffer.getvalue()


def _seed_registry() -> None:
    """Seed the synthetic registry into the temporary test database."""
    # Import inside the function so conftest.py can patch SessionLocal.
    from app.db import SessionLocal
    from app.fixtures import seed_registry

    session = SessionLocal()

    try:
        seed_registry.seed(session)
        session.commit()
    finally:
        session.close()


def _academic_text(**overrides: str) -> str:
    """Build the standard synthetic academic document text."""
    fields = {
        "Student Name": "Aarav Demo",
        "Institution Name": "Example Technical Institute",
        "Student ID": "DEMO-STU-001",
        "Course": "B.Tech CSE",
        "Semester / Year": "5",
        "Certificate / Marksheet ID": "DEMO-MARK-001",
    }

    fields.update(overrides)

    return "\n".join(
        f"{label}: {value}"
        for label, value in fields.items()
    )


def _use_ocr(
    monkeypatch,
    **kwargs,
) -> None:
    """Install the project's fake OCR adapter."""
    adapter = create_fake_adapter(
        mode="clean",
        **kwargs,
    )

    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_adapter",
        lambda: adapter,
    )


def _use_empty_ocr(monkeypatch) -> None:
    """Install the fake OCR adapter that produces no text."""
    adapter = create_fake_adapter(
        mode="empty",
    )

    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_adapter",
        lambda: adapter,
    )


def _use_misread_student_id_ocr(monkeypatch) -> None:
    """Install the project's known low-confidence Student ID scenario."""
    from app.adapters.ocr.fake_adapter import (
        _LABEL_X1,
        _LABEL_X2,
        _ROW_H,
        _ROW_Y0,
        _VALUE_X1,
        _VALUE_X2,
        _academic_two_column_rows,
    )
    from app.adapters.ocr.base import OcrAdapter, OcrRegion, OcrResult

    class MisreadStudentIdAdapter(OcrAdapter):
        def run(self, image):
            regions = []
            y = _ROW_Y0

            for label, value in _academic_two_column_rows():
                regions.append(
                    OcrRegion(
                        label,
                        0.95,
                        (_LABEL_X1, y, _LABEL_X2, y + 20),
                        1,
                    )
                )

                if label == "Student ID":
                    text = "DEMO-STU-OO1"
                    confidence = 0.50
                else:
                    text = value
                    confidence = 0.95

                regions.append(
                    OcrRegion(
                        text,
                        confidence,
                        (_VALUE_X1, y, _VALUE_X2, y + 20),
                        1,
                    )
                )

                y += _ROW_H

            mean_confidence = sum(
                region.confidence
                for region in regions
            ) / len(regions)

            return OcrResult(
                "\n".join(
                    region.text
                    for region in regions
                ),
                regions,
                mean_confidence,
                "fake",
                "0.0.0-test",
                [],
            )

    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_adapter",
        lambda: MisreadStudentIdAdapter(),
    )


def _enable_chain(test_settings) -> None:
    """Enable blockchain recording for a test."""
    test_settings.BLOCKCHAIN_ENABLED = True
    test_settings.BLOCKCHAIN_CONTRACT_ADDRESS = (
        "0xabcabcabcabcabcabcabcabcabcabcabcabcabca"
    )


def _install_shared_chain(monkeypatch):
    """Install one shared successful fake blockchain adapter."""
    shared = FakeBlockchainAdapter(
        mode="success",
    )

    monkeypatch.setattr(
        "app.services.blockchain_service.FakeBlockchainAdapter",
        lambda *args, **kwargs: shared,
    )

    return shared


def _upload(
    client: TestClient,
    *,
    category: str = "academic_certificate",
    filename: str = "sample.png",
    content: bytes | None = None,
):
    """Upload a valid document through the public API."""
    return client.post(
        "/api/v1/documents",
        files={
            "file": (
                filename,
                content if content is not None else _png_bytes(),
                "image/png",
            )
        },
        data={
            "category": category,
        },
    )


def _verify(
    client: TestClient,
    document_id: str,
):
    """Run synchronous verification."""
    response = client.post(
        f"/api/v1/documents/{document_id}/verify"
    )

    assert response.status_code == 200

    return response.json()


def _get_verification_detail(
    client: TestClient,
    verification_id: str,
):
    """Get the complete verification detail."""
    return client.get(
        f"/api/v1/verifications/{verification_id}"
    )


def test_matching_fixture_returns_verified_match(
    client,
    monkeypatch,
):
    _seed_registry()
    _use_ocr(monkeypatch)

    upload_response = _upload(client)

    assert upload_response.status_code == 201

    document_id = upload_response.json()["document_id"]

    body = _verify(
        client,
        document_id,
    )

    assert body["status"] == "VERIFIED_MATCH"

    verification_id = body["verification_id"]

    detail_response = _get_verification_detail(
        client,
        verification_id,
    )

    assert detail_response.status_code == 200

    detail = detail_response.json()

    assert detail["status"] == "VERIFIED_MATCH"

    field_comparisons = detail["field_comparisons"]

    assert field_comparisons

    assert all(
        comparison["matched"] is True
        for comparison in field_comparisons
    )


def test_no_registry_entry_returns_no_trusted_record(
    client,
    monkeypatch,
):
    _seed_registry()

    _use_ocr(
        monkeypatch,
        custom_text=_academic_text(
            **{
                "Student ID": "DEMO-STU-999",
            }
        ),
    )

    upload_response = _upload(client)

    assert upload_response.status_code == 201

    document_id = upload_response.json()["document_id"]

    body = _verify(
        client,
        document_id,
    )

    assert body["status"] == "NO_TRUSTED_RECORD"


def test_low_confidence_required_field_returns_review_required(
    client,
    monkeypatch,
):
    _seed_registry()

    _use_ocr(
        monkeypatch,
        custom_text=_academic_text(),
        custom_confidence=0.50,
    )

    upload_response = _upload(client)

    assert upload_response.status_code == 201

    document_id = upload_response.json()["document_id"]

    body = _verify(
        client,
        document_id,
    )

    assert body["status"] == "REVIEW_REQUIRED"


def test_known_field_mismatch_returns_integrity_mismatch(
    client,
    monkeypatch,
):
    _seed_registry()

    _use_ocr(
        monkeypatch,
        custom_text=_academic_text(
            **{
                "Semester / Year": "6",
            }
        ),
    )

    upload_response = _upload(client)

    assert upload_response.status_code == 201

    document_id = upload_response.json()["document_id"]

    body = _verify(
        client,
        document_id,
    )

    assert body["status"] == "INTEGRITY_MISMATCH"

    verification_id = body["verification_id"]

    detail_response = _get_verification_detail(
        client,
        verification_id,
    )

    assert detail_response.status_code == 200

    detail = detail_response.json()

    assert detail["status"] == "INTEGRITY_MISMATCH"

    mismatch_fields = {
        row["field"]
        for row in detail["field_comparisons"]
        if row["matched"] is False
    }

    assert "semester_or_year" in mismatch_fields


def test_empty_ocr_returns_review_required(
    client,
    monkeypatch,
):
    _seed_registry()

    _use_empty_ocr(monkeypatch)

    upload_response = _upload(client)

    assert upload_response.status_code == 201

    document_id = upload_response.json()["document_id"]

    body = _verify(
        client,
        document_id,
    )

    assert body["status"] == "REVIEW_REQUIRED"


def test_upload_validation_rejects_invalid_category(
    client,
):
    response = _upload(
        client,
        category="invalid_category",
    )

    assert response.status_code == 400

    body = response.json()

    assert body["error"]["code"] == "INVALID_CATEGORY"


def test_upload_validation_rejects_unsupported_media_type(
    client,
):
    response = client.post(
        "/api/v1/documents",
        data={
            "category": "academic_certificate",
        },
        files={
            "file": (
                "document.txt",
                BytesIO(b"plain text document"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 415

    body = response.json()

    assert body["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_upload_validation_rejects_empty_file(
    client,
):
    response = client.post(
        "/api/v1/documents",
        data={
            "category": "academic_certificate",
        },
        files={
            "file": (
                "empty.png",
                BytesIO(b""),
                "image/png",
            )
        },
    )

    assert response.status_code == 422

    body = response.json()

    assert body["error"]["code"] == "EMPTY_OR_CORRUPT_FILE"


def test_upload_validation_rejects_oversized_file(
    client,
):
    large_content = b"x" * (20 * 1024 * 1024)

    response = _upload(
        client,
        content=large_content,
    )

    assert response.status_code == 413

    body = response.json()

    assert body["error"]["code"] == "FILE_TOO_LARGE"


def test_blockchain_disabled_returns_not_requested(
    client,
    monkeypatch,
    test_settings,
):
    _seed_registry()

    _use_ocr(monkeypatch)

    test_settings.BLOCKCHAIN_ENABLED = False

    upload_response = _upload(client)

    assert upload_response.status_code == 201

    document_id = upload_response.json()["document_id"]

    body = _verify(
        client,
        document_id,
    )

    assert body["status"] == "VERIFIED_MATCH"

    verification_id = body["verification_id"]

    blockchain_response = client.get(
        f"/api/v1/verifications/{verification_id}/blockchain"
    )

    assert blockchain_response.status_code == 200

    blockchain = blockchain_response.json()

    assert blockchain["recording_status"] == "NOT_REQUESTED"


def test_blockchain_failure_does_not_change_verification(
    client,
    monkeypatch,
    test_settings,
):
    _seed_registry()

    _use_ocr(monkeypatch)

    _enable_chain(test_settings)

    def blockchain_unavailable(*args, **kwargs):
        raise ConnectionError("RPC unavailable")

    monkeypatch.setattr(
        FakeBlockchainAdapter,
        "submit_event",
        blockchain_unavailable,
    )

    upload_response = _upload(client)

    assert upload_response.status_code == 201

    document_id = upload_response.json()["document_id"]

    body = _verify(
        client,
        document_id,
    )

    assert body["status"] == "VERIFIED_MATCH"

    verification_id = body["verification_id"]

    blockchain_response = client.get(
        f"/api/v1/verifications/{verification_id}/blockchain"
    )

    assert blockchain_response.status_code == 200

    blockchain = blockchain_response.json()

    assert blockchain["recording_status"] in {
        "FAILED",
        "PENDING",
        "NOT_REQUESTED",
    }

    detail_response = _get_verification_detail(
        client,
        verification_id,
    )

    assert detail_response.status_code == 200

    detail = detail_response.json()

    assert detail["status"] == "VERIFIED_MATCH"


def test_review_correction_creates_new_verification_row(
    client,
    monkeypatch,
):
    _seed_registry()

    _use_misread_student_id_ocr(monkeypatch)

    upload_response = _upload(client)

    assert upload_response.status_code == 201

    document_id = upload_response.json()["document_id"]

    original = _verify(
        client,
        document_id,
    )

    assert original["status"] == "REVIEW_REQUIRED"

    original_id = original["verification_id"]

    review_response = client.post(
        f"/api/v1/verifications/{original_id}/review",
        json={
            "reviewer_ref": "reviewer-001",
            "action": "CORRECT",
            "corrections": {
                "student_id": "DEMO-STU-001",
            },
        },
    )

    assert review_response.status_code == 201

    review_body = review_response.json()

    assert review_body["new_status"] == "VERIFIED_MATCH"

    new_id = review_body["new_verification_id"]

    assert new_id is not None
    assert new_id != original_id

    original_detail = _get_verification_detail(
        client,
        original_id,
    )

    assert original_detail.status_code == 200

    original_body = original_detail.json()

    assert original_body["is_current"] is False

    corrected_detail = _get_verification_detail(
        client,
        new_id,
    )

    assert corrected_detail.status_code == 200

    corrected_body = corrected_detail.json()

    assert corrected_body["is_current"] is True

    assert (
        corrected_body["supersedes_verification_id"]
        == original_id
    )


def test_duplicate_blockchain_submission_does_not_create_duplicate_record(
    client,
    monkeypatch,
    test_settings,
):
    _seed_registry()

    _use_ocr(monkeypatch)

    _enable_chain(test_settings)

    shared = _install_shared_chain(monkeypatch)

    upload_response = _upload(client)

    assert upload_response.status_code == 201

    document_id = upload_response.json()["document_id"]

    body = _verify(
        client,
        document_id,
    )

    assert body["status"] == "VERIFIED_MATCH"

    verification_id = body["verification_id"]

    first_response = client.get(
        f"/api/v1/verifications/{verification_id}/blockchain"
    )

    assert first_response.status_code == 200

    first = first_response.json()

    assert first["recording_status"] == "CONFIRMED"

    first_submission_count = len(shared.submissions)

    second_response = client.get(
        f"/api/v1/verifications/{verification_id}/blockchain"
    )

    assert second_response.status_code == 200

    second = second_response.json()

    assert second["recording_status"] == "CONFIRMED"

    assert len(shared.submissions) == first_submission_count

    assert (
        second.get("transaction_hash")
        == first.get("transaction_hash")
    )


def test_missing_required_field_takes_review_precedence_over_mismatch(
    client,
    monkeypatch,
):
    _seed_registry()

    _use_ocr(
        monkeypatch,
        custom_text=_academic_text(
            **{
                "Student ID": "",
                "Semester / Year": "6",
            }
        ),
    )

    upload_response = _upload(client)

    assert upload_response.status_code == 201

    document_id = upload_response.json()["document_id"]

    body = _verify(
        client,
        document_id,
    )

    assert body["status"] == "REVIEW_REQUIRED"