"""Preprocessing and OCR orchestration.

Owned by Task 05 — see tasks/05-*.md.
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import pypdfium2 as pdfium
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

from app.adapters.ocr import get_ocr_adapter
from app.adapters.ocr.base import OcrAdapter, OcrRegion, OcrResult
from app.config import settings
from app.models import Document, ExtractionResult, ExtractionStatus, ProcessingState
from app.repositories.documents_repo import get_by_id as get_document, update_processing_state
from app.repositories.extraction_repo import create as create_extraction
from app.services.upload_service import safe_upload_path


MAX_LONG_EDGE = 2000


class OcrProcessingError(Exception):
    """Raised when OCR processing fails unrecoverably."""
    def __init__(self, message: str, warnings: List[str]):
        self.warnings = warnings
        super().__init__(message)


def _preprocess_image(image: Image.Image) -> Image.Image:
    """Apply conservative preprocessing to an image.

    Steps (in order):
    1. EXIF orientation correction
    2. Grayscale conversion
    3. Light denoise (mild median filter)
    4. Contrast normalization (mild)

    The original image is not modified; a copy is returned.
    """
    # Work on a copy
    img = image.copy()

    # 1. EXIF orientation correction
    img = ImageOps.exif_transpose(img)

    # 2. Grayscale
    if img.mode != "L":
        img = img.convert("L")

    # 3. Light denoise - mild median filter (3x3)
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # 4. Mild contrast enhancement (CLAHE-like via PIL)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.2)

    return img


def _resize_to_max_long_edge(image: Image.Image, max_long_edge: int = MAX_LONG_EDGE) -> Image.Image:
    """Resize image so its longest edge does not exceed max_long_edge."""
    width, height = image.size
    long_edge = max(width, height)

    if long_edge <= max_long_edge:
        return image

    scale = max_long_edge / long_edge
    new_width = int(width * scale)
    new_height = int(height * scale)
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def _render_pdf_pages(file_path: Path) -> List[Image.Image]:
    """Render PDF pages to PIL images, capped at MAX_PDF_PAGES and MAX_LONG_EDGE."""
    pdf = pdfium.PdfDocument(str(file_path))
    try:
        page_count = len(pdf)
        max_pages = min(page_count, settings.MAX_PDF_PAGES)
        images = []
        for page_idx in range(max_pages):
            page = pdf[page_idx]
            # Render at scale to fit within MAX_LONG_EDGE
            # First render at 1.0 to get dimensions, then scale if needed
            bitmap = page.render(scale=1.0)
            pil_image = bitmap.to_pil()
            pil_image = _resize_to_max_long_edge(pil_image)
            images.append(pil_image)
        return images
    finally:
        pdf.close()


def _load_image_file(file_path: Path) -> Image.Image:
    """Load an image file (JPEG/PNG) and return PIL Image."""
    with Image.open(file_path) as img:
        img.load()  # Force load into memory
        return img.copy()


def _run_adapter_with_timeout(
    adapter: OcrAdapter,
    image: Image.Image,
    timeout_seconds: int,
) -> OcrResult:
    """Run adapter.run() with a per-page timeout.

    Uses ThreadPoolExecutor for Windows-compatible timeout.
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(adapter.run, image)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError:
            raise TimeoutError(f"OCR timed out after {timeout_seconds} seconds")


def _sort_regions_reading_order(regions: List[OcrRegion]) -> List[OcrRegion]:
    """Sort regions top-to-bottom, then left-to-right.

    Uses bbox (x1, y1, x2, y2) — sorts by y1 (top), then x1 (left).
    """
    return sorted(regions, key=lambda r: (r.bbox[1], r.bbox[0]))


def _assemble_multipage_result(page_results: List[Tuple[int, OcrResult]]) -> OcrResult:
    """Combine per-page OcrResults into a single result with page-tagged regions.

    Args:
        page_results: List of (page_number, OcrResult) tuples, 1-indexed pages.

    Returns:
        Combined OcrResult with all regions, joined text, and aggregated warnings.
    """
    all_regions: List[OcrRegion] = []
    all_warnings: List[str] = []
    engine_name = ""
    engine_version = ""

    for page_num, page_result in page_results:
        # Tag regions with page number
        for region in page_result.regions:
            # Create new region with updated page
            all_regions.append(OcrRegion(
                text=region.text,
                confidence=region.confidence,
                bbox=region.bbox,
                page=page_num,
            ))

        all_warnings.extend(page_result.warnings)
        if not engine_name:
            engine_name = page_result.engine_name
        if not engine_version:
            engine_version = page_result.engine_version

    # Sort all regions in reading order
    all_regions = _sort_regions_reading_order(all_regions)

    # Join text in reading order
    full_text = "\n".join(r.text for r in all_regions)

    # Compute mean confidence
    mean_confidence = None
    if all_regions:
        mean_confidence = sum(r.confidence for r in all_regions) / len(all_regions)

    return OcrResult(
        text=full_text,
        regions=all_regions,
        mean_confidence=mean_confidence,
        engine_name=engine_name,
        engine_version=engine_version,
        warnings=all_warnings,
    )


