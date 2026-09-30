"""Queries for student_documents (document-to-student links)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.student_document import StudentDocument


def create(session: Session, link: StudentDocument) -> StudentDocument:
    session.add(link)
    session.flush()
    return link


def get(session: Session, student_id: str, document_id: str) -> StudentDocument | None:
    stmt = select(StudentDocument).where(
        StudentDocument.student_id == student_id,
        StudentDocument.document_id == document_id,
    )
    return session.scalars(stmt).first()


def next_version(session: Session, student_id: str, category) -> int:
    stmt = (
        select(func.count(StudentDocument.id))
        .join(Document, Document.id == StudentDocument.document_id)
        .where(StudentDocument.student_id == student_id, Document.category == category)
    )
    return int(session.scalar(stmt) or 0) + 1


def list_for_student(session: Session, student_id: str) -> list[tuple[StudentDocument, Document]]:
    stmt = (
        select(StudentDocument, Document)
        .join(Document, Document.id == StudentDocument.document_id)
        .where(StudentDocument.student_id == student_id)
        .order_by(StudentDocument.linked_at.desc(), StudentDocument.version.desc())
    )
    return [(link, doc) for link, doc in session.execute(stmt).all()]
