"""Tests for secure upload and file handling (Task 04)."""

import io
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.db import Base
from app.main import app
from app.models.document import Document, DocumentCategory, ProcessingState
from app.repositories.documents_repo import get_by_id
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


# Resolve fixtures relative to this test file so the tests work regardless
# of the directory from which pytest is launched.
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def make_test_engine(database_url: str):
    test_engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(test_engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return test_engine


@pytest.fixture(scope="function")
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def temp_upload_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="function")
def test_settings(
    temp_db_path: str,
    temp_upload_dir: Path,
) -> Settings:
    return Settings(
        APP_ENV="test",
        DATABASE_URL=f"sqlite:///{temp_db_path}",
        UPLOAD_DIR=str(temp_upload_dir),
        MAX_UPLOAD_MB=10,
        MAX_PDF_PAGES=5,
        ALLOWED_MIME_TYPES=[
            "image/jpeg",
            "image/png",
            "application/pdf",
        ],
        OCR_ENGINE="paddleocr",
        OCR_LANGUAGE="en",
        OCR_TIMEOUT_SECONDS=30,
        LOW_CONFIDENCE_THRESHOLD=0.70,
        REGISTRY_MODE="synthetic_demo",
        BLOCKCHAIN_ENABLED=False,
        BLOCKCHAIN_RPC_URL="http://127.0.0.1:8545",
        BLOCKCHAIN_CHAIN_ID=31337,
        BLOCKCHAIN_CONTRACT_ADDRESS="",
        BLOCKCHAIN_TX_TIMEOUT_SECONDS=30,
        BLOCKCHAIN_MAX_RETRIES=2,
        CHAIN_EVENT_SALT="test_salt_" + "0" * 56,
        RETENTION_DAYS=7,
        LOG_LEVEL="DEBUG",
    )


@pytest.fixture(scope="function")
def db_session(temp_db_path: str):
    test_engine = make_test_engine(
        f"sqlite:///{temp_db_path}"
    )

    Base.metadata.create_all(
        bind=test_engine
    )

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        test_engine.dispose()


def create_valid_png() -> bytes:
    img = Image.new(
        "RGB",
        (100, 100),
        color="red",
    )

    buf = io.BytesIO()

    img.save(
        buf,
        format="PNG",
    )

    return buf.getvalue()


def create_valid_jpeg() -> bytes:
    img = Image.new(
        "RGB",
        (100, 100),
        color="blue",
    )

    buf = io.BytesIO()

    img.save(
        buf,
        format="JPEG",
    )

    return buf.getvalue()


