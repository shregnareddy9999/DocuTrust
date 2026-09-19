"""GET /health.

Owned by Task 01 — see tasks/01-foundation.md.
"""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from fastapi import APIRouter

from app.config import settings
from app.db import engine

router = APIRouter()


@router.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_status = "ok"
    except SQLAlchemyError:
        database_status = "error"

    return {
        "status": "ok",
        "database": database_status,
        "ocr_adapter": settings.OCR_ENGINE,
        "blockchain": "enabled" if settings.BLOCKCHAIN_ENABLED else "disabled",
    }