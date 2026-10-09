"""Academic summary generation from persisted OCR/extraction data."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

import app.adapters.ai as ai_adapters
from app.adapters.ai.base import AcademicSummaryError
from app.models.document import DocumentCategory, ProcessingState
from app.models.extraction import ExtractionStatus
from app.repositories import documents_repo, extraction_repo
from app.services.extraction_service import extract_fields
from app.services.ocr_service import OcrProcessingError, process_document


class AcademicSummaryValidationError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class AcademicSummaryGenerationError(RuntimeError):
    pass


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _parse_json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _field_lines(fields: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for name, payload in fields.items():
        value = None
        source = "ocr"
        if isinstance(payload, dict):
            value = payload.get("value")
            source = str(payload.get("source") or "ocr")
        if value is None or str(value).strip() == "":
            continue
        lines.append(f"{name} ({source}): {value}")
    return lines


def _document_text(document_id: str, raw_ocr_json: str, extracted_fields_json: str) -> str:
    raw = _parse_json_object(raw_ocr_json)
    text = raw.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    fields = _parse_json_object(extracted_fields_json)
    lines = _field_lines(fields)
    if lines:
        return "\n".join(lines)

    return f"No OCR text is available for document {document_id}."


def _dedupe_document_ids(document_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for document_id in document_ids:
        if document_id in seen:
            continue
        seen.add(document_id)
        ordered.append(document_id)
    return ordered


def _build_prompt(document_sections: list[str]) -> str:
    combined = "\n\n".join(document_sections)
    mode = "single-document summary" if len(document_sections) == 1 else "multi-document comparison"
    return f"""Task: {mode} for synthetic academic documents.

Rules:
- Use only the supplied OCR/extracted text.
- Do not invent marks, grades, CGPA, percentages, dates, institutions, subjects, ranks, attendance, achievements, or calculations.
- If text is missing or unclear, say it is not available or unclear.
- Do not make authenticity, fraud, government, or document-verdict claims.

Output:
- Keep it concise and student-friendly.
- For one document: summarize only supported academic details.
- For multiple documents: compare supported similarities, differences, changes over time, and inconsistencies. Cite the document label for each important observation.

Supplied document information:
{combined}
"""


def _successful_extraction_or_process(session: Session, document_id: str):
    successful = extraction_repo.get_latest_successful_for_document(session, document_id)
    if successful is not None:
        return successful

    document = documents_repo.get_by_id(session, document_id)
    if document is None:
        raise AcademicSummaryValidationError(
            "DOCUMENT_NOT_FOUND",
            "Document not found.",
        )
    if document.processing_state == ProcessingState.OCR_IN_PROGRESS:
        raise AcademicSummaryValidationError(
            "EXTRACTION_NOT_READY",
            "Extraction is already in progress for this document.",
        )

    try:
        process_document(document_id, session)
    except OcrProcessingError as exc:
        session.commit()
        raise AcademicSummaryValidationError(
            "EXTRACTION_NOT_READY",
            "OCR could not read this document. A successful extraction is required before generating a summary.",
        ) from exc

    extraction = extract_fields(document_id, session)
    session.commit()
    if extraction is None or extraction.status != ExtractionStatus.SUCCEEDED:
        raise AcademicSummaryValidationError(
            "EXTRACTION_NOT_READY",
            "A successful extraction is required before generating a summary.",
        )
    return extraction


def generate_academic_summary(session: Session, document_ids: list[str]) -> dict[str, Any]:
    unique_ids = _dedupe_document_ids(document_ids)
    if not unique_ids:
        raise AcademicSummaryValidationError(
            "NO_DOCUMENTS_SELECTED",
            "Select at least one academic document.",
        )

    document_sections: list[str] = []
    for index, document_id in enumerate(unique_ids, start=1):
        document = documents_repo.get_by_id(session, document_id)
        if document is None:
            raise AcademicSummaryValidationError(
                "DOCUMENT_NOT_FOUND",
                "Document not found.",
            )

        if _enum_value(document.category) != DocumentCategory.ACADEMIC_CERTIFICATE.value:
            raise AcademicSummaryValidationError(
                "NON_ACADEMIC_DOCUMENT",
                "Only academic certificate documents can be summarized.",
            )

        extraction = _successful_extraction_or_process(session, document_id)

        document_text = _document_text(
            document_id=document_id,
            raw_ocr_json=extraction.raw_ocr_json,
            extracted_fields_json=extraction.extracted_fields_json,
        )
        document_sections.append(
            f"Document {index} ({document.original_filename}, id {document.id}):\n{document_text}"
        )

    adapter = ai_adapters.get_academic_summary_adapter()
    try:
        result = adapter.generate_summary(_build_prompt(document_sections))
    except AcademicSummaryError as exc:
        raise AcademicSummaryGenerationError(
            "Could not generate the academic summary. Confirm that Ollama is running locally."
        ) from exc

    return {
        "summary": result.summary,
        "documents_analyzed": len(unique_ids),
        "model": result.model,
    }
