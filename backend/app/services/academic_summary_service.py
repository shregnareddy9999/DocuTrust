"""AI Academic Summary service.

Builds an academic summary from OCR text already stored for academic
certificate documents.

This service reuses the existing DocuTrust OCR pipeline and AI adapter.
It does not change verification, matching, or blockchain behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.adapters.ai import get_ai_adapter
from app.models.document import DocumentCategory, ProcessingState
from app.models.extraction import ExtractionStatus
from app.repositories import documents_repo, extraction_repo
from app.services.extraction_service import extract_fields
from app.services.ocr_service import OcrProcessingError, process_document


class DocumentNotFoundError(Exception):
    """Raised when a requested document does not exist."""

    def __init__(self, document_id: str):
        super().__init__(document_id)


class DocumentNotAcademicError(Exception):
    """Raised when a document is not an academic certificate."""

    def __init__(self, document_id: str):
        super().__init__(document_id)


class ExtractionNotReadyError(Exception):
    """Raised when OCR/extraction is still being processed."""

    def __init__(self, document_id: str):
        super().__init__(document_id)


class NoExtractedTextError(Exception):
    """Raised when an academic document has no usable OCR text."""

    def __init__(self, document_id: str):
        super().__init__(
            f"No usable OCR text is available for document: {document_id}"
        )


@dataclass
class AcademicSummaryResult:
    """Internal result returned by the Academic Summary service."""

    summary: str
    documents_analyzed: int
    model: str


def _extract_text_from_extraction(extraction) -> str:
    """Read usable text from a persisted OCR extraction."""

    if extraction is None:
        return ""

    raw_ocr_json = getattr(extraction, "raw_ocr_json", None)

    if not raw_ocr_json:
        return ""

    try:
        raw = json.loads(raw_ocr_json)
    except (TypeError, ValueError):
        return ""

    if not isinstance(raw, dict):
        return ""

    text = raw.get("text")

    if isinstance(text, str):
        return text.strip()

    regions = raw.get("regions")

    if not isinstance(regions, list):
        return ""

    texts: list[str] = []

    for region in regions:
        if not isinstance(region, dict):
            continue

        region_text = region.get("text")

        if isinstance(region_text, str) and region_text.strip():
            texts.append(region_text.strip())

    return "\n".join(texts).strip()


def _ensure_extraction(
    document_id: str,
    session: Session,
):
    """Ensure successful OCR exists, using the existing OCR pipeline."""

    document = documents_repo.get_by_id(session, document_id)

    if document is None:
        raise DocumentNotFoundError(document_id)

    if document.processing_state == ProcessingState.OCR_IN_PROGRESS:
        raise ExtractionNotReadyError(document_id)

    successful = extraction_repo.get_latest_successful_for_document(
        session,
        document_id,
    )

    if successful is None:
        try:
            process_document(document_id, session)
        except OcrProcessingError as exc:
            raise ExtractionNotReadyError(document_id) from exc

        successful = extraction_repo.get_latest_successful_for_document(
            session,
            document_id,
        )

    if successful is None:
        raise ExtractionNotReadyError(document_id)

    # Reuse the existing deterministic OCR-to-fields extraction service.
    extraction = extract_fields(document_id, session)

    if extraction is None:
        raise ExtractionNotReadyError(document_id)

    if extraction.status == ExtractionStatus.FAILED:
        raise ExtractionNotReadyError(document_id)

    session.commit()

    return extraction


def generate_academic_summary(
    document_ids: list[str],
    session: Session,
) -> AcademicSummaryResult:
    """Generate a concise AI summary for academic documents."""

    if not document_ids:
        raise ValueError("At least one document ID is required.")

    documents = []

    # ---------------------------------------------------------
    # 1. Validate every requested document.
    # ---------------------------------------------------------
    for document_id in document_ids:
        document = documents_repo.get_by_id(
            session,
            document_id,
        )

        if document is None:
            raise DocumentNotFoundError(document_id)

        if document.category != DocumentCategory.ACADEMIC_CERTIFICATE:
            raise DocumentNotAcademicError(document_id)

        documents.append(document)

    # ---------------------------------------------------------
    # 2. Make sure OCR exists and collect OCR text.
    # ---------------------------------------------------------
    extracted_texts: list[str] = []

    for document in documents:
        extraction = _ensure_extraction(
            document.id,
            session,
        )

        text = _extract_text_from_extraction(
            extraction,
        )

        if not text:
            raise NoExtractedTextError(document.id)

        extracted_texts.append(text)

    # ---------------------------------------------------------
    # 3. Combine OCR text from all selected documents.
    # ---------------------------------------------------------
    combined_ocr_text = "\n\n".join(
        (
            f"DOCUMENT {index + 1}\n"
            f"{text}"
        )
        for index, text in enumerate(extracted_texts)
    )

    # ---------------------------------------------------------
    # 4. Use the project's existing AI adapter.
    # ---------------------------------------------------------
    adapter = get_ai_adapter()

    result = adapter.generate_academic_summary(
        combined_ocr_text,
        len(documents),
    )

    # The adapter already returns the normalized AI result.
    model = getattr(adapter, "model", None)

    if not model:
        model = getattr(result, "model", "unknown")

    return AcademicSummaryResult(
        summary=result.summary,
        documents_analyzed=len(documents),
        model=model,
    )
