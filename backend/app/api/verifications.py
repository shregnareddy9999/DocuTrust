"""POST /documents/{id}/verify and review endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories import registry_repo, review_repo, verification_repo
from app.services.extraction_service import UnknownCategoryError
from app.services.review_service import (
    EmptyReviewerRefError,
    InvalidReviewActionError,
    MissingCorrectionsError,
    UnknownCorrectionFieldError,
    VerificationNotFoundError,
    review_verification,
)
from app.services.verification_service import (
    DocumentNotFoundError,
    ExtractionNotReadyError,
    verify_document,
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


def _parse_list(raw: str | None) -> list:
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []

    return parsed if isinstance(parsed, list) else []


def _iso_z(value) -> str:
    if value is None:
        return ""

    text = value.isoformat()

    if text.endswith("Z"):
        return text

    if "+" in text:
        return text

    return text + "Z"


@router.post("/documents/{document_id}/verify")
def post_verify(
    document_id: str,
    db: Session = Depends(get_db),
):
    try:
        row = verify_document(document_id, db)

    except DocumentNotFoundError:
        _http_error(
            404,
            "DOCUMENT_NOT_FOUND",
            "Document not found",
        )

    except ExtractionNotReadyError:
        _http_error(
            409,
            "EXTRACTION_NOT_READY",
            "Extraction is not ready",
        )

    except UnknownCategoryError:
        _http_error(
            500,
            "INTERNAL_ERROR",
            str(exc),
        )

    status = (
        row.status.value
        if hasattr(row.status, "value")
        else str(row.status)
    )

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
        _http_error(
            422,
            "EMPTY_REVIEWER_REF",
            "reviewer_ref is required",
        )

    if not isinstance(action, str):
        _http_error(
            400,
            "INVALID_ACTION",
            "Invalid review action",
        )

    if action == "CORRECT":
        if not isinstance(corrections, dict) or not corrections:
            _http_error(
                422,
                "MISSING_CORRECTIONS",
                "corrections are required for CORRECT",
            )

    try:
        review, new_verification = review_verification(
            session=db,
            verification_id=verification_id,
            reviewer_ref=reviewer_ref,
            action=action,
            corrections=corrections,
            comment=comment,
        )

    except VerificationNotFoundError:
        _http_error(
            404,
            "VERIFICATION_NOT_FOUND",
            "Verification not found",
        )

    except InvalidReviewActionError:
        _http_error(
            400,
            "INVALID_ACTION",
            "Invalid review action",
        )

    except MissingCorrectionsError:
        _http_error(
            422,
            "MISSING_CORRECTIONS",
            "corrections are required for CORRECT",
        )

    except UnknownCorrectionFieldError as exc:
        _http_error(
            422,
            "UNKNOWN_CORRECTION_FIELD",
            str(exc),
        )

    except EmptyReviewerRefError:
        _http_error(
            422,
            "EMPTY_REVIEWER_REF",
            "reviewer_ref is required",
        )

    except Exception as exc:
        db.rollback()
        _http_error(
            500,
            "INTERNAL_ERROR",
            str(exc),
        )

    if new_verification is not None:
        new_verification_id = new_verification.id
        new_status = new_verification.status.value
    else:
        new_verification_id = None
        reviewed = verification_repo.get_by_id(db, verification_id)
        new_status = reviewed.status.value if reviewed is not None else None

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
    row = verification_repo.get_by_id(
        db,
        verification_id,
    )

    if row is None:
        _http_error(
            404,
            "VERIFICATION_NOT_FOUND",
            "Verification not found",
        )

    latest = verification_repo.get_latest_for_document(
        db,
        row.document_id,
    )

    is_current = (
        latest is not None
        and latest.id == row.id
    )

    registry_key = None

    if row.registry_record_id:
        record = registry_repo.get_by_id(
            db,
            row.registry_record_id,
        )

        if record is not None:
            registry_key = record.synthetic_record_key

    reviews = review_repo.list_for_verification(
        db,
        row.id,
    )

    review_actions = []

    for action in reviews:
        corrections = None

        if action.corrections_json:
            try:
                corrections = json.loads(
                    action.corrections_json
                )
            except (
                json.JSONDecodeError,
                TypeError,
            ):
                corrections = {}

        review_actions.append(
            {
                "review_action_id": action.id,
                "reviewer_ref": action.reviewer_ref,
                "action": (
                    action.action.value
                    if hasattr(action.action, "value")
                    else str(action.action)
                ),
                "corrections": corrections,
                "comment": action.comment,
                "created_at": _iso_z(
                    action.created_at
                ),
            }
        )

    status = (
        row.status.value
        if hasattr(row.status, "value")
        else str(row.status)
    )

    return {
        "verification_id": row.id,
        "document_id": row.document_id,
        "status": status,
        "registry_record_key": registry_key,
        "field_comparisons": _parse_list(
            row.field_comparisons_json
        ),
        "rule_results": _parse_list(
            row.rule_results_json
        ),
        "reason_codes": _parse_list(
            row.reason_codes_json
        ),
        "is_current": is_current,
        "supersedes_verification_id": (
            row.supersedes_verification_id
        ),
        "review_actions": review_actions,
        "created_at": _iso_z(
            row.created_at
        ),
    }


