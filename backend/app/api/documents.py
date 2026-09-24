"""Document upload and retrieval endpoints.

Owned by Task 04 — see tasks/04-*.md.
GET /documents/{id}/extraction is Task 06 (read-only; does not run OCR or mapping).
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.pipeline_service import (
    get_document_view,
    get_extraction_view,
)
from app.services.upload_service import UploadError, process_upload
from app.services.verification_service import (
    DocumentNotFoundError,
    ExtractionNotReadyError,
)

router = APIRouter()


def _http_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": {}}},
    )


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        document = await process_upload(file, category)
        return {
            "document_id": document.id,
            "category": document.category.value,
            "processing_state": document.processing_state.value,
        }
    except UploadError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": {"code": e.code, "message": e.message, "details": {}}},
        ) from e


@router.get("/documents/{document_id}")
async def get_document(document_id: str, db: Session = Depends(get_db)):
    try:
        return get_document_view(db, document_id)
    except DocumentNotFoundError:
        _http_error(404, "DOCUMENT_NOT_FOUND", "Document not found")


@router.get("/documents/{document_id}/extraction")
async def get_extraction(document_id: str, db: Session = Depends(get_db)):
    """Read the latest persisted extraction. Does not run OCR or mapping."""
    try:
        return get_extraction_view(db, document_id)
    except DocumentNotFoundError:
        _http_error(404, "DOCUMENT_NOT_FOUND", "Document not found")
    except ExtractionNotReadyError:
        _http_error(409, "EXTRACTION_NOT_READY", "Extraction is not ready")
