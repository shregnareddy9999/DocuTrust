"""AI summary adapter factory."""

from app.adapters.ai.ollama_adapter import OllamaAcademicSummaryAdapter
from app.config import settings


def get_academic_summary_adapter() -> OllamaAcademicSummaryAdapter:
    return OllamaAcademicSummaryAdapter(
        base_url=settings.AI_SUMMARY_OLLAMA_URL,
        model=settings.AI_SUMMARY_MODEL,
        timeout_seconds=settings.AI_SUMMARY_TIMEOUT_SECONDS,
    )