class TestHappyPaths:
    def test_upload_valid_png(
        self,
        client: TestClient,
        temp_upload_dir: Path,
        db_session,
    ):
        png_data = create_valid_png()

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "test.png",
                    png_data,
                    "image/png",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert "document_id" in data
        assert data["category"] == "academic_certificate"
        assert data["processing_state"] == "UPLOADED"

        doc_id = data["document_id"]

        doc = get_by_id(
            db_session,
            doc_id,
        )

        assert doc is not None
        assert doc.category.value == "academic_certificate"
        assert doc.mime_type == "image/png"
        assert doc.byte_size == len(png_data)
        assert doc.page_count == 1
        assert doc.processing_state == ProcessingState.UPLOADED
        assert doc.sha256

        stored_files = list(
            temp_upload_dir.iterdir()
        )

        assert len(stored_files) == 1
        assert stored_files[0].name == doc.storage_key
        assert stored_files[0].suffix == ".png"
        assert stored_files[0].read_bytes() == png_data

    def test_upload_valid_single_page_pdf(
        self,
        client: TestClient,
        temp_upload_dir: Path,
        db_session,
    ):
        pdf_path = (
            FIXTURES_DIR / "multi_page_6.pdf"
        )

        pdf_data = pdf_path.read_bytes()[:100000]

        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(
            str(pdf_path)
        )

        single_page_pdf = pdfium.PdfDocument.new()

        page = single_page_pdf.new_page(
            595,
            842,
        )

        page.close()

        buf = io.BytesIO()

        single_page_pdf.save(buf)

        single_page_pdf.close()
        pdf.close()

        pdf_data = buf.getvalue()

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "test.pdf",
                    pdf_data,
                    "application/pdf",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 201

        data = response.json()

        doc_id = data["document_id"]

        doc = get_by_id(
            db_session,
            doc_id,
        )

        assert doc.page_count == 1

    def test_upload_valid_jpeg(
        self,
        client: TestClient,
        temp_upload_dir: Path,
        db_session,
    ):
        jpeg_data = create_valid_jpeg()

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "test.jpg",
                    jpeg_data,
                    "image/jpeg",
                )
            },
            data={
                "category": "institutional_id",
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["category"] == "institutional_id"

        doc = get_by_id(
            db_session,
            data["document_id"],
        )

        assert doc.mime_type == "image/jpeg"
        assert doc.page_count == 1


class TestRejectionCases:
    def test_invalid_category(
        self,
        client: TestClient,
        temp_upload_dir: Path,
    ):
        png_data = create_valid_png()

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "test.png",
                    png_data,
                    "image/png",
                )
            },
            data={
                "category": "invalid_category",
            },
        )

        assert response.status_code == 400

        data = response.json()

        assert data["error"]["code"] == "INVALID_CATEGORY"
        assert (
            "invalid_category"
            in data["error"]["message"]
        )

        assert len(
            list(temp_upload_dir.iterdir())
        ) == 0

    def test_file_over_size_limit(
        self,
        client: TestClient,
        temp_upload_dir: Path,
    ):
        large_data = b"x" * (
            11 * 1024 * 1024
        )

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "large.bin",
                    large_data,
                    "application/octet-stream",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 413

        data = response.json()

        assert (
            data["error"]["code"]
            == "FILE_TOO_LARGE"
        )

        assert len(
            list(temp_upload_dir.iterdir())
        ) == 0

    def test_pdf_over_page_limit(
        self,
        client: TestClient,
        temp_upload_dir: Path,
    ):
        pdf_path = (
            FIXTURES_DIR / "multi_page_6.pdf"
        )

        pdf_data = pdf_path.read_bytes()

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "test.pdf",
                    pdf_data,
                    "application/pdf",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 413

        data = response.json()

        assert (
            data["error"]["code"]
            == "FILE_TOO_LARGE"
        )

        assert (
            "page"
            in data["error"]["message"].lower()
        )

        assert len(
            list(temp_upload_dir.iterdir())
        ) == 0

    def test_txt_file(
        self,
        client: TestClient,
        temp_upload_dir: Path,
    ):
        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "test.txt",
                    b"plain text",
                    "text/plain",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 415

        data = response.json()

        assert (
            data["error"]["code"]
            == "UNSUPPORTED_MEDIA_TYPE"
        )

        assert len(
            list(temp_upload_dir.iterdir())
        ) == 0

    def test_pdf_renamed_png(
        self,
        client: TestClient,
        temp_upload_dir: Path,
    ):
        pdf_path = (
            FIXTURES_DIR / "single_page.pdf"
        )

        pdf_data = pdf_path.read_bytes()

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "fake.png",
                    pdf_data,
                    "image/png",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 415

        data = response.json()

        assert (
            data["error"]["code"]
            == "UNSUPPORTED_MEDIA_TYPE"
        )

        assert len(
            list(temp_upload_dir.iterdir())
        ) == 0

    def test_zero_byte_file(
        self,
        client: TestClient,
        temp_upload_dir: Path,
    ):
        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "empty.png",
                    b"",
                    "image/png",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 422

        data = response.json()

        assert (
            data["error"]["code"]
            == "EMPTY_OR_CORRUPT_FILE"
        )

        assert len(
            list(temp_upload_dir.iterdir())
        ) == 0

    def test_corrupt_truncated_png(
        self,
        client: TestClient,
        temp_upload_dir: Path,
    ):
        corrupt_path = (
            FIXTURES_DIR / "corrupt.png"
        )

        corrupt_data = corrupt_path.read_bytes()

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "corrupt.png",
                    corrupt_data,
                    "image/png",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 422

        data = response.json()

        assert (
            data["error"]["code"]
            == "EMPTY_OR_CORRUPT_FILE"
        )

        assert len(
            list(temp_upload_dir.iterdir())
        ) == 0

    def test_encrypted_pdf(
        self,
        client: TestClient,
        temp_upload_dir: Path,
    ):
        pdf_path = (
            FIXTURES_DIR / "encrypted.pdf"
        )

        pdf_data = pdf_path.read_bytes()

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "encrypted.pdf",
                    pdf_data,
                    "application/pdf",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 422

        data = response.json()

        assert (
            data["error"]["code"]
            == "EMPTY_OR_CORRUPT_FILE"
        )

        assert len(
            list(temp_upload_dir.iterdir())
        ) == 0


