"""Retention cleanup for expired DocuTrust documents.

Dry-run is the default. Actual cleanup requires --delete.

Task 12 requirements:
- Retain documents for RETENTION_DAYS (default: 7).
- Delete expired uploaded files.
- Blank raw OCR data.
- Preserve extracted fields.
- Preserve verification history.
- Preserve review history.
- Preserve blockchain records.
- Never delete synthetic registry records.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.document import Document
from app.models.extraction import ExtractionResult
from app.services.upload_service import safe_upload_path


DEFAULT_RETENTION_DAYS = 7


@dataclass
class CleanupSummary:
    """Summary of one cleanup run."""

    expired_documents: int = 0
    files_deleted: int = 0
    files_missing: int = 0
    raw_ocr_cleared: int = 0


def get_retention_days() -> int:
    """Return RETENTION_DAYS or the documented default."""
    raw_value = os.getenv(
        "RETENTION_DAYS",
        str(DEFAULT_RETENTION_DAYS),
    )

    try:
        value = int(raw_value)
    except ValueError:
        return DEFAULT_RETENTION_DAYS

    if value <= 0:
        return DEFAULT_RETENTION_DAYS

    return value


def _make_cutoff(retention_days: int) -> datetime:
    """Return the naive UTC cutoff used by the project's DateTime columns."""
    return datetime.utcnow() - timedelta(days=retention_days)


def _get_expired_documents(
    session: Session,
    cutoff: datetime,
) -> list[Document]:
    """Return documents older than the retention cutoff."""
    statement = (
        select(Document)
        .where(Document.uploaded_at < cutoff)
        .order_by(Document.uploaded_at.asc())
    )

    return list(session.scalars(statement).all())


def _delete_uploaded_file(
    document: Document,
    *,
    dry_run: bool,
) -> str:
    """Delete an expired document's uploaded file.

    Returns:
        "deleted" when the file exists and is deleted or would be deleted.
        "missing" when the file does not exist.
    """
    upload_path: Path = safe_upload_path(document.storage_key)

    if not upload_path.exists():
        return "missing"

    if not dry_run:
        upload_path.unlink()

    return "deleted"


def _clear_raw_ocr(
    session: Session,
    document_id: str,
    *,
    dry_run: bool,
) -> bool:
    """Blank raw OCR while preserving extracted fields."""
    statement = select(ExtractionResult).where(
        ExtractionResult.document_id == document_id
    )

    extractions = list(session.scalars(statement).all())

    changed = False

    for extraction in extractions:
        if extraction.raw_ocr_json:
            changed = True

            if not dry_run:
                extraction.raw_ocr_json = ""

    return changed


def cleanup_expired(
    session: Session,
    *,
    retention_days: int | None = None,
    delete: bool = False,
) -> CleanupSummary:
    """Run retention cleanup.

    Args:
        session: Existing SQLAlchemy session.
        retention_days: Number of days to retain data.
        delete: When False, perform a dry-run. When True, apply changes.

    Returns:
        CleanupSummary describing what was found/changed.
    """
    if retention_days is None:
        retention_days = get_retention_days()

    if retention_days <= 0:
        raise ValueError("retention_days must be greater than zero")

    cutoff = _make_cutoff(retention_days)
    expired_documents = _get_expired_documents(session, cutoff)

    summary = CleanupSummary(
        expired_documents=len(expired_documents),
    )

    for document in expired_documents:
        file_status = _delete_uploaded_file(
            document,
            dry_run=not delete,
        )

        if file_status == "deleted":
            summary.files_deleted += 1
        else:
            summary.files_missing += 1

        if _clear_raw_ocr(
            session,
            document.id,
            dry_run=not delete,
        ):
            summary.raw_ocr_cleared += 1

    if delete:
        session.commit()

    return summary


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Clean expired DocuTrust document data.",
    )

    parser.add_argument(
        "--delete",
        action="store_true",
        help=(
            "Actually delete expired uploaded files and blank raw OCR. "
            "Without this flag the command performs a dry-run."
        ),
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        default=None,
        help="Override RETENTION_DAYS for this run.",
    )

    return parser


def main() -> int:
    """Run cleanup from the command line."""
    parser = _build_parser()
    args = parser.parse_args()

    retention_days = (
        args.retention_days
        if args.retention_days is not None
        else get_retention_days()
    )

    if retention_days <= 0:
        parser.error("--retention-days must be greater than zero")

    dry_run = not args.delete

    print(
        "Retention cleanup: "
        f"{'DRY-RUN' if dry_run else 'DELETE'} "
        f"(retention={retention_days} days)"
    )

    session = SessionLocal()

    try:
        summary = cleanup_expired(
            session,
            retention_days=retention_days,
            delete=args.delete,
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(f"Expired documents: {summary.expired_documents}")
    print(f"Files deleted: {summary.files_deleted}")
    print(f"Files missing: {summary.files_missing}")
    print(f"Raw OCR records affected: {summary.raw_ocr_cleared}")

    if dry_run:
        print("No changes were made. Use --delete to apply cleanup.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())