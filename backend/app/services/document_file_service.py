"""Document file preview and guarded removal helpers."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.repositories import documents_repo, verification_repo
from app.services.upload_service import safe_upload_path
from app.services.verification_service import DocumentNotFoundError


class DocumentFileNotFoundError(Exception):
    """The document row exists, but its stored file is unavailable."""


class DocumentHasHistoryError(Exception):
    """The document has verification history and cannot be removed destructively."""


def get_document_file(session: Session, document_id: str) -> tuple[Path, str, str]:
    document = documents_repo.get_by_id(session, document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)

    path = safe_upload_path(document.storage_key)
    if not path.exists():
        raise DocumentFileNotFoundError(document_id)

    return path, document.mime_type, document.original_filename


def delete_document_without_history(session: Session, document_id: str) -> None:
    document = documents_repo.get_by_id(session, document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)

    if verification_repo.list_for_document(session, document_id):
        raise DocumentHasHistoryError(document_id)

    path = safe_upload_path(document.storage_key)
    documents_repo.delete_with_extractions(session, document)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        session.rollback()
        raise
    session.commit()
