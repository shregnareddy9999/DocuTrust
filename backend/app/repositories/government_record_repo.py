"""Queries for government_records."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.government_record import GovernmentRecord


def create(session: Session, record: GovernmentRecord) -> GovernmentRecord:
    session.add(record)
    session.flush()
    return record


def list_for_student(session: Session, student_id: str) -> list[GovernmentRecord]:
    stmt = (
        select(GovernmentRecord)
        .where(GovernmentRecord.student_id == student_id)
        .order_by(GovernmentRecord.created_at.asc(), GovernmentRecord.id.asc())
    )
    return list(session.scalars(stmt).all())
