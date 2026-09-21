"""Deterministic canned OCR responses.

Owned by Task 05 — see tasks/05-*.md.

Default clean/low_confidence output is two-column (label left, value right)
so Task 06 mapping can run without inventing values. custom_text still splits
by newline for unit tests that pass an override.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from PIL import Image

from app.adapters.ocr.base import OcrAdapter, OcrRegion, OcrResult
from app.fixtures.fixture_data import FIXTURES
from app.fixtures.generate_samples import FIELD_LABELS


# Two-column layout aligned with generate_samples.MARGIN / MARGIN+340.
_LABEL_X1, _LABEL_X2 = 60, 320
_VALUE_X1, _VALUE_X2 = 400, 740
_ROW_Y0 = 140
_ROW_H = 55


def _academic_two_column_rows() -> list[tuple[str, str]]:
    fields = FIXTURES["academic_certificate"]["fields"]
    return [
        (FIELD_LABELS[name], str(value))
        for name, value in fields.items()
        if value is not None
    ]


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

        confidence = self.config.custom_confidence if self.config.custom_confidence is not None else (
            0.95 if mode == "clean" else 0.50
        )

        if self.config.custom_text is not None:
            regions = []
            y = 100
            for line in self.config.custom_text.split("\n"):
                if line.strip():
                    regions.append(
                        OcrRegion(
                            text=line,
                            confidence=confidence,
                            bbox=(100, y, 500, y + 30),
                            page=1,
                        )
                    )
                    y += 40
        else:
            regions = []
            y = _ROW_Y0
            for label, value in _academic_two_column_rows():
                regions.append(
                    OcrRegion(
                        text=label,
                        confidence=confidence,
                        bbox=(_LABEL_X1, y, _LABEL_X2, y + 20),
                        page=1,
                    )
                )
                regions.append(
                    OcrRegion(
                        text=value,
                        confidence=confidence,
                        bbox=(_VALUE_X1, y, _VALUE_X2, y + 20),
                        page=1,
                    )
                )
                y += _ROW_H

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
    """Factory function to create a configured FakeOcrAdapter."""
    config = FakeOcrConfig(
        mode=mode,
        custom_text=custom_text,
        custom_confidence=custom_confidence,
    )
    return FakeOcrAdapter(config)
