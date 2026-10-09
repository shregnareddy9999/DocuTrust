"""Deterministic fake AI adapter for tests."""

from __future__ import annotations

from app.adapters.ai.base import (
    AcademicSummaryAdapter,
    AcademicSummaryError,
    AcademicSummaryResult,
)


class FakeAcademicSummaryAdapter(AcademicSummaryAdapter):
    def __init__(
        self,
        summary: str = "Aarav Demo submitted synthetic academic documents with available semester details.",
        model: str = "fake-academic-summary",
        should_fail: bool = False,
    ):
        self.summary = summary
        self.model = model
        self.should_fail = should_fail
        self.prompts: list[str] = []

    def generate_summary(self, prompt: str) -> AcademicSummaryResult:
        self.prompts.append(prompt)
        if self.should_fail:
            raise AcademicSummaryError("Simulated AI summary failure")
        return AcademicSummaryResult(summary=self.summary, model=self.model)
