"""SQLAlchemy model: review_actions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ReviewActionType(str, PyEnum):
    ACCEPT = "ACCEPT"
    CORRECT = "CORRECT"
    UNRESOLVED = "UNRESOLVED"


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verification_results.id"),
        nullable=False,
    )
    reviewer_ref: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[ReviewActionType] = mapped_column(
        Enum(
            ReviewActionType,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda members: [member.value for member in members],
            validate_strings=True,
        ),
        nullable=False,
    )
    corrections_json: Mapped[str] = mapped_column(Text, nullable=True)
    comment: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    verification: Mapped[VerificationResult] = relationship(back_populates="review_actions")
