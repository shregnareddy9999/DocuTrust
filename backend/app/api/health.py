"""GET /health.

Owned by Task 01 — see tasks/01-foundation.md.
"""

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "database": "not_configured",
        "ocr_adapter": settings.OCR_ENGINE,
        "blockchain": "enabled" if settings.BLOCKCHAIN_ENABLED else "disabled",
    }