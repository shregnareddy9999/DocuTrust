"""Queries for extraction_results."""

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import literal_column

from app.models.extraction import ExtractionResult, ExtractionStatus


def create(session: Session, extraction: ExtractionResult) -> ExtractionResult:
    session.add(extraction)
    session.flush()
    return extraction


def get_latest_for_document(
    session: Session,
    document_id: str,
) -> ExtractionResult | None:
    stmt = (
        select(ExtractionResult)
        .where(ExtractionResult.document_id == document_id)
        .order_by(
            ExtractionResult.created_at.desc(),
            literal_column("rowid").desc(),
        )
        .limit(1)
    )
    return session.scalars(stmt).first()


def get_latest_successful_for_document(
    session: Session,
    document_id: str,
) -> ExtractionResult | None:
    stmt = (
        select(ExtractionResult)
        .where(
            ExtractionResult.document_id == document_id,
            ExtractionResult.status == ExtractionStatus.SUCCEEDED,
        )
        .order_by(
            ExtractionResult.created_at.desc(),
            literal_column("rowid").desc(),
        )
        .limit(1)
    )
    return session.scalars(stmt).first()
