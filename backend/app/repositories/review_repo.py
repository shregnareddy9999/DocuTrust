"""Queries for review_actions."""

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import literal_column

from app.models.review import ReviewAction


def create(session: Session, action: ReviewAction) -> ReviewAction:
    session.add(action)
    session.flush()
    return action


def list_for_verification(
    session: Session,
    verification_id: str,
) -> list[ReviewAction]:
    stmt = (
        select(ReviewAction)
        .where(ReviewAction.verification_id == verification_id)
        .order_by(
            ReviewAction.created_at.desc(),
            literal_column("rowid").desc(),
        )
    )
    return list(session.scalars(stmt).all())
