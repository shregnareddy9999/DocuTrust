"""Shared fixtures: temp DB, fake adapters.

Owned by Task 01 — see tasks/01-foundation.md.
"""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


@pytest.fixture(scope="session")
def temp_db_path():
    """Create a temporary SQLite database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="session")
def temp_upload_dir():
    """Create a temporary upload directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="session")
def test_settings(temp_db_path: str, temp_upload_dir: Path) -> Settings:
    """Create a Settings instance with test overrides."""
    return Settings(
        APP_ENV="test",
        DATABASE_URL=f"sqlite:///{temp_db_path}",
        UPLOAD_DIR=str(temp_upload_dir),
        MAX_UPLOAD_MB=10,
        MAX_PDF_PAGES=5,
        ALLOWED_MIME_TYPES=["image/jpeg", "image/png", "application/pdf"],
        OCR_ENGINE="paddleocr",
        OCR_LANGUAGE="en",
        OCR_TIMEOUT_SECONDS=30,
        LOW_CONFIDENCE_THRESHOLD=0.70,
        REGISTRY_MODE="synthetic_demo",
        BLOCKCHAIN_ENABLED=False,
        BLOCKCHAIN_RPC_URL="http://127.0.0.1:8545",
        BLOCKCHAIN_CHAIN_ID=31337,
        BLOCKCHAIN_CONTRACT_ADDRESS="",
        BLOCKCHAIN_TX_TIMEOUT_SECONDS=30,
        BLOCKCHAIN_MAX_RETRIES=2,
        CHAIN_EVENT_SALT="test_salt_" + "0" * 56,  # 64 hex chars
        RETENTION_DAYS=7,
        LOG_LEVEL="DEBUG",
    )


@pytest.fixture(scope="function")
def client(test_settings: Settings) -> TestClient:
    """Create a TestClient with the test settings."""
    # Override the settings in the app
    # Note: In a real implementation, we'd use dependency injection
    # For now, the app uses the global settings at import time
    # Tests that need different settings should patch the config module
    return TestClient(app)


@pytest.fixture(scope="session")
def fake_ocr_adapter():
    """Placeholder for fake OCR adapter — implemented in Task 05."""
    # Import will be available when Task 05 implements it
    # from app.adapters.ocr.fake_adapter import FakeOcrAdapter
    # return FakeOcrAdapter()
    return None


@pytest.fixture(scope="session")
def fake_blockchain_adapter():
    """Placeholder for fake blockchain adapter — implemented in Task 09."""
    # from app.adapters.blockchain.fake_adapter import FakeBlockchainAdapter
    # return FakeBlockchainAdapter()
    return None