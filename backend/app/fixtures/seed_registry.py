"""
Idempotently populates `registry_records` with the four locked fixtures from
`docs/category-schemas.md` (Task 03, `docs/implementation-plan.md` step 3).

    python -m app.fixtures.seed_registry

Behaviour (Task 03 §7 Requirement 2):
  * Look up each fixture by (category, synthetic_record_key).
  * Absent -> create.
  * Present and identical (fields, source_label, active) -> unchanged.
  * Present and different -> report the difference, do NOT overwrite.
  * Print a clear created/unchanged/divergent summary.
  * Exit non-zero if anything was divergent, or if the DB is unavailable.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.document import DocumentCategory
from app.models.registry import RegistryRecord
from app.repositories import registry_repo

from .fixture_data import FIXTURES, SOURCE_LABEL


@dataclass
class SeedSummary:
    created: list[tuple[str, str]] = field(default_factory=list)
    unchanged: list[tuple[str, str]] = field(default_factory=list)
    divergent: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.divergent

    def print_report(self) -> None:
        print("Registry seeding summary")
        print("-------------------------")
        for category, key in self.created:
            print(f"  CREATED    {category:<24} {key}")
        for category, key in self.unchanged:
            print(f"  UNCHANGED  {category:<24} {key}")
        for category, key, reason in self.divergent:
            print(f"  DIVERGENT  {category:<24} {key}  -- {reason}")
        print(
            f"Totals: {len(self.created)} created, {len(self.unchanged)} unchanged, "
            f"{len(self.divergent)} divergent"
        )
        if self.divergent:
            print(
                "\nOne or more existing records differ from the locked fixtures and were "
                "NOT overwritten. Someone edited registry data by hand -- investigate before "
                "the demo. See docs/category-schemas.md for the expected values."
            )


def _canonical(fields: dict) -> str:
    return json.dumps(fields, sort_keys=True)


def _category_enum(category_str: str) -> DocumentCategory:
    mapping = {
        "academic_certificate": DocumentCategory.ACADEMIC_CERTIFICATE,
        "institutional_id": DocumentCategory.INSTITUTIONAL_ID,
        "pan_like_demo": DocumentCategory.PAN_LIKE_DEMO,
        "government_certificate": DocumentCategory.GOVERNMENT_CERTIFICATE,
    }
    return mapping[category_str]


def seed(session: Session) -> SeedSummary:
    summary = SeedSummary()
    for category_str, spec in FIXTURES.items():
        category = _category_enum(category_str)
        key = spec["synthetic_record_key"]
        expected_fields = spec["fields"]

        existing = registry_repo.get_by_category_and_key(session, category, key)

        if existing is None:
            record = RegistryRecord(
                category=category,
                synthetic_record_key=key,
                fields_json=_canonical(expected_fields),
                source_label=SOURCE_LABEL,
                active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            registry_repo.create(session, record)
            summary.created.append((category_str, key))
            continue

        try:
            existing_fields = json.loads(existing.fields_json)
        except (TypeError, ValueError):
            existing_fields = None

        is_identical = (
            existing_fields == expected_fields
            and existing.source_label == SOURCE_LABEL
            and existing.active is True
        )

        if is_identical:
            summary.unchanged.append((category_str, key))
        else:
            reasons = []
            if existing_fields != expected_fields:
                reasons.append("fields_json differs")
            if existing.source_label != SOURCE_LABEL:
                reasons.append(f"source_label={existing.source_label!r}")
            if existing.active is not True:
                reasons.append(f"active={existing.active!r}")
            summary.divergent.append((category_str, key, "; ".join(reasons)))

    session.commit()
    return summary


def main() -> int:
    # Import models to ensure tables are registered with Base before creating session
    from app.models import registry, document  # noqa: F401
    from app.db import Base, engine
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        summary = seed(session)
    except SQLAlchemyError as exc:
        session.rollback()
        print(f"FATAL: seeding failed, no partial changes committed: {exc}", file=sys.stderr)
        return 2
    finally:
        session.close()

    summary.print_report()
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())