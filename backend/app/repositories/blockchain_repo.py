"""Queries for blockchain_records."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import literal_column, nulls_last

from app.models.blockchain import BlockchainErrorCode, BlockchainRecord, RecordingStatus


def _newest_first():
    return (
        nulls_last(BlockchainRecord.submitted_at.desc()),
        literal_column("rowid").desc(),
    )


def create(session: Session, record: BlockchainRecord) -> BlockchainRecord:
    session.add(record)
    session.flush()
    return record


def get_by_verification_id(
    session: Session,
    verification_id: str,
) -> list[BlockchainRecord]:
    stmt = (
        select(BlockchainRecord)
        .where(BlockchainRecord.verification_id == verification_id)
        .order_by(*_newest_first())
    )
    return list(session.scalars(stmt).all())


def get_active_for_verification(
    session: Session,
    verification_id: str,
) -> BlockchainRecord | None:
    stmt = (
        select(BlockchainRecord)
        .where(
            BlockchainRecord.verification_id == verification_id,
            BlockchainRecord.recording_status != RecordingStatus.FAILED,
        )
        .order_by(*_newest_first())
        .limit(1)
    )
    return session.scalars(stmt).first()


def mark_confirmed(
    session: Session,
    record_id: str,
    confirmed_at: datetime,
) -> BlockchainRecord | None:
    record = session.get(BlockchainRecord, record_id)
    if record is None or record.recording_status != RecordingStatus.PENDING:
        return None
    record.recording_status = RecordingStatus.CONFIRMED
    record.confirmed_at = confirmed_at
    session.flush()
    return record


def mark_failed(
    session: Session,
    record_id: str,
    error_code: BlockchainErrorCode,
) -> BlockchainRecord | None:
    record = session.get(BlockchainRecord, record_id)
    if record is None or record.recording_status != RecordingStatus.PENDING:
        return None
    record.recording_status = RecordingStatus.FAILED
    record.error_code = error_code
    session.flush()
    return record
