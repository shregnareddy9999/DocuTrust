"""SQLAlchemy model: documents."""

from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DocumentCategory(str, PyEnum):
    ACADEMIC_CERTIFICATE = "academic_certificate"
    INSTITUTIONAL_ID = "institutional_id"
    PAN_LIKE_DEMO = "pan_like_demo"
    GOVERNMENT_CERTIFICATE = "government_certificate"


class ProcessingState(str, PyEnum):
    UPLOADED = "UPLOADED"
    OCR_IN_PROGRESS = "OCR_IN_PROGRESS"
    OCR_DONE = "OCR_DONE"
    OCR_FAILED = "OCR_FAILED"


DOCUMENT_CATEGORY_ENUM = Enum(
    DocumentCategory,
    native_enum=False,
    create_constraint=True,
    values_callable=lambda members: [member.value for member in members],
    validate_strings=True,
    name="document_category",
)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    category: Mapped[DocumentCategory] = mapped_column(
        DOCUMENT_CATEGORY_ENUM,
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_state: Mapped[ProcessingState] = mapped_column(
        Enum(
            ProcessingState,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda members: [member.value for member in members],
            validate_strings=True,
        ),
        nullable=False,
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    extractions: Mapped[list[ExtractionResult]] = relationship(back_populates="document")
    verifications: Mapped[list[VerificationResult]] = relationship(back_populates="document")
