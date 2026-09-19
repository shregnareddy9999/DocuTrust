"""SQLAlchemy model: registry_records."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.document import DOCUMENT_CATEGORY_ENUM, DocumentCategory


class RegistryRecord(Base):
    __tablename__ = "registry_records"
    __table_args__ = (
        UniqueConstraint("category", "synthetic_record_key"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    category: Mapped[DocumentCategory] = mapped_column(
        DOCUMENT_CATEGORY_ENUM,
        nullable=False,
    )
    synthetic_record_key: Mapped[str] = mapped_column(String, nullable=False)
    fields_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_label: Mapped[str] = mapped_column(String, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    verifications: Mapped[list[VerificationResult]] = relationship(
        back_populates="registry_record",
    )
