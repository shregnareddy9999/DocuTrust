"""AI Adapter interface for academic summary generation.

Owned by AI Academic Summary feature.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AcademicSummaryResult:
    """Result from AI academic summary generation.

    Attributes:
        summary: The generated academic summary text.
        model: Name of the model used.
        documents_analyzed: Number of documents that contributed to the summary.
    """
    summary: str
    model: str
    documents_analyzed: int


class AiAdapter(ABC):
    """Abstract interface for AI academic summary adapters.

    Implementations must normalize engine-specific output to AcademicSummaryResult.
    Raw engine responses must never escape the adapter module.
    """

    @abstractmethod
    def generate_academic_summary(
        self,
        combined_ocr_text: str,
        document_count: int,
    ) -> AcademicSummaryResult:
        """Generate an academic summary from combined OCR text.

        Args:
            combined_ocr_text: Combined OCR text from one or more academic documents.
            document_count: Number of documents the text came from.

        Returns:
            AcademicSummaryResult with the generated summary.
        """
        pass