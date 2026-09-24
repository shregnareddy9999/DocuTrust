"""End-to-end pipeline tests with fake OCR and fake chain — Task 10."""

from __future__ import annotations

import time
from io import BytesIO

from PIL import Image

from app.adapters.blockchain.fake_adapter import FakeBlockchainAdapter
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
from app.services.blockchain_service import OUTCOME_CODES


def _png_bytes(tint=255) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 64), color=(tint, tint, tint)).save(buffer, format="PNG")
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


def _install_shared_chain(monkeypatch):
    shared = FakeBlockchainAdapter(mode="success")

    def _factory(*args, **kwargs):
        return shared

    monkeypatch.setattr(
        "app.services.blockchain_service.FakeBlockchainAdapter",
        _factory,
    )
    return shared


def _upload(client, png=None):
    return client.post(
        "/api/v1/documents",
        files={"file": ("sample.png", png or _png_bytes(), "image/png")},
        data={"category": "academic_certificate"},
    ).json()["document_id"]


def _verify(client, document_id):
    response = client.post(f"/api/v1/documents/{document_id}/verify")
    assert response.status_code == 200
    return response.json()


def test_e2e_verified_match_chain_confirmed(
    client, monkeypatch, test_settings
):
    started = time.perf_counter()
    _enable_chain(test_settings)
    shared = _install_shared_chain(monkeypatch)
    _seed_registry()
    _use_ocr(monkeypatch)
    document_id = _upload(client)
    body = _verify(client, document_id)
    elapsed = time.perf_counter() - started
    assert elapsed < 15
    assert body["status"] == VerificationStatus.VERIFIED_MATCH.value
    chain = client.get(
        f"/api/v1/verifications/{body['verification_id']}/blockchain"
    ).json()
    assert chain["recording_status"] == "CONFIRMED"
    assert shared.submissions[-1][2] == OUTCOME_CODES[VerificationStatus.VERIFIED_MATCH]


def test_e2e_integrity_mismatch_outcome_code_3(
    client, monkeypatch, test_settings
):
    _enable_chain(test_settings)
    shared = _install_shared_chain(monkeypatch)
    _seed_registry()
    _use_ocr(monkeypatch, custom_text=_academic_text(**{"Semester / Year": "6"}))
    document_id = _upload(client, _png_bytes(250))
    body = _verify(client, document_id)
    assert body["status"] == VerificationStatus.INTEGRITY_MISMATCH.value
    chain = client.get(
        f"/api/v1/verifications/{body['verification_id']}/blockchain"
    ).json()
    assert chain["recording_status"] == "CONFIRMED"
    assert shared.submissions[-1][2] == 3


def test_e2e_no_trusted_record_outcome_code_2(
    client, monkeypatch, test_settings
):
    _enable_chain(test_settings)
    shared = _install_shared_chain(monkeypatch)
    _seed_registry()
    _use_ocr(monkeypatch, custom_text=_academic_text(**{"Student ID": "DEMO-STU-999"}))
    document_id = _upload(client, _png_bytes(240))
    body = _verify(client, document_id)
    assert body["status"] == VerificationStatus.NO_TRUSTED_RECORD.value
    chain = client.get(
        f"/api/v1/verifications/{body['verification_id']}/blockchain"
    ).json()
    assert chain["recording_status"] == "CONFIRMED"
    assert shared.submissions[-1][2] == 2


