"""Task 10 orchestration: verify/review plus isolated chain recording."""

from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

import app.config as config_module
from app.models.document import ProcessingState
from app.models.extraction import ExtractionStatus
from app.repositories import (
    blockchain_repo,
    documents_repo,
    extraction_repo,
    registry_repo,
    review_repo,
    verification_repo,
)
from app.services.blockchain_service import submit_verification
from app.services.review_service import review_verification
from app.services.verification_service import (
    DocumentNotFoundError,
    ExtractionNotReadyError,
    verify_document,
)

logger = logging.getLogger(__name__)


class VerificationLookupError(ValueError):
    """No verification row for the requested id."""


def _iso_z(value) -> str | None:
    if value is None:
        return None
    text = value.isoformat()
    if text.endswith("Z") or "+" in text:
        return text
    return text + "Z"


def _parse_json_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _parse_json_object(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def record_verification_on_chain(session: Session, verification_id: str) -> None:
    """Submit a terminal verification. Never raises into the caller."""
    try:
        submit_verification(
            session,
            verification_id,
            enabled=bool(config_module.settings.BLOCKCHAIN_ENABLED),
            chain_id=config_module.settings.BLOCKCHAIN_CHAIN_ID,
            contract_address=config_module.settings.BLOCKCHAIN_CONTRACT_ADDRESS or "",
            chain_event_salt=config_module.settings.CHAIN_EVENT_SALT,
            timeout_seconds=config_module.settings.BLOCKCHAIN_TX_TIMEOUT_SECONDS,
        )
        session.commit()
    except Exception:
        logger.warning(
            "blockchain submission failed; verification %s left unchanged",
            verification_id,
        )
        try:
            session.rollback()
        except Exception:
            pass


def verify_and_record(document_id: str, session: Session):
    """Run Task 07 verify, then Task 09 submit without affecting the result."""
    row = verify_document(document_id, session)
    record_verification_on_chain(session, row.id)
    refreshed = verification_repo.get_by_id(session, row.id)
    return refreshed if refreshed is not None else row


def review_and_record(
    session: Session,
    verification_id: str,
    reviewer_ref: str,
    action: str,
    corrections: dict | None = None,
    comment: str | None = None,
):
    review, new_verification = review_verification(
        session=session,
        verification_id=verification_id,
        reviewer_ref=reviewer_ref,
        action=action,
        corrections=corrections,
        comment=comment,
    )
    if new_verification is not None:
        record_verification_on_chain(session, new_verification.id)
        refreshed = verification_repo.get_by_id(session, new_verification.id)
        if refreshed is not None:
            new_verification = refreshed
    return review, new_verification


def get_document_view(session: Session, document_id: str) -> dict:
    document = documents_repo.get_by_id(session, document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)
    uploaded = document.uploaded_at.isoformat()
    if not uploaded.endswith("Z") and "+" not in uploaded:
        uploaded = uploaded + "Z"
    return {
        "document_id": document.id,
        "category": _enum_value(document.category),
        "original_filename": document.original_filename,
        "processing_state": _enum_value(document.processing_state),
        "uploaded_at": uploaded,
    }


def get_extraction_view(session: Session, document_id: str) -> dict:
    document = documents_repo.get_by_id(session, document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)

    if document.processing_state == ProcessingState.OCR_IN_PROGRESS:
        raise ExtractionNotReadyError(document_id)

    extraction = extraction_repo.get_latest_for_document(session, document_id)

    if document.processing_state == ProcessingState.OCR_FAILED:
        return {
            "document_id": document.id,
            "engine_name": extraction.engine_name if extraction is not None else "",
            "engine_version": extraction.engine_version if extraction is not None else "",
            "extracted_fields": _parse_json_object(
                extraction.extracted_fields_json if extraction is not None else None
            ),
            "warnings": _parse_json_list(
                extraction.warnings_json if extraction is not None else None
            ),
            "status": ExtractionStatus.FAILED.value,
        }

    if extraction is None:
        raise ExtractionNotReadyError(document_id)

    return {
        "document_id": document.id,
        "engine_name": extraction.engine_name,
        "engine_version": extraction.engine_version,
        "extracted_fields": _parse_json_object(extraction.extracted_fields_json),
        "warnings": _parse_json_list(extraction.warnings_json),
        "status": _enum_value(extraction.status),
    }


def get_verification_view(session: Session, verification_id: str) -> dict:
    row = verification_repo.get_by_id(session, verification_id)
    if row is None:
        raise VerificationLookupError(verification_id)

    latest = verification_repo.get_latest_for_document(session, row.document_id)
    is_current = latest is not None and latest.id == row.id

    registry_key = None
    if row.registry_record_id:
        record = registry_repo.get_by_id(session, row.registry_record_id)
        if record is not None:
            registry_key = record.synthetic_record_key

    reviews = list(reversed(review_repo.list_for_verification(session, row.id)))
    review_actions = []
    for action in reviews:
        corrections = None
        if action.corrections_json:
            try:
                corrections = json.loads(action.corrections_json)
            except (json.JSONDecodeError, TypeError):
                corrections = {}
        review_actions.append(
            {
                "review_action_id": action.id,
                "reviewer_ref": action.reviewer_ref,
                "action": _enum_value(action.action),
                "corrections": corrections,
                "comment": action.comment,
                "created_at": _iso_z(action.created_at),
            }
        )

    return {
        "verification_id": row.id,
        "document_id": row.document_id,
        "status": _enum_value(row.status),
        "registry_record_key": registry_key,
        "field_comparisons": _parse_json_list(row.field_comparisons_json),
        "rule_results": _parse_json_list(row.rule_results_json),
        "reason_codes": _parse_json_list(row.reason_codes_json),
        "is_current": is_current,
        "supersedes_verification_id": row.supersedes_verification_id,
        "review_actions": review_actions,
        "created_at": _iso_z(row.created_at),
    }


def get_document_verifications_view(session: Session, document_id: str) -> dict:
    document = documents_repo.get_by_id(session, document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)

    rows = verification_repo.list_for_document(session, document_id)
    latest = verification_repo.get_latest_for_document(session, document_id)
    current_id = latest.id if latest is not None else None

    verifications = []
    for row in rows:
        verifications.append(
            {
                "verification_id": row.id,
                "status": _enum_value(row.status),
                "is_current": row.id == current_id,
                "supersedes_verification_id": row.supersedes_verification_id,
                "review_action_count": len(
                    review_repo.list_for_verification(session, row.id)
                ),
                "created_at": _iso_z(row.created_at),
            }
        )

    return {"document_id": document_id, "verifications": verifications}


def get_blockchain_view(session: Session, verification_id: str) -> dict:
    verification = verification_repo.get_by_id(session, verification_id)
    if verification is None:
        raise VerificationLookupError(verification_id)

    empty = {
        "verification_id": verification_id,
        "recording_status": "NOT_REQUESTED",
        "chain_id": None,
        "contract_address": None,
        "transaction_hash": None,
        "event_digest": None,
        "submitted_at": None,
        "confirmed_at": None,
        "error_code": None,
    }

    if not config_module.settings.BLOCKCHAIN_ENABLED:
        return empty

    record = blockchain_repo.get_active_for_verification(session, verification_id)
    if record is None:
        records = blockchain_repo.get_by_verification_id(session, verification_id)
        record = records[0] if records else None
    if record is None:
        return empty

    status = _enum_value(record.recording_status)
    if status == "NOT_REQUESTED":
        return empty

    error_code = None
    if record.error_code is not None:
        error_code = _enum_value(record.error_code)

    return {
        "verification_id": verification_id,
        "recording_status": status,
        "chain_id": record.chain_id,
        "contract_address": record.contract_address,
        "transaction_hash": record.transaction_hash,
        "event_digest": record.event_digest,
        "submitted_at": _iso_z(record.submitted_at) if record.submitted_at else None,
        "confirmed_at": _iso_z(record.confirmed_at) if record.confirmed_at else None,
        "error_code": error_code,
    }
