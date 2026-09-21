"""Deterministic OCR-to-schema field extraction for Task 06."""

from __future__ import annotations

import re
from typing import Any

from app.domain.schemas import FieldDef, get_schema


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REAL_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def _normalize(text: str) -> str:
    """Normalize text for case-insensitive, whitespace-tolerant matching."""
    return " ".join(text.lower().split())


def _extract_after_label(text: str, label: str) -> str | None:
    """Return the original OCR value appearing after a matched label."""
    normalized_text = _normalize(text)
    normalized_label = _normalize(label)

    if normalized_text == normalized_label:
        return None

    # Match the label case-insensitively while allowing flexible whitespace.
    label_pattern = re.escape(normalized_label).replace(r"\ ", r"\s+")
    match = re.search(label_pattern, text, flags=re.IGNORECASE)

    if match is None:
        return None

    value = text[match.end():].strip()
    value = value.lstrip(":=-").strip()

    return value or None


def _label_match(text: str, labels: tuple[str, ...]) -> str | None:
    """Return the matching label, preferring the longest label."""
    normalized = _normalize(text)

    matches = [
        label
        for label in labels
        if _normalize(label) in normalized
    ]

    if not matches:
        return None

    return max(matches, key=len)


def _region_value(region: Any, labels: tuple[str, ...]) -> tuple[str | None, Any]:
    """Extract a value from a single OCR region."""
    text = getattr(region, "text", "")
    confidence = getattr(region, "confidence", None)

    matched_label = _label_match(text, labels)

    if matched_label is None:
        return None, confidence

    value = _extract_after_label(text, matched_label)

    return value, confidence


def _validate_text(value: str) -> tuple[str, str | None]:
    if not value.strip():
        return value, "invalid_format"

    return value, None


def _validate_date(value: str) -> tuple[str, str | None]:
    if not DATE_RE.fullmatch(value.strip()):
        return value, "unrecognized_date_format"

    return value, None


def _validate_demo_pan(value: str) -> tuple[str, str | None]:
    value = value.strip()

    if REAL_PAN_RE.fullmatch(value):
        return value, "invalid_format"

    if len(value) != 6:
        return value, "invalid_format"

    return value, None


def _validate(field: FieldDef, value: str) -> tuple[str, str | None]:
    """Validate a value without changing the original value."""
    if field.name == "demo_pan_code":
        return _validate_demo_pan(value)

    if field.type == "date":
        return _validate_date(value)

    if field.type == "text":
        return _validate_text(value)

    return value, None


def map_ocr_to_fields(
    ocr_result: Any,
    category: str,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """
    Map an OcrResult-like object onto the category schema.

    The function deliberately accepts an OcrResult-like object rather than
    importing Task 05's adapter classes, because those classes are owned by
    Task 05.
    """
    schema = get_schema(category)
    regions = getattr(ocr_result, "regions", [])
    existing_warnings = list(getattr(ocr_result, "warnings", []))

    extracted_fields: dict[str, dict[str, Any]] = {}
    warnings = existing_warnings.copy()

    for field in schema:
        found_value: str | None = None
        found_confidence: float | None = None

        for region in regions:
            value, confidence = _region_value(region, field.labels)

            if value is not None:
                found_value = value
                found_confidence = confidence
                break

        if found_value is None:
            extracted_fields[field.name] = {
                "value": None,
                "confidence": None,
                "source": "ocr",
            }

            if field.required:
                warning = f"missing_field:{field.name}"
                if warning not in warnings:
                    warnings.append(warning)

            continue

        validated_value, validation_warning = _validate(
            field,
            found_value,
        )

        extracted_fields[field.name] = {
            "value": validated_value,
            "confidence": found_confidence,
            "source": "ocr",
        }

        if validation_warning:
            warning = f"{validation_warning}:{field.name}"
            if warning not in warnings:
                warnings.append(warning)

    return extracted_fields, warnings
