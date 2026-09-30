"""OCR seam shared by Dev (Aadhaar linkage) and Shregna.

`extract_fields(file)` is the ONE function others call. Today it is a deterministic MOCK that
returns fixed values; a real engine can replace `_mock_extract` later without changing callers.

Rules that apply here (AGENTS.md):
  * Rule 10: if PaddleOCR is added, `import paddleocr` happens ONLY in this module.
  * Rule 5:  `ocr_confidence` describes character recognition only. It is not an authenticity score.
  * Rule 7:  mock numbers are synthetic and start with 0000 (a real Aadhaar never starts with 0 or 1).
  * Privacy: OCRError carries a short code only, never extracted text, so the number cannot leak
             through an exception message or a log line.

Return shape (stable contract for callers):
    {"aadhaar_number": str | None,   # 12 digits, no spaces, or None if not found
     "name": str | None,
     "ocr_confidence": float,        # 0.0-1.0, recognition only
     "engine": "mock"}
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

ENGINE = "mock"  # swap point: "mock" today


class OCRError(Exception):
    """Technical OCR failure. `.code` is a fixed string; never put extracted text in it."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# Fixed synthetic values. Numbers start with 0000 so they can never be a real Aadhaar number.
DEMO_NUMBER_LINKED = "000000001001"        # linked to DEMO-STU-001 by routers/aadhaar.py
DEMO_NUMBER_UNREGISTERED = "000000009999"  # linked to nobody

_FIXED = {"aadhaar_number": DEMO_NUMBER_LINKED, "name": "Aarav Demo", "ocr_confidence": 0.98}


def _filename_of(file, filename: str | None) -> str:
    if filename:
        return filename
    if isinstance(file, (str, Path)):
        return Path(file).name
    return getattr(file, "name", "") or ""


def _mock_extract(filename: str) -> dict:
    """Deterministic: the same filename always gives the same result (Rule 8).

    Default -> fixed linked demo values. Filename hints exist only so every outcome can be demoed:
      'ocrfail'      -> raises OCRError (simulated engine crash)
      'nonumber'     -> no number found
      'unregistered' -> a demo number that is linked to nobody
    """
    name = filename.lower()
    if "ocrfail" in name:
        raise OCRError("OCR_ENGINE_ERROR")
    result = dict(_FIXED, engine=ENGINE)
    if "nonumber" in name:
        result["aadhaar_number"] = None
    elif "unregistered" in name:
        result["aadhaar_number"] = DEMO_NUMBER_UNREGISTERED
    return result


def extract_fields(file: "bytes | bytearray | BinaryIO | str | Path", filename: str | None = None) -> dict:
    """Extract fields from an uploaded document.

    `file` may be raw bytes, an open binary file-like object, or a path. `filename` is optional
    (file-like objects and paths supply their own). Raises OCRError on technical failure.
    """
    if isinstance(file, (bytes, bytearray)):
        data = bytes(file)
    elif isinstance(file, (str, Path)):
        try:
            data = Path(file).read_bytes()
        except OSError as exc:
            raise OCRError("INPUT_UNREADABLE") from exc
    else:
        try:
            data = file.read()
        except (OSError, ValueError, AttributeError) as exc:
            raise OCRError("INPUT_UNREADABLE") from exc
    if not data:
        raise OCRError("EMPTY_INPUT")
    return _mock_extract(_filename_of(file, filename))
