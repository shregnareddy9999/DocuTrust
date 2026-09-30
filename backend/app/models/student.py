"""SQLAlchemy model: students (synthetic demo students only)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    student_ref: Mapped[str] = mapped_column(String, nullable=False, unique=True)  # e.g. DEMO-STU-101
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    aadhaar_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    aadhaar_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    source_label: Mapped[str] = mapped_column(String, nullable=False)  # always "synthetic-demo"
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
