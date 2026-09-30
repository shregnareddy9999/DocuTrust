"""Queries for marksheets."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.marksheet import Marksheet


def create(session: Session, marksheet: Marksheet) -> Marksheet:
    session.add(marksheet)
    session.flush()
    return marksheet


def list_for_student(session: Session, student_id: str) -> list[Marksheet]:
    """Chronological: semester, then upload time."""
    stmt = (
        select(Marksheet)
        .where(Marksheet.student_id == student_id)
        .order_by(Marksheet.semester.asc(), Marksheet.uploaded_at.asc(), Marksheet.id.asc())
    )
    return list(session.scalars(stmt).all())
