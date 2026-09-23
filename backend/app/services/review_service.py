"""Human review actions and additive verification corrections for Task 08."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.domain.matching import find_applicable_record
from app.domain.rules import evaluate
from app.domain.schemas import get_schema
from app.models.review import ReviewAction, ReviewActionType
from app.models.verification import VerificationResult
from app.repositories import registry_repo, review_repo, verification_repo
from app.repositories.documents_repo import get_by_id as get_document_by_id
from app.repositories.extraction_repo import get_latest_successful_for_document


class VerificationNotFoundError(ValueError):
    pass


class InvalidReviewActionError(ValueError):
    pass


class MissingCorrectionsError(ValueError):
    pass


class UnknownCorrectionFieldError(ValueError):
    pass


class EmptyReviewerRefError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_json_object(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _document_category(session: Session, document_id: str) -> str:
    document = get_document_by_id(session, document_id)
    if document is None:
        raise VerificationNotFoundError(document_id)
    return (
        document.category.value
        if hasattr(document.category, "value")
        else str(document.category)
    )


def _schema_field_names(category: str) -> set[str]:
    return {field.name for field in get_schema(category)}


def _match_field_names(category: str) -> set[str]:
    return {field.name for field in get_schema(category) if field.match_field}


def _entry_value(entry):
    if isinstance(entry, list):
        if not entry:
            return None
        for item in reversed(entry):
            if isinstance(item, dict) and item.get("source") == "corrected":
                return item.get("value")
        last = entry[-1]
        return last.get("value") if isinstance(last, dict) else last

    if isinstance(entry, dict):
        return entry.get("value")

    return entry


def _effective_fields(stored_fields: dict, corrections: dict) -> dict:
    effective = {}

    for field_name, entry in stored_fields.items():
        if isinstance(entry, list):
            # Use the latest effective value, but give Task 07 its normal
            # single-entry field shape.
            effective[field_name] = {
                "value": _entry_value(entry),
                "confidence": next(
                    (
                        item.get("confidence")
                        for item in reversed(entry)
                        if isinstance(item, dict)
                        and item.get("source") != "corrected"
                    ),
                    None,
                ),
                "source": "ocr",
            }
        elif isinstance(entry, dict):
            effective[field_name] = dict(entry)
        else:
            effective[field_name] = entry

    for field_name, value in corrections.items():
        effective[field_name] = {
            "value": value,
            "confidence": None,
            "source": "corrected",
        }

    return effective


def _add_corrections_to_extraction(extraction_fields: dict, corrections: dict) -> dict:
    updated = dict(extraction_fields)

    for field_name, corrected_value in corrections.items():
        original = updated.get(field_name)

        if isinstance(original, list):
            entries = list(original)
        elif isinstance(original, dict):
            entries = [dict(original)]
        else:
            entries = []

        entries.append(
            {
                "value": corrected_value,
                "confidence": None,
                "source": "corrected",
            }
        )

        updated[field_name] = entries

    return updated


def _persist_verification(
    session: Session,
    reviewed: VerificationResult,
    outcome,
) -> VerificationResult:
    registry_record_id = None

    if outcome.registry_record is not None:
        if hasattr(outcome.registry_record, "id"):
            registry_record_id = outcome.registry_record.id
        elif isinstance(outcome.registry_record, dict):
            registry_record_id = outcome.registry_record.get("id")

    rule_results = [
        {
            "rule_id": result.rule_id,
            "passed": result.passed,
            "reason": result.reason,
        }
        for result in outcome.rule_results
    ]

    row = VerificationResult(
        document_id=reviewed.document_id,
        registry_record_id=registry_record_id,
        status=outcome.status,
        field_comparisons_json=json.dumps(outcome.field_comparisons),
        rule_results_json=json.dumps(rule_results),
        reason_codes_json=json.dumps(outcome.reason_codes),
        supersedes_verification_id=reviewed.id,
        created_at=_now(),
    )

    return verification_repo.create(session, row)


def _update_extraction_with_correction(
    session: Session,
    document_id: str,
    corrections: dict,
):
    extraction = get_latest_successful_for_document(session, document_id)

    if extraction is None:
        raise RuntimeError("Extraction is not available for correction")

    fields = _parse_json_object(extraction.extracted_fields_json)
    extraction.extracted_fields_json = json.dumps(
        _add_corrections_to_extraction(fields, corrections)
    )
    session.flush()

    return extraction


def _build_match_result(session: Session, category: str, extracted_fields: dict):
    schema = get_schema(category)
    records = registry_repo.list_active_by_category(session, category)
    candidates = []
    for record in records:
        if isinstance(record, dict):
            data = dict(record)
        else:
            data = {c.name: getattr(record, c.name, None) for c in record.__table__.columns}
        raw_fields = data.get('fields_json') or data.get('fields') or {}
        for _ in range(2):
            if isinstance(raw_fields, str):
                try: raw_fields = json.loads(raw_fields)
                except (json.JSONDecodeError, TypeError): raw_fields = {}
            else: break
        if isinstance(raw_fields, dict) and isinstance(raw_fields.get('fields'), dict): raw_fields = raw_fields['fields']
        if not isinstance(raw_fields, dict): raw_fields = {}
        for k,v in list(raw_fields.items()):
            if isinstance(v, dict) and 'value' in v: raw_fields[k] = v.get('value')
        raw_category = data.get('category')
        if hasattr(raw_category, 'value'): raw_category = raw_category.value
        candidates.append({'id':data.get('id'),'category':raw_category,'active':data.get('active',True),'synthetic_record_key':data.get('synthetic_record_key'),'fields':raw_fields})
    return find_applicable_record(category, extracted_fields, candidates, schema)

def review_verification(
    session: Session,
    verification_id: str,
    reviewer_ref: str,
    action: str,
    corrections: dict | None = None,
    comment: str | None = None,
):
    reviewed = verification_repo.get_by_id(session, verification_id)

    if reviewed is None:
        raise VerificationNotFoundError(verification_id)

    if not reviewer_ref or not reviewer_ref.strip():
        raise EmptyReviewerRefError()

    try:
        review_action = ReviewActionType(action)
    except (ValueError, TypeError) as exc:
        raise InvalidReviewActionError(action) from exc

    corrections = corrections or {}

    if review_action == ReviewActionType.CORRECT:
        if not isinstance(corrections, dict) or not corrections:
            raise MissingCorrectionsError()

        category = _document_category(session, reviewed.document_id)
        unknown = set(corrections) - _schema_field_names(category)

        if unknown:
            raise UnknownCorrectionFieldError(
                ", ".join(sorted(unknown))
            )

    review = ReviewAction(
        verification_id=reviewed.id,
        reviewer_ref=reviewer_ref.strip(),
        action=review_action,
        corrections_json=(
            json.dumps(corrections)
            if review_action == ReviewActionType.CORRECT
            else None
        ),
        comment=comment,
        created_at=_now(),
    )

    review_repo.create(session, review)
    # Audit row must survive a later re-evaluation failure (Task 08 Req 2).
    session.commit()
    session.refresh(review)
    session.refresh(reviewed)

    if review_action == ReviewActionType.UNRESOLVED:
        return review, None

    try:
        new_row = _reevaluate_after_review(
            session,
            reviewed,
            review_action,
            corrections,
        )
        session.commit()
        session.refresh(review)
        session.refresh(new_row)
        return review, new_row
    except Exception:
        session.rollback()
        session.refresh(review)
        raise


def _reevaluate_after_review(
    session: Session,
    reviewed: VerificationResult,
    review_action: ReviewActionType,
    corrections: dict,
) -> VerificationResult:
    category = _document_category(session, reviewed.document_id)
    extraction = get_latest_successful_for_document(
        session,
        reviewed.document_id,
    )
    if extraction is None:
        raise RuntimeError("Extraction is not available for re-evaluation")

    stored_fields = _parse_json_object(extraction.extracted_fields_json)

    if review_action == ReviewActionType.ACCEPT:
        effective_fields = _effective_fields(stored_fields, {})
        confirmed = _match_field_names(category)
        extraction_status = (
            extraction.status.value
            if hasattr(extraction.status, "value")
            else str(extraction.status)
        )
    else:
        updated_extraction = _update_extraction_with_correction(
            session,
            reviewed.document_id,
            corrections,
        )
        stored_fields = _parse_json_object(
            updated_extraction.extracted_fields_json
        )
        effective_fields = _effective_fields(stored_fields, corrections)
        confirmed = set(corrections)
        extraction_status = (
            updated_extraction.status.value
            if hasattr(updated_extraction.status, "value")
            else str(updated_extraction.status)
        )

    match_result = _build_match_result(session, category, effective_fields)
    outcome = evaluate(
        extraction_status,
        effective_fields,
        match_result,
        get_schema(category),
        settings.LOW_CONFIDENCE_THRESHOLD,
        confidence_confirmed_fields=confirmed,
    )
    return _persist_verification(session, reviewed, outcome)







