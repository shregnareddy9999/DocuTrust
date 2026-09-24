"""Deterministic OCR-to-schema field extraction for Task 06."""

from __future__ import annotations

import json
import re
from types import SimpleNamespace
from typing import Any

from sqlalchemy.orm import Session

from app.domain.schemas import FieldDef, get_schema, SCHEMA_REGISTRY
from app.models.extraction import ExtractionResult, ExtractionStatus
from app.repositories import documents_repo, extraction_repo


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REAL_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
RIGHT_SLACK_PX = 8
MALFORMED_OCR_WARNING = "malformed_raw_ocr_json"


class UnknownCategoryError(ValueError):
    """Raised when a document category has no schema. API maps this to 500."""


def _normalize(text: str) -> str:
    """Normalize text for case-insensitive, whitespace-tolerant matching."""
    return " ".join(text.lower().split())


def _region_text(region: Any) -> str:
    if isinstance(region, dict):
        return str(region.get("text") or "")
    return str(getattr(region, "text", "") or "")


def _region_confidence(region: Any) -> float | None:
    if isinstance(region, dict):
        return region.get("confidence")
    return getattr(region, "confidence", None)


def _region_page(region: Any) -> int:
    if isinstance(region, dict):
        return int(region.get("page") or 1)
    return int(getattr(region, "page", 1) or 1)


def _region_bbox(region: Any) -> tuple[float, float, float, float]:
    if isinstance(region, dict):
        bbox = region.get("bbox") or (0, 0, 0, 0)
    else:
        bbox = getattr(region, "bbox", None) or (0, 0, 0, 0)
    if len(bbox) != 4:
        return (0.0, 0.0, 0.0, 0.0)
    return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))


def _label_prefix_match(normalized_text: str, normalized_label: str) -> bool:
    """True if text equals the label or starts with label then : / = / end."""
    if not normalized_label:
        return False
    if normalized_text == normalized_label:
        return True
    if not normalized_text.startswith(normalized_label):
        return False
    rest = normalized_text[len(normalized_label) :]
    if not rest:
        return True
    return rest[0] in " :=-"


def _matching_label(text: str, labels: tuple[str, ...]) -> str | None:
    """Longest label that equals the text or is a prefix followed by : / = / EOS."""
    normalized = _normalize(text)
    matches = [
        label
        for label in labels
        if _label_prefix_match(normalized, _normalize(label))
    ]
    if not matches:
        return None
    return max(matches, key=len)


def _owning_field(text: str, schema: list[FieldDef]) -> FieldDef | None:
    """Field whose longest matching label wins for this region (cross-field)."""
    scored: list[tuple[int, FieldDef]] = []
    for field in schema:
        matched = _matching_label(text, field.labels)
        if matched is not None:
            scored.append((len(matched), field))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def _remainder_after_label(text: str, label: str) -> str | None:
    """Return a meaningful OCR value remaining after a matched label."""
    normalized_label = _normalize(label)
    label_pattern = re.escape(normalized_label).replace(r"\ ", r"\s+")
    match = re.search(label_pattern, text, flags=re.IGNORECASE)
    if match is None:
        return None

    value = text[match.end() :].strip()
    value = value.lstrip(":=-").strip()

    # Ignore punctuation-only OCR artifacts attached to labels.
    # Example: "Date of Birth:." -> no inline value.
    if value and not re.search(r"[A-Za-z0-9]", value):
        return None

    return value or None


def _vertical_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> bool:
    return min(a[3], b[3]) > max(a[1], b[1])


def _horizontal_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> bool:
    return min(a[2], b[2]) > max(a[0], b[0])


def _is_label_only_for_schema(region: Any, schema: list[FieldDef]) -> bool:
    text = _region_text(region)
    for field in schema:
        matched = _matching_label(text, field.labels)
        if matched is None:
            continue
        if _remainder_after_label(text, matched) is None:
            return True
    return False


