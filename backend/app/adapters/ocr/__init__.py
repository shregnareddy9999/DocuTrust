"""OCR Adapter Factory.

Owned by Task 05 — see tasks/05-*.md.
"""

from __future__ import annotations

from app.adapters.ocr.base import OcrAdapter
import app.config as config_module


def get_ocr_adapter() -> OcrAdapter:
    """Return the configured OCR adapter instance.

    Reads OCR_ENGINE from settings and returns the corresponding adapter.
    Fails fast on unknown engine values — no silent fallbacks.

    Returns:
        An OcrAdapter implementation.

    Raises:
        ValueError: If OCR_ENGINE is not a recognized value.
    """
    settings = config_module.settings
    engine = settings.OCR_ENGINE

    if engine == "fake":
        from app.adapters.ocr.fake_adapter import create_fake_adapter
        return create_fake_adapter(mode="clean")

    if engine == "paddleocr":
        from app.adapters.ocr.paddleocr_adapter import PaddleOcrAdapter
        return PaddleOcrAdapter()

    raise ValueError(
        f"Unknown OCR_ENGINE: '{engine}'. "
        f"Supported values: 'fake', 'paddleocr'"
    )