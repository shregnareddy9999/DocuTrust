"""SQLAlchemy model: student_documents (links an uploaded document to a student; additive history)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StudentDocument(Base):
    __tablename__ = "student_documents"
    __table_args__ = (UniqueConstraint("student_id", "document_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3... per student + category
    linked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
