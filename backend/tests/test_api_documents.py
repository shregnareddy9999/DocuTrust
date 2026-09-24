"""API contract tests for document endpoints — Task 10."""

from __future__ import annotations

from io import BytesIO

from PIL import Image


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 64), color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _upload(client, png=None, category="academic_certificate"):
    return client.post(
        "/api/v1/documents",
        files={"file": ("sample.png", png or _png_bytes(), "image/png")},
        data={"category": category},
    )


def test_health_shape(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "database", "ocr_adapter", "blockchain"}
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["ocr_adapter"] in ("configured", "fake", "paddleocr")
    assert body["blockchain"] in ("enabled", "disabled")


def test_document_types_shape(client):
    response = client.get("/api/v1/document-types")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    categories = {row["category"] for row in body}
    assert categories == {
        "academic_certificate",
        "institutional_id",
        "pan_like_demo",
        "government_certificate",
    }
    academic = next(row for row in body if row["category"] == "academic_certificate")
    field = academic["fields"][0]
    assert set(field) == {"name", "label", "type", "required", "match_field"}


def test_upload_returns_uploaded_and_does_not_run_ocr(client):
    response = _upload(client)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"document_id", "category", "processing_state"}
    assert body["category"] == "academic_certificate"
    assert body["processing_state"] == "UPLOADED"
    assert body["processing_state"] != "OCR_IN_PROGRESS"

    meta = client.get(f"/api/v1/documents/{body['document_id']}")
    assert meta.status_code == 200
    assert meta.json()["processing_state"] == "UPLOADED"

    extraction = client.get(f"/api/v1/documents/{body['document_id']}/extraction")
    assert extraction.status_code == 409
    assert extraction.json()["error"]["code"] == "EXTRACTION_NOT_READY"


def test_get_document_shape(client):
    document_id = _upload(client).json()["document_id"]
    response = client.get(f"/api/v1/documents/{document_id}")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "document_id",
        "category",
        "original_filename",
        "processing_state",
        "uploaded_at",
    }
    assert body["document_id"] == document_id
    assert body["uploaded_at"].endswith("Z")


def test_unknown_document_404(client):
    response = client.get("/api/v1/documents/ffffffffffffffffffffffffffffffff")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_extraction_unknown_document_404(client):
    response = client.get(
        "/api/v1/documents/ffffffffffffffffffffffffffffffff/extraction"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_verification_history_unknown_document_404(client):
    response = client.get(
        "/api/v1/documents/ffffffffffffffffffffffffffffffff/verifications"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_invalid_category(client):
    response = _upload(client, category="not_a_category")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CATEGORY"


def test_unsupported_media_type(client):
    response = client.post(
        "/api/v1/documents",
        files={"file": ("note.txt", b"plain text", "text/plain")},
        data={"category": "academic_certificate"},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_empty_file(client):
    response = client.post(
        "/api/v1/documents",
        files={"file": ("empty.png", b"", "image/png")},
        data={"category": "academic_certificate"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_OR_CORRUPT_FILE"


def test_oversized_file(client):
    response = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "huge.pdf",
                b"%PDF-1.4\n" + b"x" * (11 * 1024 * 1024),
                "application/pdf",
            )
        },
        data={"category": "academic_certificate"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_verification_history_empty_after_upload(client):
    document_id = _upload(client).json()["document_id"]
    response = client.get(f"/api/v1/documents/{document_id}/verifications")
    assert response.status_code == 200
    body = response.json()
    assert body == {"document_id": document_id, "verifications": []}
