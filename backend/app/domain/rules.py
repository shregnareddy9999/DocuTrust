"""Deterministic rules and status precedence. No scores, weights, or probabilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.domain.matching import (
    MatchResult,
    extracted_confidence,
    extracted_value,
    identifying_key_name,
)
from app.domain.normalization import DATE_RE, normalize_for_comparison
from app.domain.schemas import FieldDef
from app.domain.status import VerificationStatus


REAL_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

RULE_IDS = (
    "required_field_presence",
    "field_match",
    "category_schema_validity",
    "date_consistency",
    "known_fixture_duplicate",
)

EXTRACTION_FAILED = "FAILED"

REASON_DATE_CONSISTENCY = (
    "No related-date check is defined for the current categories."
)
REASON_REQUIRED_PASS = "Every required field has a non-null extracted value."
REASON_REQUIRED_FAIL = "One or more required fields are missing."
REASON_FIELD_MATCH_PASS = "Every match field equals the applicable registry record."
REASON_FIELD_MATCH_NO_RECORD = "No applicable registry record for field comparison."
REASON_SCHEMA_PASS = "Extracted values conform to the declared field types."
REASON_SCHEMA_FAIL = "One or more extracted values do not conform to the declared type."
REASON_DUPLICATE_PASS = "Identifying key does not indicate fixture confusion."
REASON_DUPLICATE_FAIL = (
    "Possible fixture confusion: identifying key matches a registry record "
    "whose other match fields disagree."
)
REASON_REGISTRY_DATA_ERROR = (
    "Registry fixtures contain more than one fully matching active record."
)


@dataclass
class RuleResult:
    rule_id: str
    passed: bool
    reason: str


@dataclass
class VerificationOutcome:
    status: VerificationStatus
    field_comparisons: list[dict[str, Any]]
    rule_results: list[RuleResult]
    reason_codes: list[str]
    registry_record: dict[str, Any] | None = None


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def required_field_presence(
    extracted_fields: dict,
    registry_record: dict | None,
    schema: list[FieldDef],
) -> RuleResult:
    missing = [
        field_def.name
        for field_def in schema
        if field_def.required and _is_missing(extracted_value(extracted_fields, field_def.name))
    ]
    if missing:
        return RuleResult(
            RULE_IDS[0],
            False,
            REASON_REQUIRED_FAIL,
        )
    return RuleResult(RULE_IDS[0], True, REASON_REQUIRED_PASS)


def field_match(
    extracted_fields: dict,
    registry_record: dict | None,
    schema: list[FieldDef],
) -> RuleResult:
    if registry_record is None:
        return RuleResult(RULE_IDS[1], False, REASON_FIELD_MATCH_NO_RECORD)
    registry_fields = registry_record.get("fields") or {}
    mismatched: list[str] = []
    for field_def in schema:
        if not field_def.match_field:
            continue
        extracted = extracted_value(extracted_fields, field_def.name)
        registry = registry_fields.get(field_def.name)
        _, extracted_norm = normalize_for_comparison(
            extracted if extracted is not None else "",
            field_def.type,
        )
        _, registry_norm = normalize_for_comparison(
            registry if registry is not None else "",
            field_def.type,
        )
        if extracted_norm is None or registry_norm is None or extracted_norm != registry_norm:
            mismatched.append(field_def.name)
    if mismatched:
        key = registry_record.get("synthetic_record_key") or "unknown"
        first = mismatched[0]
        return RuleResult(
            RULE_IDS[1],
            False,
            f"{first} does not match registry record {key}",
        )
    return RuleResult(RULE_IDS[1], True, REASON_FIELD_MATCH_PASS)


def _value_conforms(field_def: FieldDef, value: Any) -> bool:
    if _is_missing(value):
        return True
    text = str(value)
    if field_def.name == "demo_pan_code":
        stripped = text.strip()
        if REAL_PAN_RE.fullmatch(stripped):
            return False
        return len(stripped) == 6
    if field_def.type == "date":
        return DATE_RE.fullmatch(text.strip()) is not None
    if field_def.type == "integer":
        try:
            int(text.strip())
        except ValueError:
            return False
        return True
    if field_def.type == "text":
        return bool(text.strip())
    return True


def category_schema_validity(
    extracted_fields: dict,
    registry_record: dict | None,
    schema: list[FieldDef],
) -> RuleResult:
    for field_def in schema:
        value = extracted_value(extracted_fields, field_def.name)
        if not _value_conforms(field_def, value):
            return RuleResult(RULE_IDS[2], False, REASON_SCHEMA_FAIL)
    return RuleResult(RULE_IDS[2], True, REASON_SCHEMA_PASS)


def date_consistency(
    extracted_fields: dict,
    registry_record: dict | None,
    schema: list[FieldDef],
) -> RuleResult:
    return RuleResult(RULE_IDS[3], True, REASON_DATE_CONSISTENCY)


def known_fixture_duplicate(
    extracted_fields: dict,
    registry_record: dict | None,
    schema: list[FieldDef],
) -> RuleResult:
    if registry_record is None:
        return RuleResult(RULE_IDS[4], True, REASON_DUPLICATE_PASS)
    key_name = identifying_key_name(str(registry_record.get("category") or ""))
    if key_name is None:
        for field_def in schema:
            if field_def.name in (
                "student_id",
                "id_number",
                "demo_pan_code",
                "certificate_number",
            ):
                key_name = field_def.name
                break
    if key_name is None:
        return RuleResult(RULE_IDS[4], True, REASON_DUPLICATE_PASS)
    extracted = extracted_value(extracted_fields, key_name)
    registry_fields = registry_record.get("fields") or {}
    registry_key = registry_fields.get(key_name)
    key_type = "text"
    for field_def in schema:
        if field_def.name == key_name:
            key_type = field_def.type
            break
    _, extracted_norm = normalize_for_comparison(
        extracted if extracted is not None else "",
        key_type,
    )
    _, registry_norm = normalize_for_comparison(
        registry_key if registry_key is not None else "",
        key_type,
    )
    if extracted_norm is None or registry_norm is None or extracted_norm != registry_norm:
        return RuleResult(RULE_IDS[4], True, REASON_DUPLICATE_PASS)
    match_rule = field_match(extracted_fields, registry_record, schema)
    if not match_rule.passed:
        return RuleResult(RULE_IDS[4], False, REASON_DUPLICATE_FAIL)
    return RuleResult(RULE_IDS[4], True, REASON_DUPLICATE_PASS)


RULE_FUNCTIONS = (
    required_field_presence,
    field_match,
    category_schema_validity,
    date_consistency,
    known_fixture_duplicate,
)


def run_rules(
    extracted_fields: dict,
    registry_record: dict | None,
    schema: list[FieldDef],
) -> list[RuleResult]:
    results: list[RuleResult] = []
    for func in RULE_FUNCTIONS:
        try:
            results.append(func(extracted_fields, registry_record, schema))
        except Exception:
            results.append(
                RuleResult(
                    func.__name__,
                    False,
                    f"Rule {func.__name__} raised an exception.",
                )
            )
    return results


def _missing_required(extracted_fields: dict, schema: list[FieldDef]) -> list[str]:
    return [
        field_def.name
        for field_def in schema
        if field_def.required
        and _is_missing(extracted_value(extracted_fields, field_def.name))
    ]


def _low_confidence_fields(
    extracted_fields: dict,
    schema: list[FieldDef],
    low_confidence_threshold: float,
) -> list[str]:
    names: list[str] = []
    for field_def in schema:
        if not field_def.match_field:
            continue
        confidence = extracted_confidence(extracted_fields, field_def.name)
        if confidence is not None and confidence < low_confidence_threshold:
            names.append(field_def.name)
    return names


def _has_applicable_record(match_result: MatchResult) -> bool:
    return match_result.record is not None and (
        match_result.is_full_match or match_result.is_applicable_reference
    )


def evaluate(
    extraction_status: str,
    extracted_fields: dict,
    match_result: MatchResult,
    schema: list[FieldDef],
    low_confidence_threshold: float,
) -> VerificationOutcome:
    """
    Status precedence from docs/verification-rules.md. First match wins.

    1. OCR/extraction failed → PROCESSING_FAILED
    2. Required field missing OR match-field confidence below threshold → REVIEW_REQUIRED
    3. No applicable registry record → NO_TRUSTED_RECORD
    4. Applicable record with any failed match-field comparison → INTEGRITY_MISMATCH
    5. Applicable record with all match-field comparisons passing → VERIFIED_MATCH

    Registry data errors and rule exceptions are PROCESSING_FAILED, never a mismatch.
    """
    rule_results = run_rules(extracted_fields, match_result.record, schema)
    comparisons = list(match_result.comparisons)
    record = match_result.record

    if extraction_status == EXTRACTION_FAILED:
        return VerificationOutcome(
            status=VerificationStatus.PROCESSING_FAILED,
            field_comparisons=comparisons,
            rule_results=rule_results,
            reason_codes=["EXTRACTION_FAILED"],
            registry_record=None,
        )

    if any(result.reason.endswith("raised an exception.") for result in rule_results):
        failed = next(
            result.rule_id
            for result in rule_results
            if result.reason.endswith("raised an exception.")
        )
        return VerificationOutcome(
            status=VerificationStatus.PROCESSING_FAILED,
            field_comparisons=comparisons,
            rule_results=rule_results,
            reason_codes=[f"RULE_EXCEPTION:{failed}"],
            registry_record=None,
        )

    if match_result.registry_data_error:
        return VerificationOutcome(
            status=VerificationStatus.PROCESSING_FAILED,
            field_comparisons=comparisons,
            rule_results=rule_results,
            reason_codes=["REGISTRY_DATA_ERROR"],
            registry_record=None,
        )

    missing = _missing_required(extracted_fields, schema)
    low_confidence = _low_confidence_fields(
        extracted_fields,
        schema,
        low_confidence_threshold,
    )
    if missing or low_confidence:
        codes: list[str] = [f"MISSING_REQUIRED:{name}" for name in missing]
        codes.extend(f"LOW_CONFIDENCE:{name}" for name in low_confidence)
        return VerificationOutcome(
            status=VerificationStatus.REVIEW_REQUIRED,
            field_comparisons=comparisons,
            rule_results=rule_results,
            reason_codes=codes,
            registry_record=record,
        )

    if not _has_applicable_record(match_result):
        return VerificationOutcome(
            status=VerificationStatus.NO_TRUSTED_RECORD,
            field_comparisons=comparisons,
            rule_results=rule_results,
            reason_codes=["NO_TRUSTED_RECORD"],
            registry_record=None,
        )

    failed_comparisons = [
        row["field"] for row in comparisons if not row.get("matched")
    ]
    if failed_comparisons:
        return VerificationOutcome(
            status=VerificationStatus.INTEGRITY_MISMATCH,
            field_comparisons=comparisons,
            rule_results=rule_results,
            reason_codes=[f"FIELD_MISMATCH:{name}" for name in failed_comparisons],
            registry_record=record,
        )

    return VerificationOutcome(
        status=VerificationStatus.VERIFIED_MATCH,
        field_comparisons=comparisons,
        rule_results=rule_results,
        reason_codes=[],
        registry_record=record,
    )
