"""GET /document-types endpoint for Task 06."""

from fastapi import APIRouter

from app.domain.schemas import document_types


router = APIRouter()


@router.get("/document-types")
def get_document_types() -> list[dict]:
    """Return the category schema registry."""
    return document_types()
