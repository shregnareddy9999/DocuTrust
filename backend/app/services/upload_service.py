"""Validate and store uploads.

Owned by Task 04 — see tasks/04-*.md.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pypdfium2 as pdfium
from PIL import Image
from fastapi import UploadFile

from app.config import settings
from app.models.document import Document, DocumentCategory, ProcessingState
from app.repositories.documents_repo import create as create_document


CHUNK_SIZE = 64 * 1024
MAGIC_BUFFER_SIZE = 8 * 1024

MIME_MAGIC = {
    b"%PDF-": "application/pdf",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
}

EXT_FROM_MIME = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}


class UploadError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _get_upload_dir() -> Path:
    return Path(settings.UPLOAD_DIR).resolve()


def _get_allowed_mime_types() -> set[str]:
    return set(settings.ALLOWED_MIME_TYPES)


def _get_max_bytes() -> int:
    return settings.MAX_UPLOAD_MB * 1024 * 1024


def _get_max_pdf_pages() -> int:
    return settings.MAX_PDF_PAGES


def safe_upload_path(storage_key: str) -> Path:
    """
    Resolve the full path for a storage_key and assert it stays inside UPLOAD_DIR.
    Raises ValueError if containment fails.
    """
    upload_dir = _get_upload_dir()
    target = (upload_dir / storage_key).resolve()
    if upload_dir not in target.parents and target != upload_dir:
        raise ValueError("Path traversal attempt detected")
    return target


def generate_storage_key(sniffed_mime: str) -> str:
    ext = EXT_FROM_MIME.get(sniffed_mime)
    if not ext:
        raise ValueError(f"Unsupported MIME type for storage: {sniffed_mime}")
    return f"{uuid4().hex}{ext}"


def generate_temp_key() -> str:
    return f"{uuid4().hex}.tmp"


def sniff_mime_type(file_path: Path) -> str | None:
    """Read magic bytes from file to determine MIME type."""
    with open(file_path, "rb") as f:
        header = f.read(MAGIC_BUFFER_SIZE)
    for magic, mime in MIME_MAGIC.items():
        if header.startswith(magic):
            return mime
    return None


def validate_image(file_path: Path) -> None:
    """Validate image file using Pillow verify(). Raises on corrupt/empty."""
    try:
        with Image.open(file_path) as img:
            img.verify()
    except Exception as e:
        raise UploadError(
            code="EMPTY_OR_CORRUPT_FILE",
            message="Image file is corrupt or empty",
            status_code=422,
        ) from e


def validate_pdf(file_path: Path) -> int:
    """
    Validate PDF file using pypdfium2. Returns page count.
    Raises on corrupt, encrypted, or page count exceeding limit.
    """
    try:
        pdf = pdfium.PdfDocument(str(file_path))
    except Exception as e:
        raise UploadError(
            code="EMPTY_OR_CORRUPT_FILE",
            message="PDF file is corrupt, encrypted, or unreadable",
            status_code=422,
        ) from e

    try:
        page_count = len(pdf)
    finally:
        pdf.close()

    max_pdf_pages = _get_max_pdf_pages()
    if page_count > max_pdf_pages:
        raise UploadError(
            code="FILE_TOO_LARGE",
            message=f"PDF page count ({page_count}) exceeds maximum allowed ({max_pdf_pages})",
            status_code=413,
        )

    return page_count


async def process_upload(file: UploadFile, category_str: str) -> Document:
    """
    Stream upload to temp file, validate, then atomically rename to final storage key.
    Creates Document row only after all validation passes.
    """
    valid_categories = {c.value for c in DocumentCategory}
    if category_str not in valid_categories:
        raise UploadError(
            code="INVALID_CATEGORY",
            message=f"Invalid category '{category_str}'. Must be one of: {', '.join(sorted(valid_categories))}",
            status_code=400,
        )

    category = DocumentCategory(category_str)

    temp_key = generate_temp_key()
    temp_path = safe_upload_path(temp_key)

    upload_dir = _get_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)

    sha256 = hashlib.sha256()
    byte_count = 0
    max_bytes = _get_max_bytes()
    allowed_mime_types = _get_allowed_mime_types()

    try:
        with open(temp_path, "wb") as out:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                byte_count += len(chunk)
                if byte_count > max_bytes:
                    raise UploadError(
                        code="FILE_TOO_LARGE",
                        message=f"File size exceeds maximum allowed ({settings.MAX_UPLOAD_MB} MB)",
                        status_code=413,
                    )
                sha256.update(chunk)
                out.write(chunk)

        if byte_count == 0:
            raise UploadError(
                code="EMPTY_OR_CORRUPT_FILE",
                message="Uploaded file is empty",
                status_code=422,
            )

        sniffed_mime = sniff_mime_type(temp_path)
        if not sniffed_mime or sniffed_mime not in allowed_mime_types:
            raise UploadError(
                code="UNSUPPORTED_MEDIA_TYPE",
                message=f"Unsupported file type. Allowed: {', '.join(sorted(allowed_mime_types))}",
                status_code=415,
            )

        # Check for mismatch between declared and sniffed MIME type
        declared_mime = file.content_type
        if declared_mime and declared_mime != sniffed_mime:
            raise UploadError(
                code="UNSUPPORTED_MEDIA_TYPE",
                message=f"Declared MIME type '{declared_mime}' does not match detected type '{sniffed_mime}'",
                status_code=415,
            )

        if sniffed_mime.startswith("image/"):
            validate_image(temp_path)
            page_count = 1
        else:
            page_count = validate_pdf(temp_path)

        storage_key = generate_storage_key(sniffed_mime)
        final_path = safe_upload_path(storage_key)

        temp_path.rename(final_path)

        document = Document(
            id=uuid4().hex,
            category=category,
            original_filename=file.filename or "unknown",
            storage_key=storage_key,
            sha256=sha256.hexdigest(),
            mime_type=sniffed_mime,
            byte_size=byte_count,
            page_count=page_count,
            processing_state=ProcessingState.UPLOADED,
            uploaded_at=datetime.now(timezone.utc),
        )

        from app.db import SessionLocal
        db = SessionLocal()
        try:
            created = create_document(db, document)
            db.commit()
            return created
        except Exception:
            db.rollback()
            final_path.unlink(missing_ok=True)
            raise
        finally:
            db.close()

    except UploadError:
        temp_path.unlink(missing_ok=True)
        raise
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise