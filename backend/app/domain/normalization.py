"""Whitespace, case, and date normalization for comparison only."""

from __future__ import annotations

import re

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_text(value: str) -> str:
    """Trim, collapse internal whitespace, and case-fold for comparison."""
    return " ".join(value.split()).casefold()


def normalize_date(value: str) -> str | None:
    """Return YYYY-MM-DD or None if the value is not already that format."""
    stripped = value.strip()
    if DATE_RE.fullmatch(stripped):
        return stripped
    return None


def normalize_for_comparison(value: object, field_type: str) -> tuple[str, str | None]:
    """
    Return (original, normalized).

    Original casing and identifier characters are preserved. Hyphens and letters
    are never stripped; O is never rewritten as 0. Invalid dates yield
    normalized None so they are excluded from equality.
    """
    if value is None:
        return "", None

    original = str(value)
    if field_type == "date":
        return original, normalize_date(original)
    if field_type == "integer":
        stripped = original.strip()
        try:
            int(stripped)
        except ValueError:
            return original, None
        return original, stripped
    return original, normalize_text(original)
