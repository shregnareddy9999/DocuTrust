"""SQLAlchemy model: verification_results."""

from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class VerificationStatus(str, PyEnum):
    PENDING = "PENDING"
    VERIFIED_MATCH = "VERIFIED_MATCH"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_TRUSTED_RECORD = "NO_TRUSTED_RECORD"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH"
    PROCESSING_FAILED = "PROCESSING_FAILED"


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    registry_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("registry_records.id"),
        nullable=True,
    )
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(
            VerificationStatus,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda members: [member.value for member in members],
            validate_strings=True,
        ),
        nullable=False,
    )
    field_comparisons_json: Mapped[str] = mapped_column(Text, nullable=False)
    rule_results_json: Mapped[str] = mapped_column(Text, nullable=False)
    reason_codes_json: Mapped[str] = mapped_column(Text, nullable=False)
    supersedes_verification_id: Mapped[str | None] = mapped_column(
        ForeignKey("verification_results.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    document: Mapped[Document] = relationship(back_populates="verifications")
    registry_record: Mapped[RegistryRecord | None] = relationship(
        back_populates="verifications",
    )
    supersedes_verification: Mapped[VerificationResult | None] = relationship(
        remote_side="VerificationResult.id",
        foreign_keys=[supersedes_verification_id],
        back_populates="superseded_by",
    )
    superseded_by: Mapped[list[VerificationResult]] = relationship(
        foreign_keys=[supersedes_verification_id],
        back_populates="supersedes_verification",
    )
    review_actions: Mapped[list[ReviewAction]] = relationship(back_populates="verification")
    blockchain_records: Mapped[list[BlockchainRecord]] = relationship(
        back_populates="verification",
    )
