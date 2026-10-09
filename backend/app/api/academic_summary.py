"""AI academic summary endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.academic_summary_service import (
    AcademicSummaryGenerationError,
    AcademicSummaryValidationError,
    generate_academic_summary,
)

router = APIRouter()


class AcademicSummaryRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)


def _http_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": {}}},
    )


@router.post("/academic-summary")
async def create_academic_summary(
    request: AcademicSummaryRequest,
    db: Session = Depends(get_db),
):
    try:
        return generate_academic_summary(db, request.document_ids)
    except AcademicSummaryValidationError as exc:
        if exc.code == "DOCUMENT_NOT_FOUND":
            _http_error(404, exc.code, exc.message)
        if exc.code in {"NO_DOCUMENTS_SELECTED", "NON_ACADEMIC_DOCUMENT"}:
            _http_error(400, exc.code, exc.message)
        _http_error(409, exc.code, exc.message)
    except AcademicSummaryGenerationError as exc:
        _http_error(503, "AI_SUMMARY_UNAVAILABLE", str(exc))
