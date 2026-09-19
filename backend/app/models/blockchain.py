
"""SQLAlchemy model: blockchain_records."""

from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class RecordingStatus(str, PyEnum):
    NOT_REQUESTED = "NOT_REQUESTED"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class BlockchainErrorCode(str, PyEnum):
    RPC_UNAVAILABLE = "RPC_UNAVAILABLE"
    TX_REVERTED = "TX_REVERTED"
    RECEIPT_TIMEOUT = "RECEIPT_TIMEOUT"
    EVENT_MISMATCH = "EVENT_MISMATCH"


class BlockchainRecord(Base):
    __tablename__ = "blockchain_records"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid4().hex
    )
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verification_results.id"),
        nullable=False,
    )
    chain_id: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_address: Mapped[str] = mapped_column(String, nullable=False)
    transaction_hash: Mapped[str] = mapped_column(String, nullable=True)
    event_digest: Mapped[str] = mapped_column(String, nullable=False)
    recording_status: Mapped[RecordingStatus] = mapped_column(
        Enum(
            RecordingStatus,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda members: [member.value for member in members],
            validate_strings=True,
        ),
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    error_code: Mapped[BlockchainErrorCode] = mapped_column(
        Enum(
            BlockchainErrorCode,
            native_enum=False,
            create_constraint=True,
            values_callable=lambda members: [member.value for member in members],
            validate_strings=True,
        ),
        nullable=True,
    )

    verification: Mapped[VerificationResult] = relationship(
        back_populates="blockchain_records"
    )