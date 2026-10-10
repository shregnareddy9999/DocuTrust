"""Local Ollama adapter for academic summaries."""

from __future__ import annotations

import httpx

from app.adapters.ai.base import (
    AcademicSummaryAdapter,
    AcademicSummaryError,
    AcademicSummaryResult,
)


class OllamaAcademicSummaryAdapter(AcademicSummaryAdapter):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:latest",
        timeout_seconds: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_summary(self, prompt: str) -> AcademicSummaryResult:
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0,
                        "num_ctx": 4096,
                        "num_predict": 420,
                    },
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AcademicSummaryError("Could not reach the local AI summary service") from exc

        summary = payload.get("response")
        if not isinstance(summary, str) or not summary.strip():
            raise AcademicSummaryError("The local AI summary service returned no summary")

        model = payload.get("model")
        return AcademicSummaryResult(
            summary=summary.strip(),
            model=model if isinstance(model, str) and model else self.model,
        )
