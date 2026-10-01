"""Ollama AI adapter.

External Ollama communication is isolated in this adapter.
"""

from __future__ import annotations

from typing import Any

import httpx


ACADEMIC_SUMMARY_PROMPT = """
You are an AI assistant summarizing academic documents for a student.

Use ONLY the OCR text supplied below.

STRICT RULES:
1. Never invent information.
2. Never estimate missing marks, grades, GPA, CGPA, percentages, ranks, attendance, or achievements.
3. If Student ID is present, include it exactly as supplied.
4. If Student ID is not present, write: Student ID: Not available.
5. If another required field is missing, write: Not available.
6. Keep the response concise.
7. Do not repeat the OCR text.
8. Do not write a long introduction or conclusion.
9. Do not make claims about authenticity, genuineness, fraud, government verification, or document validity.
10. Treat the documents as synthetic demo documents for the DocuTrust hackathon.

For ONE document, use this format:

Academic Summary

Student Name: ...
Student ID: ...
Institution: ...
Course: ...

Academic Performance:
- Semester/date: ...
- GPA/SGPA: ...
- Important subjects and marks/grades: ...
- Academic status: ...

For MULTIPLE documents:
- Identify the student using the supplied information.
- Briefly compare the semesters/documents.
- Mention available GPA/SGPA values.
- Mention important subjects/marks/grades only when present.
- Keep the comparison compact.

Maximum response length: approximately 250 words.

OCR DOCUMENTS:
"""


class OllamaAdapter:
    """Adapter for local Ollama inference."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 180,
    ):
        self.base_url = (
            base_url or "http://127.0.0.1:11434"
        ).rstrip("/")

        self.model = model or "llama3.2:latest"

        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
    ) -> str:
        """Generate a response from Ollama."""

        combined_prompt = prompt

        if system:
            combined_prompt = (
                f"{system}\n\n"
                f"{prompt}"
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": combined_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 300,
            },
        }

        try:
            with httpx.Client(
                timeout=self.timeout_seconds
            ) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )

                response.raise_for_status()

                data = response.json()

        except httpx.TimeoutException as exc:
            raise RuntimeError(
                "The AI model request timed out. "
                "Please try again or check if the local "
                "Ollama model is responding."
            ) from exc

        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"Ollama request failed: {exc}"
            ) from exc

        except ValueError as exc:
            raise RuntimeError(
                "Ollama returned an invalid response."
            ) from exc

        generated_text = data.get("response")

        if not isinstance(generated_text, str):
            raise RuntimeError(
                "Ollama did not return generated text."
            )

        generated_text = generated_text.strip()

        if not generated_text:
            raise RuntimeError(
                "Ollama returned an empty response."
            )

        return generated_text


def build_academic_summary_prompt(
    documents_text: str,
) -> str:
    """Build the academic-summary prompt."""

    return (
        ACADEMIC_SUMMARY_PROMPT
        + "\n"
        + documents_text
    )