"""OcrAdapter interface, OcrResult, OcrRegion.

Owned by Task 05 — see tasks/05-*.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class OcrRegion:
    """A single text region detected by OCR.

    Attributes:
        text: The recognized text content.
        confidence: Character recognition confidence, 0.0–1.0.
        bbox: Bounding box as (x1, y1, x2, y2) in image pixel coordinates.
        page: 1-indexed page number for multi-page documents.
    """
    text: str
    confidence: float
    bbox: tuple[int, int, int, int]
    page: int


@dataclass
class OcrResult:
    """Normalized OCR result consumed by downstream services.

    Attributes:
        text: All region texts joined in reading order (top-to-bottom, then left-to-right).
        regions: List of detected text regions with confidence and position.
        mean_confidence: Mean confidence across all regions, or None if no regions.
        engine_name: Name of the OCR engine (e.g., "paddleocr").
        engine_version: Version of the OCR engine package at runtime.
        warnings: List of warning strings (e.g., "no_text_detected", per-page failures).
    """
    text: str
    regions: List[OcrRegion]
    mean_confidence: float | None
    engine_name: str
    engine_version: str
    warnings: List[str]


class OcrAdapter(ABC):
    """Abstract interface for OCR engines.

    Implementations must normalize engine-specific output to OcrResult.
    Raw engine responses must never escape the adapter module.
    """

    @abstractmethod
    def run(self, image: "PIL.Image.Image") -> OcrResult:
        """Run OCR on a single preprocessed page image.

        Args:
            image: A PIL Image in memory (already preprocessed).

        Returns:
            OcrResult with recognized text, regions, confidence, and metadata.
        """
        pass