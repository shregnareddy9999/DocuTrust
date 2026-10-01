"""Academic Summary API endpoints.

Owned by AI Academic Summary feature.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.academic_summary_service import (
    DocumentNotAcademicError,
    DocumentNotFoundError,
    ExtractionNotReadyError,
    NoExtractedTextError,
    generate_academic_summary,
)

router = APIRouter(prefix="/academic-summary", tags=["academic-summary"])


class AcademicSummaryRequest(BaseModel):
    document_ids: list[str]


class AcademicSummaryResponse(BaseModel):
    summary: str
    documents_analyzed: int
    model: str


def _http_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": {}}},
    )


@router.post("", response_model=AcademicSummaryResponse, status_code=status.HTTP_200_OK)
async def create_academic_summary(
    request: AcademicSummaryRequest,
    db: Session = Depends(get_db),
):
    """Generate an academic summary from selected academic documents.

    Validates that all documents exist and are academic certificates,
    retrieves their OCR text, and generates a summary using the configured AI adapter.
    """
    try:
        result = generate_academic_summary(request.document_ids, db)
        return AcademicSummaryResponse(
            summary=result.summary,
            documents_analyzed=result.documents_analyzed,
            model=result.model,
        )
    except DocumentNotFoundError as e:
        _http_error(404, "DOCUMENT_NOT_FOUND", f"Document not found: {e}")
    except DocumentNotAcademicError as e:
        _http_error(400, "INVALID_DOCUMENT_TYPE", f"Document is not an academic certificate: {e}")
    except ExtractionNotReadyError as e:
        _http_error(409, "EXTRACTION_NOT_READY", f"Extraction not ready for document: {e}")
    except NoExtractedTextError as e:
        _http_error(422, "NO_TEXT_AVAILABLE", str(e))
    except ValueError as e:
        _http_error(400, "INVALID_REQUEST", str(e))