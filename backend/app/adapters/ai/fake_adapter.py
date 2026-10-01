"""Deterministic fake AI adapter for academic summary tests.

Owned by AI Academic Summary feature.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.adapters.ai.base import AcademicSummaryResult, AiAdapter


@dataclass
class FakeAiConfig:
    """Configuration for the fake AI adapter.

    Attributes:
        mode: Deterministic response mode.
        custom_summary: Optional custom summary text for 'success' mode.
    """
    mode: Literal["success", "empty_text", "connection_error", "timeout", "http_error"]
    custom_summary: str | None = None


class FakeAiAdapter(AiAdapter):
    """Fake AI adapter returning deterministic canned responses.

    Modes:
        success: Returns a realistic academic summary.
        empty_text: Simulates empty OCR text input.
        connection_error: Simulates Ollama connection failure.
        timeout: Simulates request timeout.
        http_error: Simulates HTTP error response.
    """

    _DEFAULT_SUMMARY = (
        "AI Academic Summary (Demo)\n\n"
        "Student: Aarav Demo\n"
        "Student ID: DEMO-2026-001\n"
        "Institution: Oriental University\n"
        "Course: B.Tech Computer Science and Engineering\n\n"
        "Semester 1: Data Structures (85%), Calculus (78%), Physics (82%)\n"
        "Semester 2: Algorithms (88%), Linear Algebra (80%), Chemistry (75%)\n"
        "Semester 3: Database Systems (90%), Operating Systems (85%), "
        "Computer Networks (83%)\n\n"
        "Note: This summary is based on synthetic demo documents. "
        "Grades and subjects shown are from the supplied OCR text only. "
        "Information not present in the OCR text is not included."
    )

    def __init__(self, config: FakeAiConfig | None = None):
        self.config = config or FakeAiConfig(mode="success")

    def generate_academic_summary(
        self,
        combined_ocr_text: str,
        document_count: int,
    ) -> AcademicSummaryResult:
        mode = self.config.mode

        if mode == "empty_text":
            return AcademicSummaryResult(
                summary="No text available from the submitted documents to generate a summary.",
                model="fake-model",
                documents_analyzed=document_count,
            )

        if mode == "connection_error":
            return AcademicSummaryResult(
                summary=(
                    "Could not connect to the local AI model (Ollama). "
                    "Please ensure Ollama is running at the configured URL and the model is available."
                ),
                model="fake-model",
                documents_analyzed=document_count,
            )

        if mode == "timeout":
            return AcademicSummaryResult(
                summary=(
                    "The AI model request timed out. Please try again or check if the model is responding."
                ),
                model="fake-model",
                documents_analyzed=document_count,
            )

        if mode == "http_error":
            return AcademicSummaryResult(
                summary=(
                    "The AI model returned an error (HTTP 500). "
                    "Please check the model configuration."
                ),
                model="fake-model",
                documents_analyzed=document_count,
            )

        # success mode
        summary = self.config.custom_summary or self._DEFAULT_SUMMARY
        return AcademicSummaryResult(
            summary=summary,
            model="fake-model",
            documents_analyzed=document_count,
        )


def create_fake_adapter(
    mode: Literal["success", "empty_text", "connection_error", "timeout", "http_error"] = "success",
    custom_summary: str | None = None,
) -> FakeAiAdapter:
    """Factory function to create a configured FakeAiAdapter."""
    config = FakeAiConfig(mode=mode, custom_summary=custom_summary)
    return FakeAiAdapter(config)