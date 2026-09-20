"""Tests for OCR pipeline — Task 05.

Default suite uses fake adapter only. No paddleocr import occurs.
Integration test marked @pytest.mark.integration requires real PaddleOCR.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import Image

from app.adapters.ocr.base import OcrRegion, OcrResult
from app.adapters.ocr.fake_adapter import create_fake_adapter, FakeOcrAdapter
from app.models import Document, DocumentCategory, ExtractionResult, ExtractionStatus, ProcessingState
from app.repositories.documents_repo import create as create_document
from app.services.ocr_service import process_document
import app.config as config_module
import app.adapters.ocr as ocr_adapters_module
import app.services.ocr_service as ocr_service_module


@pytest.fixture(autouse=True)
def patch_ocr_settings(test_settings, monkeypatch):
    """Monkeypatch config.settings for OCR adapter factory and service."""
    monkeypatch.setattr(config_module, "settings", test_settings)
    monkeypatch.setattr(ocr_service_module, "settings", test_settings)


def _create_test_document(session, mime_type: str = "image/png") -> Document:
    """Create a minimal test document with a dummy file on disk."""
    from app.services.upload_service import generate_storage_key, safe_upload_path

    storage_key = generate_storage_key(mime_type)
    file_path = safe_upload_path(storage_key)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create a minimal valid image file
    img = Image.new("RGB", (100, 100), color="white")
    if mime_type == "application/pdf":
        # For PDF tests, copy a real PDF from fixtures
        fixture_pdf = Path("backend/app/fixtures/sample_documents/academic_certificate_match.pdf")
        if fixture_pdf.exists():
            import shutil
            shutil.copy2(fixture_pdf, file_path)
        else:
            # Fallback: create a minimal valid PDF
            file_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n192\n%%EOF\n")
    else:
        img.save(file_path)

    doc = Document(
        id="test-doc-" + hashlib.md5(storage_key.encode()).hexdigest()[:16],
        category=DocumentCategory.ACADEMIC_CERTIFICATE,
        original_filename="test.png",
        storage_key=storage_key,
        sha256=hashlib.sha256(file_path.read_bytes()).hexdigest(),
        mime_type=mime_type,
        byte_size=file_path.stat().st_size,
        page_count=1,
        processing_state=ProcessingState.UPLOADED,
        uploaded_at=datetime.now(timezone.utc),
    )
    return create_document(session, doc)


def _get_mean_confidence(extraction: ExtractionResult) -> float | None:
    """Extract mean_confidence from raw_ocr_json."""
    data = json.loads(extraction.raw_ocr_json)
    return data.get("mean_confidence")


class TestOcrPipeline:
    """OCR pipeline tests using fake adapter."""

    def test_clean_fake_response_succeeds(self, db_session, test_settings):
        """Clean fake response -> SUCCEEDED, confidence populated, OCR_DONE, engine recorded."""
        test_settings.OCR_ENGINE = "fake"

        document = _create_test_document(db_session)
        db_session.commit()

        extraction = process_document(document.id, db_session)
        db_session.commit()

        assert extraction.status == ExtractionStatus.SUCCEEDED
        assert extraction.engine_name == "fake"
        assert extraction.engine_version == "0.0.0-test"
        mean_conf = _get_mean_confidence(extraction)
        assert mean_conf is not None
        assert mean_conf > 0.9
        assert extraction.raw_ocr_json is not None
        assert extraction.warnings_json == "[]"

        db_session.refresh(document)
        assert document.processing_state == ProcessingState.OCR_DONE

    def test_low_confidence_fake_passes_through_unaltered(self, db_session, test_settings):
        """Low-confidence fake -> SUCCEEDED; exact low values pass through unaltered."""
        test_settings.OCR_ENGINE = "fake"

        document = _create_test_document(db_session)
        db_session.commit()

        # Monkeypatch both factory and service to use low_confidence adapter
        def low_conf_get():
            return create_fake_adapter(mode="low_confidence")

        original_factory_get = ocr_adapters_module.get_ocr_adapter
        original_service_get = ocr_service_module.get_ocr_adapter
        ocr_adapters_module.get_ocr_adapter = low_conf_get
        ocr_service_module.get_ocr_adapter = low_conf_get
        try:
            extraction = process_document(document.id, db_session)
            db_session.commit()
        finally:
            ocr_adapters_module.get_ocr_adapter = original_factory_get
            ocr_service_module.get_ocr_adapter = original_service_get

        assert extraction.status == ExtractionStatus.SUCCEEDED
        mean_conf = _get_mean_confidence(extraction)
        assert mean_conf is not None
        assert abs(mean_conf - 0.50) < 0.01

        warnings = json.loads(extraction.warnings_json)
        assert "no_text_detected" not in warnings

    def test_empty_fake_succeeds_with_no_text_detected(self, db_session, test_settings):
        """Empty fake -> SUCCEEDED with no_text_detected warning, NOT FAILED."""
        test_settings.OCR_ENGINE = "fake"

        document = _create_test_document(db_session)
        db_session.commit()

        def empty_get():
            return create_fake_adapter(mode="empty")

        original_factory_get = ocr_adapters_module.get_ocr_adapter
        original_service_get = ocr_service_module.get_ocr_adapter
        ocr_adapters_module.get_ocr_adapter = empty_get
        ocr_service_module.get_ocr_adapter = empty_get
        try:
            extraction = process_document(document.id, db_session)
            db_session.commit()
        finally:
            ocr_adapters_module.get_ocr_adapter = original_factory_get
            ocr_service_module.get_ocr_adapter = original_service_get

        assert extraction.status == ExtractionStatus.SUCCEEDED
        warnings = json.loads(extraction.warnings_json)
        assert "no_text_detected" in warnings

        db_session.refresh(document)
        assert document.processing_state == ProcessingState.OCR_DONE

    def test_raising_fake_failed_ocr_failed(self, db_session, test_settings):
        """Raising fake -> FAILED, OCR_FAILED, exception type recorded, no silent empty success."""
        test_settings.OCR_ENGINE = "fake"

        document = _create_test_document(db_session)
        db_session.commit()

        def raises_get():
            return create_fake_adapter(mode="raises")

        original_factory_get = ocr_adapters_module.get_ocr_adapter
        original_service_get = ocr_service_module.get_ocr_adapter
        ocr_adapters_module.get_ocr_adapter = raises_get
        ocr_service_module.get_ocr_adapter = raises_get
        try:
            extraction = process_document(document.id, db_session)
            db_session.commit()
        finally:
            ocr_adapters_module.get_ocr_adapter = original_factory_get
            ocr_service_module.get_ocr_adapter = original_service_get

        assert extraction.status == ExtractionStatus.FAILED
        warnings = json.loads(extraction.warnings_json)
        assert any("RuntimeError" in w or "Simulated OCR engine failure" in w for w in warnings)

        db_session.refresh(document)
        assert document.processing_state == ProcessingState.OCR_FAILED

    def test_timeout_fake_failed_with_timeout_warning(self, db_session, test_settings):
        """Timeout fake -> FAILED with timeout warning."""
        test_settings.OCR_ENGINE = "fake"
        # Reduce timeout for test
        test_settings.OCR_TIMEOUT_SECONDS = 1

        document = _create_test_document(db_session)
        db_session.commit()

        def timeout_get():
            return create_fake_adapter(mode="timeout")

        original_factory_get = ocr_adapters_module.get_ocr_adapter
        original_service_get = ocr_service_module.get_ocr_adapter
        ocr_adapters_module.get_ocr_adapter = timeout_get
        ocr_service_module.get_ocr_adapter = timeout_get
        try:
            extraction = process_document(document.id, db_session)
            db_session.commit()
        finally:
            ocr_adapters_module.get_ocr_adapter = original_factory_get
            ocr_service_module.get_ocr_adapter = original_service_get

        assert extraction.status == ExtractionStatus.FAILED
        warnings = json.loads(extraction.warnings_json)
        assert any("timeout" in w.lower() for w in warnings)

    def test_multipage_pdf_page2_raises_pages1_3_succeed(self, db_session, test_settings):
        """Multi-page PDF where page 2 raises -> other pages text present, page-2 warning, overall SUCCEEDED."""
        test_settings.OCR_ENGINE = "fake"

        document = _create_test_document(db_session, mime_type="application/pdf")
        db_session.commit()

        # Custom adapter that raises on page 2, succeeds on others
        from app.adapters.ocr.fake_adapter import create_fake_adapter
        from app.adapters.ocr.base import OcrResult, OcrRegion
        from PIL import Image

        class MultipageFakeAdapter:
            def __init__(self):
                self.page_count = 0
                self.clean_adapter = create_fake_adapter(mode="clean")
                self.raises_adapter = create_fake_adapter(mode="raises")

            def run(self, image: Image.Image) -> OcrResult:
                self.page_count += 1
                if self.page_count == 2:
                    try:
                        return self.raises_adapter.run(image)
                    except Exception as e:
                        raise
                return self.clean_adapter.run(image)

        multipage_adapter = MultipageFakeAdapter()

        def multipage_get():
            return multipage_adapter

        # Monkeypatch PDF rendering to return 3 pages for controlled testing
        import app.services.ocr_service as ocr_service_module
        original_render = ocr_service_module._render_pdf_pages

        def mock_render_pdf_pages(file_path):
            img = Image.new("RGB", (100, 100), color="white")
            return [img.copy(), img.copy(), img.copy()]  # 3 pages

        ocr_service_module._render_pdf_pages = mock_render_pdf_pages

        original_factory_get = ocr_adapters_module.get_ocr_adapter
        original_service_get = ocr_service_module.get_ocr_adapter
        ocr_adapters_module.get_ocr_adapter = multipage_get
        ocr_service_module.get_ocr_adapter = multipage_get
        try:
            extraction = process_document(document.id, db_session)
            db_session.commit()
        finally:
            ocr_adapters_module.get_ocr_adapter = original_factory_get
            ocr_service_module.get_ocr_adapter = original_service_get
            ocr_service_module._render_pdf_pages = original_render

        assert extraction.status == ExtractionStatus.SUCCEEDED
        warnings = json.loads(extraction.warnings_json)
        # Check that page 2 has an error warning (format: "page_2_error: RuntimeError: ...")
        assert any("page_2" in w and ("error" in w or "RuntimeError" in w) for w in warnings), f"Warnings: {warnings}"

        raw_ocr = json.loads(extraction.raw_ocr_json)
        pages = set(r["page"] for r in raw_ocr["regions"])
        # Pages 1 and 3 should have regions (page 2 failed)
        assert 1 in pages, f"Pages with regions: {pages}"
        assert 3 in pages, f"Pages with regions: {pages}"

        db_session.refresh(document)
        assert document.processing_state == ProcessingState.OCR_DONE

    def test_multipage_pdf_all_pages_fail_failed(self, db_session, test_settings):
        """Multi-page PDF where every page raises -> FAILED."""
        test_settings.OCR_ENGINE = "fake"

        document = _create_test_document(db_session, mime_type="application/pdf")
        db_session.commit()

        def all_fail_get():
            return create_fake_adapter(mode="raises")

        original_factory_get = ocr_adapters_module.get_ocr_adapter
        original_service_get = ocr_service_module.get_ocr_adapter
        ocr_adapters_module.get_ocr_adapter = all_fail_get
        ocr_service_module.get_ocr_adapter = all_fail_get
        try:
            extraction = process_document(document.id, db_session)
            db_session.commit()
        finally:
            ocr_adapters_module.get_ocr_adapter = original_factory_get
            ocr_service_module.get_ocr_adapter = original_service_get

        assert extraction.status == ExtractionStatus.FAILED
        db_session.refresh(document)
        assert document.processing_state == ProcessingState.OCR_FAILED

    def test_original_file_byte_identical(self, db_session, test_settings):
        """Original file on disk is byte-identical before and after processing."""
        test_settings.OCR_ENGINE = "fake"

        document = _create_test_document(db_session)
        from app.services.upload_service import safe_upload_path
        original_bytes = safe_upload_path(document.storage_key).read_bytes()
        db_session.commit()

        process_document(document.id, db_session)
        db_session.commit()

        after_bytes = safe_upload_path(document.storage_key).read_bytes()
        assert original_bytes == after_bytes

    def test_no_paddleocr_import_in_default_suite(self):
        """Assert paddleocr is not imported during default test run."""
        assert "paddleocr" not in sys.modules, "paddleocr must not be imported in default suite"


class TestOcrPipelineIntegration:
    """Integration tests requiring real PaddleOCR — excluded from default suite."""

    @pytest.mark.integration
    def test_real_paddleocr_academic_certificate_match(self, db_session, test_settings):
        """Real PaddleOCR on academic_certificate_match.png extracts text with confidence > 0.5."""
        test_settings.OCR_ENGINE = "paddleocr"

        sample_path = Path(__file__).parent.parent / "app" / "fixtures" / "sample_documents" / "academic_certificate_match.png"
        if not sample_path.exists():
            pytest.skip("Sample document not found")

        from app.services.upload_service import generate_storage_key, safe_upload_path
        import shutil

        storage_key = generate_storage_key("image/png")
        dest_path = safe_upload_path(storage_key)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sample_path, dest_path)

        document = Document(
            id="test-integration-" + hashlib.md5(storage_key.encode()).hexdigest()[:16],
            category=DocumentCategory.ACADEMIC_CERTIFICATE,
            original_filename="academic_certificate_match.png",
            storage_key=storage_key,
            sha256=hashlib.sha256(dest_path.read_bytes()).hexdigest(),
            mime_type="image/png",
            byte_size=dest_path.stat().st_size,
            page_count=1,
            processing_state=ProcessingState.UPLOADED,
            uploaded_at=datetime.now(timezone.utc),
        )
        create_document(db_session, document)
        db_session.commit()

        extraction = process_document(document.id, db_session)
        db_session.commit()

        assert extraction.status == ExtractionStatus.SUCCEEDED
        mean_conf = _get_mean_confidence(extraction)
        assert mean_conf is not None
        assert mean_conf > 0.5
        assert extraction.engine_name == "paddleocr"
        assert extraction.engine_version != "0.0.0-test"
        assert extraction.engine_version != ""

        db_session.refresh(document)
        assert document.processing_state == ProcessingState.OCR_DONE


class TestOcrAdapterFactory:
    """Tests for OCR adapter factory fail-fast behavior."""

    def test_unknown_ocr_engine_fails_at_startup(self, test_settings):
        """OCR_ENGINE=nonsense -> startup fails (ValueError from factory)."""
        test_settings.OCR_ENGINE = "nonsense"

        from app.adapters.ocr import get_ocr_adapter
        with pytest.raises(ValueError, match="Unknown OCR_ENGINE"):
            get_ocr_adapter()


class TestFakeAdapterModes:
    """Unit tests for FakeOcrAdapter modes."""

    def test_clean_mode_structure(self):
        adapter = create_fake_adapter(mode="clean")
        img = Image.new("RGB", (100, 100), color="white")
        result = adapter.run(img)

        assert isinstance(result, OcrResult)
        assert result.engine_name == "fake"
        assert result.engine_version == "0.0.0-test"
        assert result.mean_confidence is not None
        assert result.mean_confidence > 0.9
        assert len(result.regions) > 0
        for region in result.regions:
            assert isinstance(region, OcrRegion)
            assert 0.0 <= region.confidence <= 1.0
            assert len(region.bbox) == 4
            assert region.page == 1

    def test_low_confidence_mode_values(self):
        adapter = create_fake_adapter(mode="low_confidence")
        img = Image.new("RGB", (100, 100), color="white")
        result = adapter.run(img)

        assert result.mean_confidence is not None
        assert result.mean_confidence < 0.70

    def test_empty_mode(self):
        adapter = create_fake_adapter(mode="empty")
        img = Image.new("RGB", (100, 100), color="white")
        result = adapter.run(img)

        assert result.text == ""
        assert result.regions == []
        assert result.mean_confidence is None
        assert "no_text_detected" in result.warnings

    def test_raises_mode(self):
        adapter = create_fake_adapter(mode="raises")
        img = Image.new("RGB", (100, 100), color="white")

        with pytest.raises(RuntimeError, match="Simulated OCR engine failure"):
            adapter.run(img)

    def test_custom_text_and_confidence(self):
        adapter = create_fake_adapter(mode="clean", custom_text="Custom text", custom_confidence=0.85)
        img = Image.new("RGB", (100, 100), color="white")
        result = adapter.run(img)

        assert "Custom text" in result.text
        assert result.mean_confidence == 0.85