def _nearest_right(
    label_region: Any,
    candidates: list[tuple[int, Any]],
) -> tuple[int, Any] | None:
    label_bbox = _region_bbox(label_region)
    label_page = _region_page(label_region)
    ranked: list[tuple[float, float, int, Any]] = []
    for index, region in candidates:
        if _region_page(region) != label_page:
            continue
        bbox = _region_bbox(region)
        if bbox[0] + 1e-9 < label_bbox[2] - RIGHT_SLACK_PX:
            continue
        if not _vertical_overlap(label_bbox, bbox):
            continue
        gap = bbox[0] - label_bbox[2]
        y_delta = abs(bbox[1] - label_bbox[1])
        ranked.append((gap, y_delta, index, region))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    winner = ranked[0]
    return winner[2], winner[3]


def _nearest_below(
    label_region: Any,
    candidates: list[tuple[int, Any]],
) -> tuple[int, Any] | None:
    label_bbox = _region_bbox(label_region)
    label_page = _region_page(label_region)
    ranked: list[tuple[int, float, float, int, Any]] = []
    for index, region in candidates:
        if _region_page(region) != label_page:
            continue
        bbox = _region_bbox(region)
        if bbox[1] + 1e-9 < label_bbox[3]:
            continue
        overlap = 0 if _horizontal_overlap(label_bbox, bbox) else 1
        gap = bbox[1] - label_bbox[3]
        x_delta = abs(bbox[0] - label_bbox[0])
        ranked.append((overlap, gap, x_delta, index, region))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    winner = ranked[0]
    return winner[3], winner[4]


def _validate_text(value: str) -> tuple[str, str | None]:
    if not value.strip():
        return value, "invalid_format"
    return value, None


def _validate_date(value: str) -> tuple[str, str | None]:
    if not DATE_RE.fullmatch(value.strip()):
        return value, "unrecognized_date_format"
    return value, None


def _validate_demo_pan(value: str) -> tuple[str, str | None]:
    stripped = value.strip()
    if REAL_PAN_RE.fullmatch(stripped):
        return value, "invalid_format"
    if len(stripped) != 6:
        return value, "invalid_format"
    return value, None


def _validate_integer(value: str) -> tuple[str, str | None]:
    try:
        int(value.strip())
    except ValueError:
        return value, "invalid_format"
    return value, None


def _validate(field: FieldDef, value: str) -> tuple[str, str | None]:
    """Validate a value without changing the original OCR string."""
    try:
        if field.name == "demo_pan_code":
            return _validate_demo_pan(value)
        if field.type == "date":
            return _validate_date(value)
        if field.type == "integer":
            return _validate_integer(value)
        if field.type == "text":
            return _validate_text(value)
        return value, None
    except Exception:
        return value, "invalid_format"