def process_document(document_id: str, session) -> ExtractionResult:
    """Process a document through the OCR pipeline.

    Implements docs/document-processing.md steps 1-8:
    1. Load document row; resolve file via safe_upload_path()
    2. Set processing_state = OCR_IN_PROGRESS
    3. PDF -> render pages (capped resolution, MAX_PDF_PAGES). Image -> single page.
    4. Preprocess each page in memory.
    5. Run configured adapter per page, with per-page timeout.
    6. Assemble combined OcrResult with page-tagged regions.
    7. Write extraction_results with raw_ocr_json, warnings_json, engine_name, engine_version, status.
    8. Set processing_state to OCR_DONE or OCR_FAILED.

    Args:
        document_id: UUID of the document to process.
        session: SQLAlchemy session.

    Returns:
        The created ExtractionResult.

    Raises:
        OcrProcessingError: If the document is not found or file is missing.
    """
    # Step 1: Load document
    document = get_document(session, document_id)
    if document is None:
        raise OcrProcessingError(
            f"Document {document_id} not found",
            warnings=["document_not_found"],
        )

    # Step 2: Set processing state to OCR_IN_PROGRESS
    update_processing_state(session, document_id, ProcessingState.OCR_IN_PROGRESS)
    session.flush()

    # Resolve file path
    try:
        file_path = safe_upload_path(document.storage_key)
    except ValueError as e:
        # Path traversal or containment failure
        update_processing_state(session, document_id, ProcessingState.OCR_FAILED)
        session.flush()
        raise OcrProcessingError(
            f"Invalid storage path: {e}",
            warnings=["invalid_storage_path"],
        )

    if not file_path.exists():
        update_processing_state(session, document_id, ProcessingState.OCR_FAILED)
        session.flush()
        raise OcrProcessingError(
            f"File not found on disk: {file_path}",
            warnings=["file_missing_on_disk"],
        )

    # Get adapter
    adapter = get_ocr_adapter()
    timeout_seconds = settings.OCR_TIMEOUT_SECONDS

    page_results: List[Tuple[int, OcrResult]] = []
    all_failed = True

    try:
        # Step 3: Render pages
        if document.mime_type == "application/pdf":
            page_images = _render_pdf_pages(file_path)
        else:
            # Single image
            page_images = [_load_image_file(file_path)]

        # Step 4-5: Preprocess and run OCR per page
        for page_idx, page_image in enumerate(page_images):
            page_num = page_idx + 1

            try:
                # Preprocess
                preprocessed = _preprocess_image(page_image)

                # Run OCR with timeout
                page_result = _run_adapter_with_timeout(adapter, preprocessed, timeout_seconds)
                page_results.append((page_num, page_result))
                all_failed = False

            except TimeoutError as e:
                warning = f"page_{page_num}_timeout: {e}"
                page_results.append((page_num, OcrResult(
                    text="",
                    regions=[],
                    mean_confidence=None,
                    engine_name=adapter.__class__.__name__.replace("Adapter", "").lower() or "unknown",
                    engine_version="unknown",
                    warnings=[warning],
                )))
            except Exception as e:
                warning = f"page_{page_num}_error: {type(e).__name__}: {e}"
                page_results.append((page_num, OcrResult(
                    text="",
                    regions=[],
                    mean_confidence=None,
                    engine_name=adapter.__class__.__name__.replace("Adapter", "").lower() or "unknown",
                    engine_version="unknown",
                    warnings=[warning],
                )))

        # Step 6: Assemble combined result
        combined_result = _assemble_multipage_result(page_results)

        # Determine overall status
        has_text = bool(combined_result.text.strip())
        overall_status = ExtractionStatus.FAILED if all_failed else ExtractionStatus.SUCCEEDED

        # Add no_text_detected warning if no text at all but not a failure
        if overall_status == ExtractionStatus.SUCCEEDED and not has_text:
            combined_result.warnings.append("no_text_detected")

        # Step 7: Write extraction_results
        raw_ocr_json = json.dumps({
            "text": combined_result.text,
            "regions": [
                {
                    "text": r.text,
                    "confidence": r.confidence,
                    "bbox": r.bbox,
                    "page": r.page,
                }
                for r in combined_result.regions
            ],
            "mean_confidence": combined_result.mean_confidence,
            "engine_name": combined_result.engine_name,
            "engine_version": combined_result.engine_version,
            "warnings": combined_result.warnings,
        })

        extraction = ExtractionResult(
            id=os.urandom(16).hex(),
            document_id=document_id,
            engine_name=combined_result.engine_name,
            engine_version=combined_result.engine_version,
            raw_ocr_json=raw_ocr_json,
            extracted_fields_json="{}",  # Task 06 will populate this
            warnings_json=json.dumps(combined_result.warnings),
            status=overall_status,
            created_at=datetime.now(timezone.utc),
        )

        create_extraction(session, extraction)
        session.flush()

        # Step 8: Update processing state
        final_state = ProcessingState.OCR_DONE if overall_status == ExtractionStatus.SUCCEEDED else ProcessingState.OCR_FAILED
        update_processing_state(session, document_id, final_state)
        session.flush()

        return extraction

    except OcrProcessingError:
        # Already handled, re-raise
        raise
    except Exception as e:
        # Unexpected error
        update_processing_state(session, document_id, ProcessingState.OCR_FAILED)
        session.flush()
        raise OcrProcessingError(
            f"Unexpected error during OCR: {type(e).__name__}: {e}",
            warnings=[f"unexpected_error: {type(e).__name__}: {e}"],
        )