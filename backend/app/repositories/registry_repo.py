"""Queries for registry_records."""

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import literal_column

from app.models.document import DocumentCategory
from app.models.registry import RegistryRecord


def create(session: Session, record: RegistryRecord) -> RegistryRecord:
    session.add(record)
    session.flush()
    return record


def get_by_category_and_key(
    session: Session,
    category: DocumentCategory,
    synthetic_record_key: str,
) -> RegistryRecord | None:
    stmt = select(RegistryRecord).where(
        RegistryRecord.category == category,
        RegistryRecord.synthetic_record_key == synthetic_record_key,
    )
    return session.scalars(stmt).first()


def list_active_by_category(
    session: Session,
    category: DocumentCategory,
) -> list[RegistryRecord]:
    stmt = (
        select(RegistryRecord)
        .where(
            RegistryRecord.category == category,
            RegistryRecord.active.is_(True),
        )
        .order_by(
            RegistryRecord.created_at.asc(),
            literal_column("rowid").asc(),
        )
    )
    return list(session.scalars(stmt).all())


def get_by_id(session: Session, record_id: str) -> RegistryRecord | None:
    return session.get(RegistryRecord, record_id)
