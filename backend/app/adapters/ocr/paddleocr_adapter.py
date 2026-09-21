"""PaddleOCR adapter — the ONLY paddleocr import.

Owned by Task 05 — see tasks/05-*.md.
"""

from __future__ import annotations

from typing import List, Optional

from PIL import Image

from app.adapters.ocr.base import OcrAdapter, OcrRegion, OcrResult
from app.config import settings


class PaddleOcrAdapter(OcrAdapter):
    """PaddleOCR adapter with lazy initialization.

    Normalizes PaddleOCR's raw quadrilateral output to OcrResult.
    Raw PaddleOCR structures never escape this module.
    """

    def __init__(self):
        self._ocr_engine: Optional[object] = None
        self._engine_version: Optional[str] = None

    def _get_engine(self):
        """Lazy initialization of PaddleOCR engine."""
        if self._ocr_engine is None:
            try:
                from paddleocr import PaddleOCR
            except ImportError as e:
                raise RuntimeError(
                    "PaddleOCR not installed. Install with 'pip install paddleocr' "
                    "and ensure PaddlePaddle is available for your Python version."
                ) from e

            # Initialize PaddleOCR with configured language, CPU inference
            self._ocr_engine = PaddleOCR(
                lang=settings.OCR_LANGUAGE,
                use_angle_cls=False,
                use_gpu=False,
                show_log=False,
            )
            # Capture engine version at runtime
            try:
                import paddleocr
                self._engine_version = getattr(paddleocr, "__version__", "unknown")
            except Exception:
                self._engine_version = "unknown"

        return self._ocr_engine

    def _get_engine_version(self) -> str:
        """Get PaddleOCR version, initializing if necessary."""
        if self._engine_version is None:
            self._get_engine()
        return self._engine_version or "unknown"

    def _normalize_quad_to_bbox(self, quad: List[List[float]]) -> tuple[int, int, int, int]:
        """Convert PaddleOCR quadrilateral [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] to (x1,y1,x2,y2)."""
        xs = [int(point[0]) for point in quad]
        ys = [int(point[1]) for point in quad]
        return (min(xs), min(ys), max(xs), max(ys))

    def _sort_regions_reading_order(self, regions: List[OcrRegion]) -> List[OcrRegion]:
        """Sort regions top-to-bottom, then left-to-right."""
        return sorted(regions, key=lambda r: (r.bbox[1], r.bbox[0]))

    def run(self, image: Image.Image) -> OcrResult:
        """Run PaddleOCR on a preprocessed page image.

        Args:
            image: A PIL Image in memory (already preprocessed).

        Returns:
            OcrResult with normalized text, regions, confidence, and metadata.
        """
        engine = self._get_engine()
        engine_version = self._get_engine_version()

        # Convert PIL Image to format PaddleOCR expects (numpy array)
        import numpy as np
        img_array = np.array(image)

        # Run OCR - PaddleOCR returns list of lists of [box, (text, confidence)]
        try:
            raw_result = engine.ocr(img_array, cls=False)
        except Exception as e:
            raise RuntimeError(f"PaddleOCR inference failed: {type(e).__name__}: {e}") from e

        # Parse results
        regions: List[OcrRegion] = []
        warnings: List[str] = []

        if raw_result and raw_result[0]:
            for line in raw_result[0]:
                try:
                    # line format: [box, (text, confidence)]
                    box = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    text, confidence = line[1]

                    if text and text.strip():
                        bbox = self._normalize_quad_to_bbox(box)
                        regions.append(OcrRegion(
                            text=text.strip(),
                            confidence=float(confidence),
                            bbox=bbox,
                            page=1,  # Single page at a time
                        ))
                except (IndexError, ValueError, TypeError) as e:
                    warnings.append(f"Failed to parse OCR line: {type(e).__name__}: {e}")
                    continue

        # Sort regions in reading order
        regions = self._sort_regions_reading_order(regions)

        # Join text in reading order
        full_text = "\n".join(r.text for r in regions)

        # Compute mean confidence
        mean_confidence = None
        if regions:
            mean_confidence = sum(r.confidence for r in regions) / len(regions)

        return OcrResult(
            text=full_text,
            regions=regions,
            mean_confidence=mean_confidence,
            engine_name="paddleocr",
            engine_version=engine_version,
            warnings=warnings,
        )