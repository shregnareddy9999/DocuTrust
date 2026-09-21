"""Registry matching, steps 1–6. Pure functions; candidates are passed in."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.normalization import normalize_for_comparison
from app.domain.schemas import FieldDef


IDENTIFYING_KEYS: dict[str, str] = {
    "academic_certificate": "student_id",
    "institutional_id": "id_number",
    "pan_like_demo": "demo_pan_code",
    "government_certificate": "certificate_number",
}


@dataclass
class MatchResult:
    record: dict[str, Any] | None = None
    is_full_match: bool = False
    is_applicable_reference: bool = False
    comparisons: list[dict[str, Any]] = field(default_factory=list)
    registry_data_error: bool = False


def _field_entry(extracted_fields: dict, name: str) -> dict:
    entry = extracted_fields.get(name)
    if isinstance(entry, dict):
        return entry
    return {}


def extracted_value(extracted_fields: dict, name: str) -> Any:
    entry = _field_entry(extracted_fields, name)
    if "value" in entry:
        return entry.get("value")
    return None


def extracted_confidence(extracted_fields: dict, name: str) -> float | None:
    entry = _field_entry(extracted_fields, name)
    confidence = entry.get("confidence")
    if confidence is None:
        return None
    try:
        return float(confidence)
    except (TypeError, ValueError):
        return None


def identifying_key_name(category: str) -> str | None:
    return IDENTIFYING_KEYS.get(category)


def _candidate_fields(candidate: dict) -> dict:
    fields = candidate.get("fields")
    return fields if isinstance(fields, dict) else {}


def _is_active(candidate: dict) -> bool:
    return candidate.get("active", True) is True


def _same_category(candidate: dict, category: str) -> bool:
    raw = candidate.get("category")
    if raw is None:
        return True
    value = raw.value if hasattr(raw, "value") else raw
    return str(value) == category


def _values_equal(extracted: Any, registry: Any, field_type: str) -> bool:
    if extracted is None or extracted == "":
        return False
    if registry is None:
        return False
    _, extracted_norm = normalize_for_comparison(extracted, field_type)
    _, registry_norm = normalize_for_comparison(registry, field_type)
    if extracted_norm is None or registry_norm is None:
        return False
    return extracted_norm == registry_norm


def _comparisons_for(
    schema: list[FieldDef],
    extracted_fields: dict,
    registry_fields: dict | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    registry_fields = registry_fields or {}
    for field_def in schema:
        if not field_def.match_field:
            continue
        extracted = extracted_value(extracted_fields, field_def.name)
        registry = registry_fields.get(field_def.name)
        extracted_original, _ = normalize_for_comparison(
            extracted if extracted is not None else "",
            field_def.type,
        )
        if extracted is None:
            extracted_original = None
        registry_original = None if registry is None else str(registry)
        matched = _values_equal(extracted, registry, field_def.type)
        rows.append(
            {
                "field": field_def.name,
                "extracted_value": extracted_original if extracted is not None else None,
                "registry_value": registry_original,
                "matched": matched,
            }
        )
    return rows


def _is_full_match(
    schema: list[FieldDef],
    extracted_fields: dict,
    candidate: dict,
) -> bool:
    registry_fields = _candidate_fields(candidate)
    for field_def in schema:
        if not field_def.match_field:
            continue
        extracted = extracted_value(extracted_fields, field_def.name)
        registry = registry_fields.get(field_def.name)
        if not _values_equal(extracted, registry, field_def.type):
            return False
    return True


def _identifying_key_matches(
    category: str,
    extracted_fields: dict,
    candidate: dict,
    schema: list[FieldDef],
) -> bool:
    key_name = identifying_key_name(category)
    if key_name is None:
        return False
    field_type = "text"
    for field_def in schema:
        if field_def.name == key_name:
            field_type = field_def.type
            break
    extracted = extracted_value(extracted_fields, key_name)
    registry = _candidate_fields(candidate).get(key_name)
    return _values_equal(extracted, registry, field_type)


def _sort_key(candidate: dict) -> tuple[str, str]:
    return (str(candidate.get("id") or ""), str(candidate.get("synthetic_record_key") or ""))


def find_applicable_record(
    category: str,
    extracted_fields: dict,
    candidates: list[dict],
    schema: list[FieldDef],
) -> MatchResult:
    """
    Matching steps 1–6. Candidate order must not affect the result.
    """
    eligible = [
        candidate
        for candidate in candidates
        if _same_category(candidate, category) and _is_active(candidate)
    ]
    eligible.sort(key=_sort_key)

    full_matches = [
        candidate
        for candidate in eligible
        if _is_full_match(schema, extracted_fields, candidate)
    ]

    if len(full_matches) > 1:
        return MatchResult(
            record=None,
            is_full_match=False,
            is_applicable_reference=False,
            comparisons=_comparisons_for(schema, extracted_fields, None),
            registry_data_error=True,
        )

    if len(full_matches) == 1:
        record = full_matches[0]
        return MatchResult(
            record=record,
            is_full_match=True,
            is_applicable_reference=True,
            comparisons=_comparisons_for(
                schema,
                extracted_fields,
                _candidate_fields(record),
            ),
            registry_data_error=False,
        )

    key_matches = [
        candidate
        for candidate in eligible
        if _identifying_key_matches(category, extracted_fields, candidate, schema)
    ]

    if len(key_matches) > 1:
        return MatchResult(
            record=None,
            is_full_match=False,
            is_applicable_reference=False,
            comparisons=_comparisons_for(schema, extracted_fields, None),
            registry_data_error=True,
        )

    if len(key_matches) == 1:
        record = key_matches[0]
        return MatchResult(
            record=record,
            is_full_match=False,
            is_applicable_reference=True,
            comparisons=_comparisons_for(
                schema,
                extracted_fields,
                _candidate_fields(record),
            ),
            registry_data_error=False,
        )

    return MatchResult(
        record=None,
        is_full_match=False,
        is_applicable_reference=False,
        comparisons=_comparisons_for(schema, extracted_fields, None),
        registry_data_error=False,
    )
