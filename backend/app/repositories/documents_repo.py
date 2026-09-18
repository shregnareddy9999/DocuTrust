"""Queries for documents."""

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import literal_column

from app.models.document import Document, ProcessingState


def create(session: Session, document: Document) -> Document:
    session.add(document)
    session.flush()
    return document


def get_by_id(session: Session, document_id: str) -> Document | None:
    return session.get(Document, document_id)


def update_processing_state(
    session: Session,
    document_id: str,
    processing_state: ProcessingState,
) -> Document | None:
    document = session.get(Document, document_id)
    if document is None:
        return None
    document.processing_state = processing_state
    session.flush()
    return document


def list_recent(session: Session, limit: int) -> list[Document]:
    stmt = (
        select(Document)
        .order_by(Document.uploaded_at.desc(), literal_column("rowid").desc())
        .limit(limit)
    )
    return list(session.scalars(stmt).all())