def test_e2e_low_confidence_correct_records_both_chain_events(
    client, monkeypatch, test_settings
):
    _enable_chain(test_settings)
    shared = _install_shared_chain(monkeypatch)
    _seed_registry()
    _use_misread_student_id_ocr(monkeypatch)
    document_id = _upload(client, _png_bytes(230))
    original = _verify(client, document_id)
    assert original["status"] == VerificationStatus.REVIEW_REQUIRED.value
    corrected = client.post(
        f"/api/v1/verifications/{original['verification_id']}/review",
        json={
            "reviewer_ref": "reviewer-001",
            "action": "CORRECT",
            "corrections": {"student_id": "DEMO-STU-001"},
        },
    )
    assert corrected.status_code == 201
    new_id = corrected.json()["new_verification_id"]
    assert new_id != original["verification_id"]
    assert corrected.json()["new_status"] == VerificationStatus.VERIFIED_MATCH.value

    old = client.get(
        f"/api/v1/verifications/{original['verification_id']}"
    ).json()
    assert old["status"] == VerificationStatus.REVIEW_REQUIRED.value
    assert old["is_current"] is False
    new = client.get(f"/api/v1/verifications/{new_id}").json()
    assert new["status"] == VerificationStatus.VERIFIED_MATCH.value
    assert new["supersedes_verification_id"] == original["verification_id"]

    first_chain = client.get(
        f"/api/v1/verifications/{original['verification_id']}/blockchain"
    ).json()
    second_chain = client.get(
        f"/api/v1/verifications/{new_id}/blockchain"
    ).json()
    assert first_chain["recording_status"] == "CONFIRMED"
    assert second_chain["recording_status"] == "CONFIRMED"
    assert len(shared.submissions) == 2


def test_e2e_ocr_failure_processing_failed(client, monkeypatch):
    _seed_registry()
    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_adapter",
        lambda: create_fake_adapter(mode="raises"),
    )
    document_id = _upload(client, _png_bytes(220))
    body = _verify(client, document_id)
    assert body["status"] == VerificationStatus.PROCESSING_FAILED.value
    extraction = client.get(f"/api/v1/documents/{document_id}/extraction")
    assert extraction.status_code == 200
    assert extraction.json()["status"] == "FAILED"
    meta = client.get(f"/api/v1/documents/{document_id}").json()
    assert meta["processing_state"] == "OCR_FAILED"
    assert meta["processing_state"] != "OCR_IN_PROGRESS"


def test_e2e_chain_unavailable_leaves_verification_unchanged(
    client, monkeypatch, test_settings
):
    _enable_chain(test_settings)
    _seed_registry()
    _use_ocr(monkeypatch)

    def _boom(*args, **kwargs):
        raise ConnectionError("RPC unavailable")

    monkeypatch.setattr(FakeBlockchainAdapter, "submit_event", _boom)

    document_id = _upload(client, _png_bytes(210))
    body = _verify(client, document_id)
    assert body["status"] == VerificationStatus.VERIFIED_MATCH.value
    detail = client.get(f"/api/v1/verifications/{body['verification_id']}").json()
    assert detail["status"] == VerificationStatus.VERIFIED_MATCH.value
    chain = client.get(
        f"/api/v1/verifications/{body['verification_id']}/blockchain"
    ).json()
    assert chain["recording_status"] == "FAILED"
    assert chain["error_code"] == "RPC_UNAVAILABLE"


def test_e2e_registry_error_is_processing_failed_not_no_record(
    client, monkeypatch
):
    _seed_registry()
    _use_ocr(monkeypatch)

    def _boom(*args, **kwargs):
        raise RuntimeError("database stopped")

    monkeypatch.setattr(
        "app.services.verification_service.registry_repo.list_active_by_category",
        _boom,
    )
    document_id = _upload(client, _png_bytes(200))
    body = _verify(client, document_id)
    assert body["status"] == VerificationStatus.PROCESSING_FAILED.value
    assert body["status"] != VerificationStatus.NO_TRUSTED_RECORD.value


def test_e2e_chain_on_or_off_same_verification_status(
    client, monkeypatch, test_settings
):
    _seed_registry()
    _use_ocr(monkeypatch)
    off_id = _upload(client, _png_bytes(190))
    off = _verify(client, off_id)
    assert off["status"] != VerificationStatus.PENDING.value

    _enable_chain(test_settings)
    _install_shared_chain(monkeypatch)
    on_id = _upload(client, _png_bytes(180))
    on = _verify(client, on_id)
    assert on["status"] == off["status"]
    off_detail = client.get(f"/api/v1/verifications/{off['verification_id']}").json()
    on_detail = client.get(f"/api/v1/verifications/{on['verification_id']}").json()
    assert off_detail["status"] == on_detail["status"]
    assert off_detail["reason_codes"] == on_detail["reason_codes"]
