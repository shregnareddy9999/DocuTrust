"""Academic summary adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AcademicSummaryResult:
    summary: str
    model: str


class AcademicSummaryError(RuntimeError):
    """Raised when the local AI summary adapter cannot return a summary."""


class AcademicSummaryAdapter(ABC):
    @abstractmethod
    def generate_summary(self, prompt: str) -> AcademicSummaryResult:
        """Generate a concise summary from the supplied prompt."""
