"""Category schema registry for Task 06."""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class FieldDef:
    name: str
    label: str
    type: str
    required: bool
    match_field: bool
    labels: tuple[str, ...]
    validator: Callable[[str], bool] | None = None


from .academic_certificate import FIELDS as ACADEMIC_FIELDS
from .government_certificate import FIELDS as GOVERNMENT_FIELDS
from .institutional_id import FIELDS as INSTITUTIONAL_ID_FIELDS
from .pan_like_demo import FIELDS as PAN_LIKE_FIELDS


SCHEMA_REGISTRY = {
    "academic_certificate": ACADEMIC_FIELDS,
    "institutional_id": INSTITUTIONAL_ID_FIELDS,
    "pan_like_demo": PAN_LIKE_FIELDS,
    "government_certificate": GOVERNMENT_FIELDS,
}


def get_schema(category: str) -> list[FieldDef]:
    """Return field definitions for a document category."""
    try:
        return SCHEMA_REGISTRY[category]
    except KeyError as exc:
        raise ValueError(f"Unknown document category: {category}") from exc


def document_types() -> list[dict]:
    """Return the public document-type registry used by GET /document-types."""
    labels = {
        "academic_certificate": "Academic Certificate",
        "institutional_id": "Institutional ID",
        "pan_like_demo": "Pan Card",
        "government_certificate": "Government Certificate",
    }

    return [
        {
            "category": category,
            "label": labels[category],
            "fields": [
                {
                    "name": field.name,
                    "label": field.label,
                    "type": field.type,
                    "required": field.required,
                    "match_field": field.match_field,
                }
                for field in fields
            ],
        }
        for category, fields in SCHEMA_REGISTRY.items()
    ]
