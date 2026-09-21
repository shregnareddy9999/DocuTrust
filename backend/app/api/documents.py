"""Document upload and retrieval endpoints.

Owned by Task 04 — see tasks/04-*.md.
GET /documents/{id}/extraction is Task 06 (read-only; does not run OCR or mapping).
"""

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.document import ProcessingState
from app.models.extraction import ExtractionResult
from app.repositories.documents_repo import get_by_id
from app.repositories.extraction_repo import get_latest_for_document
from app.services.upload_service import UploadError, process_upload

router = APIRouter()


def _http_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": {}}},
    )


def _parse_extracted_fields(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_warnings(raw: str | None) -> list:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _extraction_response(document_id: str, extraction: ExtractionResult | None, *, status_value: str):
    if extraction is None:
        return {
            "document_id": document_id,
            "engine_name": "",
            "engine_version": "",
            "extracted_fields": {},
            "warnings": [],
            "status": status_value,
        }
    return {
        "document_id": document_id,
        "engine_name": extraction.engine_name,
        "engine_version": extraction.engine_version,
        "extracted_fields": _parse_extracted_fields(extraction.extracted_fields_json),
        "warnings": _parse_warnings(extraction.warnings_json),
        "status": extraction.status.value if hasattr(extraction.status, "value") else str(extraction.status),
    }


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


@router.get("/documents/{document_id}/extraction")
async def get_extraction(document_id: str, db: Session = Depends(get_db)):
    """Read the latest persisted extraction. Does not run OCR or mapping."""
    document = get_by_id(db, document_id)
    if not document:
        _http_error(404, "DOCUMENT_NOT_FOUND", "Document not found")

    if document.processing_state == ProcessingState.OCR_IN_PROGRESS:
        _http_error(409, "EXTRACTION_NOT_READY", "Extraction is not ready")

    extraction = get_latest_for_document(db, document_id)

    if document.processing_state == ProcessingState.OCR_FAILED:
        payload = _extraction_response(document.id, extraction, status_value="FAILED")
        payload["status"] = "FAILED"
        return payload

    if extraction is None:
        _http_error(409, "EXTRACTION_NOT_READY", "Extraction is not ready")

    return _extraction_response(
        document.id,
        extraction,
        status_value=extraction.status.value
        if hasattr(extraction.status, "value")
        else str(extraction.status),
    )