"""Queries for verification_results."""

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import literal_column

from app.models.verification import VerificationResult


def create(session: Session, result: VerificationResult) -> VerificationResult:
    session.add(result)
    session.flush()
    return result


def get_by_id(session: Session, verification_id: str) -> VerificationResult | None:
    return session.get(VerificationResult, verification_id)


def get_latest_for_document(
    session: Session,
    document_id: str,
) -> VerificationResult | None:
    stmt = (
        select(VerificationResult)
        .where(VerificationResult.document_id == document_id)
        .order_by(
            VerificationResult.created_at.desc(),
            literal_column("rowid").desc(),
        )
        .limit(1)
    )
    return session.scalars(stmt).first()


def list_for_document(
    session: Session,
    document_id: str,
) -> list[VerificationResult]:
    stmt = (
        select(VerificationResult)
        .where(VerificationResult.document_id == document_id)
        .order_by(
            VerificationResult.created_at.desc(),
            literal_column("rowid").desc(),
        )
    )
    return list(session.scalars(stmt).all())