def map_ocr_to_fields(
    ocr_result: Any,
    category: str,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """
    Map an OcrResult-like object onto the category schema.

    Strategy, in schema order, per field:
    1. Find a region whose text equals a label or starts with that label
       followed by ':' / '=' / end-of-string. Prefer the longest matching label.
    2. If leftover text remains in that region after the label, use it.
    3. Else nearest unused region to the right (same page, x1 >= label.x2 with
       a small pixel slack, vertical overlap, smallest gap then |y1 - label.y1|).
    4. Else nearest unused region below (y1 >= label.y2, horizontal overlap
       preferred, smallest vertical gap).
    5. No match → value/confidence null. missing_field:<name> if required.
    Never invent values; never reuse a value region; never use a label-only
    region as a value.
    """
    schema = get_schema(category)
    regions = list(getattr(ocr_result, "regions", []) or [])
    existing_warnings = list(getattr(ocr_result, "warnings", []) or [])

    extracted_fields: dict[str, dict[str, Any]] = {}
    warnings = existing_warnings.copy()
    used_value_indices: set[int] = set()

    def _available() -> list[tuple[int, Any]]:
        return [
            (i, region)
            for i, region in enumerate(regions)
            if i not in used_value_indices
            and not _is_label_only_for_schema(region, schema)
        ]

    for field in schema:
        found_value: str | None = None
        found_confidence: float | None = None
        used_index: int | None = None

        for index, region in enumerate(regions):
            if index in used_value_indices:
                continue
            text = _region_text(region)
            matched_label = _matching_label(text, field.labels)
            if matched_label is None:
                continue
            owner = _owning_field(text, schema)
            if owner is not None and owner.name != field.name:
                continue

            remainder = _remainder_after_label(text, matched_label)
            if remainder is not None:
                found_value = remainder
                found_confidence = _region_confidence(region)
                used_index = index
                break

            right = _nearest_right(region, _available())
            if right is not None:
                used_index, value_region = right
                found_value = _region_text(value_region)
                found_confidence = _region_confidence(value_region)
                break

            below = _nearest_below(region, _available())
            if below is not None:
                used_index, value_region = below
                found_value = _region_text(value_region)
                found_confidence = _region_confidence(value_region)
                break

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

        if used_index is not None:
            used_value_indices.add(used_index)

        validated_value, validation_warning = _validate(field, found_value)
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


def _ocr_from_raw_dict(raw: dict[str, Any]) -> SimpleNamespace:
    regions = []
    for item in raw.get("regions") or []:
        if isinstance(item, dict):
            regions.append(
                SimpleNamespace(
                    text=item.get("text", ""),
                    confidence=item.get("confidence"),
                    bbox=tuple(item.get("bbox") or (0, 0, 0, 0)),
                    page=item.get("page", 1),
                )
            )
        else:
            regions.append(item)
    return SimpleNamespace(
        text=raw.get("text", ""),
        regions=regions,
        warnings=list(raw.get("warnings") or []),
    )


def _parse_json_list(raw: str) -> list[Any]:
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _empty_fields(category: str) -> dict[str, dict[str, Any]]:
    return {
        field.name: {"value": None, "confidence": None, "source": "ocr"}
        for field in get_schema(category)
    }


def extract_fields(document_id: str, session: Session) -> ExtractionResult | None:
    """
    Map the latest successful OCR dump onto the document category schema and
    persist extracted_fields_json plus merged warnings. Does not commit.
    Does not change extraction status. Does not read LOW_CONFIDENCE_THRESHOLD.

    Returns the FAILED extraction row unchanged if that is the latest row.
    Returns None if the document has no extraction row to map.
    Raises UnknownCategoryError if the document category is not in the schema.
    """
    document = documents_repo.get_by_id(session, document_id)
    if document is None:
        return None

    category = (
        document.category.value
        if hasattr(document.category, "value")
        else str(document.category)
    )
    if category not in SCHEMA_REGISTRY:
        raise UnknownCategoryError(category)

    latest = extraction_repo.get_latest_for_document(session, document_id)
    if latest is not None and latest.status == ExtractionStatus.FAILED:
        return latest

    successful = extraction_repo.get_latest_successful_for_document(
        session,
        document_id,
    )
    if successful is None:
        return None

    row_warnings = _parse_json_list(successful.warnings_json)

    try:
        raw = json.loads(successful.raw_ocr_json)
        if not isinstance(raw, dict):
            raise ValueError("raw_ocr_json is not an object")
        ocr = _ocr_from_raw_dict(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        fields = _empty_fields(category)
        warnings = list(row_warnings)
        if MALFORMED_OCR_WARNING not in warnings:
            warnings.append(MALFORMED_OCR_WARNING)
        successful.extracted_fields_json = json.dumps(fields)
        successful.warnings_json = json.dumps(warnings)
        session.flush()
        return successful

    extracted, mapping_warnings = map_ocr_to_fields(ocr, category)
    merged = list(row_warnings)
    for warning in mapping_warnings:
        if warning not in merged:
            merged.append(warning)

    successful.extracted_fields_json = json.dumps(extracted)
    successful.warnings_json = json.dumps(merged)
    session.flush()
    return successful
