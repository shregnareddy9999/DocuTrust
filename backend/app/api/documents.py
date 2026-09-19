"""Document upload and retrieval endpoints.

Owned by Task 04 — see tasks/04-*.md.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories.documents_repo import get_by_id
from app.services.upload_service import UploadError, process_upload

router = APIRouter()


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
    document = get_by_id(db, document_id)
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "DOCUMENT_NOT_FOUND", "message": "Document not found", "details": {}}},
        )
    return {
        "document_id": document.id,
        "category": document.category.value,
        "original_filename": document.original_filename,
        "processing_state": document.processing_state.value,
        "uploaded_at": document.uploaded_at.isoformat() + "Z",
    }