class TestSecurityCases:
    def test_path_traversal_filename(
        self,
        client: TestClient,
        temp_upload_dir: Path,
        db_session,
    ):
        png_data = create_valid_png()

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "../../../etc/passwd",
                    png_data,
                    "image/png",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 201

        doc_id = response.json()["document_id"]

        doc = get_by_id(
            db_session,
            doc_id,
        )

        assert doc.storage_key.endswith(".png")
        assert "etc" not in doc.storage_key
        assert "passwd" not in doc.storage_key
        assert "../" not in doc.storage_key

        stored = list(
            temp_upload_dir.iterdir()
        )

        assert len(stored) == 1
        assert stored[0].name == doc.storage_key

    def test_null_byte_filename(
        self,
        client: TestClient,
        temp_upload_dir: Path,
        db_session,
    ):
        png_data = create_valid_png()

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "test\x00.png",
                    png_data,
                    "image/png",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 201

        doc = get_by_id(
            db_session,
            response.json()["document_id"],
        )

        assert "\x00" not in doc.storage_key

    def test_very_long_filename(
        self,
        client: TestClient,
        temp_upload_dir: Path,
        db_session,
    ):
        png_data = create_valid_png()

        long_name = (
            "a" * 500
            + ".png"
        )

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    long_name,
                    png_data,
                    "image/png",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 201

        doc = get_by_id(
            db_session,
            response.json()["document_id"],
        )

        assert len(doc.storage_key) < 100

    def test_duplicate_content_separate_rows(
        self,
        client: TestClient,
        temp_upload_dir: Path,
        db_session,
    ):
        png_data = create_valid_png()

        resp1 = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "test1.png",
                    png_data,
                    "image/png",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        resp2 = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "test2.png",
                    png_data,
                    "image/png",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert resp1.status_code == 201
        assert resp2.status_code == 201

        id1 = resp1.json()["document_id"]
        id2 = resp2.json()["document_id"]

        assert id1 != id2

        doc1 = get_by_id(
            db_session,
            id1,
        )

        doc2 = get_by_id(
            db_session,
            id2,
        )

        assert doc1.storage_key != doc2.storage_key
        assert doc1.sha256 == doc2.sha256

    def test_rejection_leaves_no_row_no_file(
        self,
        client: TestClient,
        temp_upload_dir: Path,
        db_session,
    ):
        test_cases = [
            (
                {"category": "bad_cat"},
                400,
                "INVALID_CATEGORY",
            ),
            (
                {
                    "file": (
                        "x",
                        b"x" * 11 * 1024 * 1024,
                        "application/pdf",
                    )
                },
                413,
                "FILE_TOO_LARGE",
            ),
            (
                {
                    "file": (
                        "x.pdf",
                        (
                            FIXTURES_DIR
                            / "multi_page_6.pdf"
                        ).read_bytes(),
                        "application/pdf",
                    )
                },
                413,
                "FILE_TOO_LARGE",
            ),
            (
                {
                    "file": (
                        "x.txt",
                        b"text",
                        "text/plain",
                    )
                },
                415,
                "UNSUPPORTED_MEDIA_TYPE",
            ),
            (
                {
                    "file": (
                        "fake.png",
                        (
                            FIXTURES_DIR
                            / "single_page.pdf"
                        ).read_bytes(),
                        "image/png",
                    )
                },
                415,
                "UNSUPPORTED_MEDIA_TYPE",
            ),
            (
                {
                    "file": (
                        "empty.png",
                        b"",
                        "image/png",
                    )
                },
                422,
                "EMPTY_OR_CORRUPT_FILE",
            ),
            (
                {
                    "file": (
                        "corrupt.png",
                        (
                            FIXTURES_DIR
                            / "corrupt.png"
                        ).read_bytes(),
                        "image/png",
                    )
                },
                422,
                "EMPTY_OR_CORRUPT_FILE",
            ),
            (
                {
                    "file": (
                        "encrypted.pdf",
                        (
                            FIXTURES_DIR
                            / "encrypted.pdf"
                        ).read_bytes(),
                        "application/pdf",
                    )
                },
                422,
                "EMPTY_OR_CORRUPT_FILE",
            ),
        ]

        for (
            extra,
            expected_status,
            expected_code,
        ) in test_cases:
            files = {
                "file": (
                    "test.png",
                    create_valid_png(),
                    "image/png",
                )
            }

            files.update(
                {
                    key: value
                    for key, value in extra.items()
                    if key == "file"
                }
            )

            data = {
                "category": "academic_certificate",
            }

            data.update(
                {
                    key: value
                    for key, value in extra.items()
                    if key != "file"
                }
            )

            response = client.post(
                "/api/v1/documents",
                files=files,
                data=data,
            )

            assert (
                response.status_code
                == expected_status
            )

            assert (
                response.json()["error"]["code"]
                == expected_code
            )

            assert len(
                list(temp_upload_dir.iterdir())
            ) == 0

            count = (
                db_session
                .query(Document)
                .count()
            )

            assert count == 0


