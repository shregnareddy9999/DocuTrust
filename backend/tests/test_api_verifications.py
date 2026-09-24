"""API contract tests for verification endpoints — Task 10."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from app.adapters.ocr.base import OcrAdapter, OcrRegion, OcrResult
from app.adapters.ocr.fake_adapter import (
    _LABEL_X1,
    _LABEL_X2,
    _ROW_H,
    _ROW_Y0,
    _VALUE_X1,
    _VALUE_X2,
    _academic_two_column_rows,
    create_fake_adapter,
)
from app.models.verification import VerificationStatus


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 64), color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _seed_registry():
    from app.db import SessionLocal
    from app.fixtures import seed_registry

    session = SessionLocal()
    try:
        seed_registry.seed(session)
        session.commit()
    finally:
        session.close()


def _upload(client):
    return client.post(
        "/api/v1/documents",
        files={"file": ("sample.png", _png_bytes(), "image/png")},
        data={"category": "academic_certificate"},
    ).json()["document_id"]


def _academic_text(**overrides) -> str:
    fields = {
        "Student Name": "Aarav Demo",
        "Institution Name": "Example Technical Institute",
        "Student ID": "DEMO-STU-001",
        "Course": "B.Tech CSE",
        "Semester / Year": "5",
        "Certificate / Marksheet ID": "DEMO-MARK-001",
    }
    fields.update(overrides)
    return "\n".join(f"{label}: {value}" for label, value in fields.items())


def _use_ocr(monkeypatch, **kwargs):
    adapter = create_fake_adapter(mode="clean", **kwargs)
    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_adapter",
        lambda: adapter,
    )


def _use_misread_student_id_ocr(monkeypatch):
    class Adapter(OcrAdapter):
        def run(self, image):
            regions = []
            y = _ROW_Y0
            for label, value in _academic_two_column_rows():
                regions.append(
                    OcrRegion(label, 0.95, (_LABEL_X1, y, _LABEL_X2, y + 20), 1)
                )
                text = "DEMO-STU-OO1" if label == "Student ID" else value
                conf = 0.50 if label == "Student ID" else 0.95
                regions.append(
                    OcrRegion(text, conf, (_VALUE_X1, y, _VALUE_X2, y + 20), 1)
                )
                y += _ROW_H
            mean = sum(item.confidence for item in regions) / len(regions)
            return OcrResult(
                "\n".join(item.text for item in regions),
                regions,
                mean,
                "fake",
                "0.0.0-test",
                [],
            )

    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_adapter",
        lambda: Adapter(),
    )


def _enable_chain(test_settings):
    test_settings.BLOCKCHAIN_ENABLED = True
    test_settings.BLOCKCHAIN_CONTRACT_ADDRESS = "0xabcabcabcabcabcabcabcabcabcabcabcabcabca"


def test_verify_unknown_document_404(client):
    response = client.post(
        "/api/v1/documents/ffffffffffffffffffffffffffffffff/verify"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_get_verification_unknown_404(client):
    response = client.get("/api/v1/verifications/ffffffffffffffffffffffffffffffff")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VERIFICATION_NOT_FOUND"


def test_blockchain_unknown_verification_404(client):
    response = client.get(
        "/api/v1/verifications/ffffffffffffffffffffffffffffffff/blockchain"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VERIFICATION_NOT_FOUND"


def test_verified_match_is_http_200_not_pending(client, monkeypatch):
    _seed_registry()
    _use_ocr(monkeypatch)
    document_id = _upload(client)
    response = client.post(f"/api/v1/documents/{document_id}/verify")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"verification_id", "status", "document_id"}
    assert body["status"] == VerificationStatus.VERIFIED_MATCH.value
    assert body["status"] != VerificationStatus.PENDING.value

    detail = client.get(f"/api/v1/verifications/{body['verification_id']}")
    assert detail.status_code == 200
    payload = detail.json()
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
        assert key in payload
    assert payload["is_current"] is True
    assert payload["review_actions"] == []


def test_no_trusted_record_is_http_200(client, monkeypatch):
    _seed_registry()
    _use_ocr(monkeypatch, custom_text=_academic_text(**{"Student ID": "DEMO-STU-999"}))
    document_id = _upload(client)
    response = client.post(f"/api/v1/documents/{document_id}/verify")
    assert response.status_code == 200
    assert response.json()["status"] == VerificationStatus.NO_TRUSTED_RECORD.value


def test_integrity_mismatch_is_http_200(client, monkeypatch):
    _seed_registry()
    _use_ocr(monkeypatch, custom_text=_academic_text(**{"Semester / Year": "6"}))
    document_id = _upload(client)
    response = client.post(f"/api/v1/documents/{document_id}/verify")
    assert response.status_code == 200
    assert response.json()["status"] == VerificationStatus.INTEGRITY_MISMATCH.value


def test_review_required_is_http_200(client, monkeypatch):
    _seed_registry()
    _use_ocr(
        monkeypatch,
        custom_text=_academic_text(),
        custom_confidence=0.50,
    )
    document_id = _upload(client)
    response = client.post(f"/api/v1/documents/{document_id}/verify")
    assert response.status_code == 200
    assert response.json()["status"] == VerificationStatus.REVIEW_REQUIRED.value


def test_processing_failed_ocr_extraction_is_http_200_failed(client, monkeypatch):
    _seed_registry()
    _use_ocr(monkeypatch)
    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_adapter",
        lambda: create_fake_adapter(mode="raises"),
    )
    document_id = _upload(client)
    verify = client.post(f"/api/v1/documents/{document_id}/verify")
    assert verify.status_code == 200
    assert verify.json()["status"] == VerificationStatus.PROCESSING_FAILED.value
    assert verify.json()["status"] != VerificationStatus.NO_TRUSTED_RECORD.value
    assert verify.json()["status"] != VerificationStatus.INTEGRITY_MISMATCH.value

    extraction = client.get(f"/api/v1/documents/{document_id}/extraction")
    assert extraction.status_code == 200
    assert extraction.json()["status"] == "FAILED"

    meta = client.get(f"/api/v1/documents/{document_id}")
    assert meta.json()["processing_state"] != "OCR_IN_PROGRESS"


def test_review_accept_correct_unresolved(client, monkeypatch):
    _seed_registry()
    _use_misread_student_id_ocr(monkeypatch)
    document_id = _upload(client)
    original_id = client.post(
        f"/api/v1/documents/{document_id}/verify"
    ).json()["verification_id"]

    unresolved = client.post(
        f"/api/v1/verifications/{original_id}/review",
        json={"reviewer_ref": "r1", "action": "UNRESOLVED", "comment": "need more"},
    )
    assert unresolved.status_code == 201
    assert unresolved.json()["new_verification_id"] is None
    assert unresolved.json()["new_status"] == VerificationStatus.REVIEW_REQUIRED.value

    corrected = client.post(
        f"/api/v1/verifications/{original_id}/review",
        json={
            "reviewer_ref": "r2",
            "action": "CORRECT",
            "corrections": {"student_id": "DEMO-STU-001"},
        },
    )
    assert corrected.status_code == 201
    new_id = corrected.json()["new_verification_id"]
    assert new_id != original_id
    assert corrected.json()["new_status"] == VerificationStatus.VERIFIED_MATCH.value

    original = client.get(f"/api/v1/verifications/{original_id}").json()
    assert original["status"] == VerificationStatus.REVIEW_REQUIRED.value
    assert original["is_current"] is False
    actions = original["review_actions"]
    assert [row["action"] for row in actions] == ["UNRESOLVED", "CORRECT"]

    history = client.get(f"/api/v1/documents/{document_id}/verifications").json()
    assert history["verifications"][0]["is_current"] is True
    assert sum(1 for row in history["verifications"] if row["is_current"]) == 1


def test_accept_does_not_force_match_when_required_missing(client, monkeypatch):
    _seed_registry()
    _use_ocr(monkeypatch, custom_text=_academic_text(**{"Student Name": ""}))
    document_id = _upload(client)
    original_id = client.post(
        f"/api/v1/documents/{document_id}/verify"
    ).json()["verification_id"]
    response = client.post(
        f"/api/v1/verifications/{original_id}/review",
        json={"reviewer_ref": "r1", "action": "ACCEPT"},
    )
    assert response.status_code == 201
    assert response.json()["new_verification_id"] != original_id
    assert response.json()["new_status"] == VerificationStatus.REVIEW_REQUIRED.value


def test_blockchain_disabled_is_not_requested(client, monkeypatch):
    _seed_registry()
    _use_ocr(monkeypatch)
    document_id = _upload(client)
    verification_id = client.post(
        f"/api/v1/documents/{document_id}/verify"
    ).json()["verification_id"]
    response = client.get(f"/api/v1/verifications/{verification_id}/blockchain")
    assert response.status_code == 200
    body = response.json()
    assert body["recording_status"] == "NOT_REQUESTED"
    assert body["chain_id"] is None
    assert body["contract_address"] is None
    assert body["transaction_hash"] is None
    assert body["event_digest"] is None
    assert body["submitted_at"] is None
    assert body["confirmed_at"] is None
    assert body["error_code"] is None


def test_blockchain_enabled_confirmed(client, monkeypatch, test_settings):
    _enable_chain(test_settings)
    _seed_registry()
    _use_ocr(monkeypatch)
    document_id = _upload(client)
    verification_id = client.post(
        f"/api/v1/documents/{document_id}/verify"
    ).json()["verification_id"]
    body = client.get(f"/api/v1/verifications/{verification_id}/blockchain").json()
    assert body["recording_status"] == "CONFIRMED"
    assert body["error_code"] is None
    assert body["transaction_hash"]
