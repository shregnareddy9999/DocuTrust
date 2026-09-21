"""Orchestrate matching and rules. Persist a new verification row per run."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.domain.matching import find_applicable_record
from app.domain.rules import (
    VerificationOutcome,
    evaluate,
    run_rules,
)
from app.domain.schemas import SCHEMA_REGISTRY, get_schema
from app.domain.status import VerificationStatus
from app.models.document import ProcessingState
from app.models.extraction import ExtractionStatus
from app.models.verification import VerificationResult
from app.models.verification import VerificationStatus as ModelVerificationStatus
from app.repositories import documents_repo, extraction_repo, registry_repo, verification_repo
from app.services.extraction_service import UnknownCategoryError, extract_fields
from app.services.ocr_service import OcrProcessingError, process_document


class DocumentNotFoundError(Exception):
    """No document row for the requested id."""


class ExtractionNotReadyError(Exception):
    """No successful extraction is available to verify."""


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_json_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _category_value(document) -> str:
    category = document.category
    return category.value if hasattr(category, "value") else str(category)


def _registry_as_dict(record) -> dict[str, Any]:
    return {
        "id": record.id,
        "category": _category_value(record) if hasattr(record, "category") else record.category,
        "active": record.active,
        "synthetic_record_key": record.synthetic_record_key,
        "fields": _parse_json_object(record.fields_json),
    }


def _rule_payload(outcome: VerificationOutcome) -> list[dict[str, Any]]:
    return [
        {
            "rule_id": result.rule_id,
            "passed": result.passed,
            "reason": result.reason,
        }
        for result in outcome.rule_results
    ]


def _persist(
    session: Session,
    document_id: str,
    outcome: VerificationOutcome,
) -> VerificationResult:
    registry_id = None
    if outcome.registry_record is not None:
        registry_id = outcome.registry_record.get("id")
    row = VerificationResult(
        document_id=document_id,
        registry_record_id=registry_id,
        status=ModelVerificationStatus(outcome.status.value),
        field_comparisons_json=json.dumps(outcome.field_comparisons),
        rule_results_json=json.dumps(_rule_payload(outcome)),
        reason_codes_json=json.dumps(outcome.reason_codes),
        supersedes_verification_id=None,
        created_at=_now(),
    )
    verification_repo.create(session, row)
    session.commit()
    session.refresh(row)
    return row


def _failed_technical(
    extracted_fields: dict,
    schema: list,
    reason_code: str,
) -> VerificationOutcome:
    match = find_applicable_record(
        "",
        extracted_fields,
        [],
        schema,
    )
    return VerificationOutcome(
        status=VerificationStatus.PROCESSING_FAILED,
        field_comparisons=match.comparisons,
        rule_results=run_rules(extracted_fields, None, schema),
        reason_codes=[reason_code],
        registry_record=None,
    )


def _persist_extraction_failed(
    session: Session,
    document_id: str,
    category: str,
    schema: list,
    extracted_fields: dict,
) -> VerificationResult:
    match = find_applicable_record(category, extracted_fields, [], schema)
    outcome = evaluate(
        ExtractionStatus.FAILED.value,
        extracted_fields,
        match,
        schema,
        settings.LOW_CONFIDENCE_THRESHOLD,
    )
    return _persist(session, document_id, outcome)


def verify_document(document_id: str, session: Session) -> VerificationResult:
    """Run OCR if needed, then matching and rules. Always inserts a new terminal row."""
    document = documents_repo.get_by_id(session, document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)

    category = _category_value(document)
    if category not in SCHEMA_REGISTRY:
        raise UnknownCategoryError(category)

    schema = get_schema(category)

    if document.processing_state == ProcessingState.OCR_IN_PROGRESS:
        raise ExtractionNotReadyError(document_id)

    successful = extraction_repo.get_latest_successful_for_document(
        session,
        document_id,
    )
    if successful is None:
        try:
            process_document(document_id, session)
        except OcrProcessingError:
            latest_failed = extraction_repo.get_latest_for_document(
                session,
                document_id,
            )
            fields = (
                _parse_json_object(latest_failed.extracted_fields_json)
                if latest_failed is not None
                else {}
            )
            return _persist_extraction_failed(
                session,
                document_id,
                category,
                schema,
                fields,
            )

        successful = extraction_repo.get_latest_successful_for_document(
            session,
            document_id,
        )
        if successful is None:
            latest_failed = extraction_repo.get_latest_for_document(
                session,
                document_id,
            )
            fields = (
                _parse_json_object(latest_failed.extracted_fields_json)
                if latest_failed is not None
                else {}
            )
            return _persist_extraction_failed(
                session,
                document_id,
                category,
                schema,
                fields,
            )

    document = documents_repo.get_by_id(session, document_id)
    extraction = extract_fields(document_id, session)
    if extraction is None:
        raise ExtractionNotReadyError(document_id)
    if extraction.status == ExtractionStatus.FAILED:
        return _persist_extraction_failed(
            session,
            document_id,
            category,
            schema,
            _parse_json_object(extraction.extracted_fields_json),
        )

    extracted_fields = _parse_json_object(extraction.extracted_fields_json)

    try:
        records = registry_repo.list_active_by_category(session, document.category)
    except Exception:
        outcome = _failed_technical(extracted_fields, schema, "REGISTRY_ERROR")
        return _persist(session, document_id, outcome)

    candidates = [_registry_as_dict(record) for record in records]
    match_result = find_applicable_record(
        category,
        extracted_fields,
        candidates,
        schema,
    )
    outcome = evaluate(
        ExtractionStatus.SUCCEEDED.value,
        extracted_fields,
        match_result,
        schema,
        settings.LOW_CONFIDENCE_THRESHOLD,
    )
    return _persist(session, document_id, outcome)
