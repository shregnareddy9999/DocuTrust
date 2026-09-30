"""SQLAlchemy model: marksheets (each upload is its own row; history is never overwritten)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Marksheet(Base):
    __tablename__ = "marksheets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    subjects_json: Mapped[str] = mapped_column(Text, nullable=False)  # {"Mathematics": 68, ...}
    total: Mapped[float | None] = mapped_column(Float, nullable=True)
    cgpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_label: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