class TestRetrieval:
    def test_get_existing_document(
        self,
        client: TestClient,
        temp_upload_dir: Path,
        db_session,
    ):
        png_data = create_valid_png()

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "test.png",
                    png_data,
                    "image/png",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        doc_id = response.json()["document_id"]

        response = client.get(
            f"/api/v1/documents/{doc_id}"
        )

        assert response.status_code == 200

        data = response.json()

        assert data["document_id"] == doc_id
        assert (
            data["category"]
            == "academic_certificate"
        )
        assert (
            data["original_filename"]
            == "test.png"
        )
        assert (
            data["processing_state"]
            == "UPLOADED"
        )
        assert "uploaded_at" in data
        assert "storage_key" not in data
        assert "sha256" not in data
        assert "byte_size" not in data
        assert "page_count" not in data

    def test_get_unknown_document(
        self,
        client: TestClient,
    ):
        response = client.get(
            "/api/v1/documents/nonexistent"
        )

        assert response.status_code == 404

        data = response.json()

        assert (
            data["error"]["code"]
            == "DOCUMENT_NOT_FOUND"
        )


class TestTempFileCleanup:
    def test_no_temp_files_after_rejection(
        self,
        client: TestClient,
        temp_upload_dir: Path,
    ):
        large_data = b"x" * (
            11 * 1024 * 1024
        )

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "large.bin",
                    large_data,
                    "application/pdf",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 413

        tmp_files = list(
            temp_upload_dir.glob("*.tmp")
        )

        assert len(tmp_files) == 0

    def test_no_temp_files_after_success(
        self,
        client: TestClient,
        temp_upload_dir: Path,
    ):
        png_data = create_valid_png()

        response = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "test.png",
                    png_data,
                    "image/png",
                )
            },
            data={
                "category": "academic_certificate",
            },
        )

        assert response.status_code == 201

        tmp_files = list(
            temp_upload_dir.glob("*.tmp")
        )

        assert len(tmp_files) == 0

        stored = list(
            temp_upload_dir.iterdir()
        )

        assert len(stored) == 1
        assert not stored[0].name.endswith(
            ".tmp"
        )