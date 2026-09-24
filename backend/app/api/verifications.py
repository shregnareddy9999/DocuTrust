"""Verify, review, verification history, and blockchain status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.extraction_service import UnknownCategoryError
from app.services.pipeline_service import (
    VerificationLookupError,
    get_blockchain_view,
    get_document_verifications_view,
    get_verification_view,
    review_and_record,
    verify_and_record,
)
from app.services.review_service import (
    EmptyReviewerRefError,
    InvalidReviewActionError,
    MissingCorrectionsError,
    UnknownCorrectionFieldError,
    VerificationNotFoundError,
)
from app.services.verification_service import (
    DocumentNotFoundError,
    ExtractionNotReadyError,
)

router = APIRouter()


def _http_error(
    status_code: int,
    code: str,
    message: str,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "details": {},
            }
        },
    )


@router.post("/documents/{document_id}/verify")
def post_verify(
    document_id: str,
    db: Session = Depends(get_db),
):
    try:
        row = verify_and_record(document_id, db)
    except DocumentNotFoundError:
        _http_error(404, "DOCUMENT_NOT_FOUND", "Document not found")
    except ExtractionNotReadyError:
        _http_error(409, "EXTRACTION_NOT_READY", "Extraction is not ready")
    except UnknownCategoryError:
        _http_error(500, "INTERNAL_ERROR", "Internal server error")

    status = row.status.value if hasattr(row.status, "value") else str(row.status)
    return {
        "verification_id": row.id,
        "status": status,
        "document_id": row.document_id,
    }


@router.post(
    "/verifications/{verification_id}/review",
    status_code=201,
)
def post_review(
    verification_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    reviewer_ref = payload.get("reviewer_ref")
    action = payload.get("action")
    corrections = payload.get("corrections")
    comment = payload.get("comment")

    if not isinstance(reviewer_ref, str) or not reviewer_ref.strip():
        _http_error(422, "EMPTY_REVIEWER_REF", "reviewer_ref is required")

    if not isinstance(action, str):
        _http_error(400, "INVALID_ACTION", "Invalid review action")

    if action == "CORRECT":
        if not isinstance(corrections, dict) or not corrections:
            _http_error(
                422,
                "MISSING_CORRECTIONS",
                "corrections are required for CORRECT",
            )

    try:
        review, new_verification = review_and_record(
            session=db,
            verification_id=verification_id,
            reviewer_ref=reviewer_ref,
            action=action,
            corrections=corrections,
            comment=comment,
        )
    except VerificationNotFoundError:
        _http_error(404, "VERIFICATION_NOT_FOUND", "Verification not found")
    except InvalidReviewActionError:
        _http_error(400, "INVALID_ACTION", "Invalid review action")
    except MissingCorrectionsError:
        _http_error(
            422,
            "MISSING_CORRECTIONS",
            "corrections are required for CORRECT",
        )
    except UnknownCorrectionFieldError as exc:
        _http_error(422, "UNKNOWN_CORRECTION_FIELD", str(exc))
    except EmptyReviewerRefError:
        _http_error(422, "EMPTY_REVIEWER_REF", "reviewer_ref is required")
    except Exception:
        db.rollback()
        _http_error(500, "INTERNAL_ERROR", "Internal server error")

    if new_verification is not None:
        new_verification_id = new_verification.id
        new_status = (
            new_verification.status.value
            if hasattr(new_verification.status, "value")
            else str(new_verification.status)
        )
    else:
        new_verification_id = None
        viewed = get_verification_view(db, verification_id)
        new_status = viewed["status"]

    return {
        "review_action_id": review.id,
        "new_verification_id": new_verification_id,
        "new_status": new_status,
    }


@router.get("/verifications/{verification_id}")
def get_verification(
    verification_id: str,
    db: Session = Depends(get_db),
):
    try:
        return get_verification_view(db, verification_id)
    except VerificationLookupError:
        _http_error(404, "VERIFICATION_NOT_FOUND", "Verification not found")


@router.get("/documents/{document_id}/verifications")
def get_document_verifications(
    document_id: str,
    db: Session = Depends(get_db),
):
    try:
        return get_document_verifications_view(db, document_id)
    except DocumentNotFoundError:
        _http_error(404, "DOCUMENT_NOT_FOUND", "Document not found")


@router.get("/verifications/{verification_id}/blockchain")
def get_verification_blockchain(
    verification_id: str,
    db: Session = Depends(get_db),
):
    try:
        return get_blockchain_view(db, verification_id)
    except VerificationLookupError:
        _http_error(404, "VERIFICATION_NOT_FOUND", "Verification not found")
