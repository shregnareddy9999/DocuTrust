"""Deterministic canned OCR responses.

Owned by Task 05 — see tasks/05-*.md.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from PIL import Image

from app.adapters.ocr.base import OcrAdapter, OcrRegion, OcrResult


@dataclass
class FakeOcrConfig:
    """Configuration for the fake OCR adapter.

    Attributes:
        mode: Deterministic response mode.
        custom_text: Optional custom text for 'clean' or 'low_confidence' modes.
        custom_confidence: Optional custom confidence for regions.
    """
    mode: Literal["clean", "low_confidence", "empty", "raises", "timeout"]
    custom_text: str | None = None
    custom_confidence: float | None = None


class FakeOcrAdapter(OcrAdapter):
    """Fake OCR adapter returning deterministic canned responses.

    Modes:
        clean: High-confidence text extraction (confidence ~0.95).
        low_confidence: Low-confidence text extraction (confidence ~0.50).
        empty: No text detected (returns SUCCEEDED with no_text_detected warning).
        raises: Simulates an OCR engine exception.
        timeout: Simulates a per-page timeout.
    """

    def __init__(self, config: FakeOcrConfig | None = None):
        self.config = config or FakeOcrConfig(mode="clean")

    def run(self, image: Image.Image) -> OcrResult:
        mode = self.config.mode

        if mode == "timeout":
            # Simulate timeout by sleeping longer than test timeout (1s)
            # Tests will enforce timeout externally; this is for manual verification.
            time.sleep(2)
            raise TimeoutError("OCR timeout simulated")

        if mode == "raises":
            raise RuntimeError("Simulated OCR engine failure")

        if mode == "empty":
            return OcrResult(
                text="",
                regions=[],
                mean_confidence=None,
                engine_name="fake",
                engine_version="0.0.0-test",
                warnings=["no_text_detected"],
            )

        # clean or low_confidence
        text = self.config.custom_text or "Aarav Demo\nExample Technical Institute\nDEMO-STU-001\nB.Tech CSE\n5\nDEMO-MARK-001"
        confidence = self.config.custom_confidence if self.config.custom_confidence is not None else (
            0.95 if mode == "clean" else 0.50
        )

        # Create regions - one per line for realistic structure
        lines = text.split("\n")
        regions = []
        y = 100
        for i, line in enumerate(lines):
            if line.strip():
                regions.append(OcrRegion(
                    text=line,
                    confidence=confidence,
                    bbox=(100, y, 500, y + 30),
                    page=1,
                ))
                y += 40

        full_text = "\n".join(r.text for r in regions)
        mean_conf = sum(r.confidence for r in regions) / len(regions) if regions else None

        return OcrResult(
            text=full_text,
            regions=regions,
            mean_confidence=mean_conf,
            engine_name="fake",
            engine_version="0.0.0-test",
            warnings=[],
        )


def create_fake_adapter(
    mode: Literal["clean", "low_confidence", "empty", "raises", "timeout"] = "clean",
    custom_text: str | None = None,
    custom_confidence: float | None = None,
) -> FakeOcrAdapter:
    """Factory function to create a configured FakeOcrAdapter.

    Args:
        mode: Response mode.
        custom_text: Optional custom extracted text.
        custom_confidence: Optional custom confidence value.

    Returns:
        Configured FakeOcrAdapter instance.
    """
    config = FakeOcrConfig(
        mode=mode,
        custom_text=custom_text,
        custom_confidence=custom_confidence,
    )
    return FakeOcrAdapter(config)