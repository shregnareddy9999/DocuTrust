"""SQLAlchemy model: extraction_results."""

from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ExtractionStatus(str, PyEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ExtractionResult(Base):
    __tablename__ = "extraction_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    engine_name: Mapped[str] = mapped_column(String, nullable=False)
    engine_version: Mapped[str] = mapped_column(String, nullable=False)
    raw_ocr_json: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_fields_json: Mapped[str] = mapped_column(Text, nullable=False)
    warnings_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ExtractionStatus] = mapped_column(
        Enum(
            ExtractionStatus,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda members: [member.value for member in members],
            validate_strings=True,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    document: Mapped[Document] = relationship(back_populates="extractions")
