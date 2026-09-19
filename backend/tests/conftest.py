
"""Shared fixtures: temporary database and fake adapters."""

import os
import tempfile
from pathlib import Path

# Set test-only environment values before importing app configuration.
os.environ.setdefault("BLOCKCHAIN_ENABLED", "false")
os.environ.setdefault("BLOCKCHAIN_CONTRACT_ADDRESS", "")
os.environ.setdefault("CHAIN_EVENT_SALT", "test_salt_" + "0" * 56)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db import Base


def make_test_engine(database_url: str) -> Engine:
    """Create a SQLite test engine with foreign-key enforcement enabled."""
    test_engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(test_engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return test_engine


@pytest.fixture(scope="function")
def temp_db_path():
    """Create a temporary SQLite database file for one test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def temp_upload_dir():
    """Create a temporary upload directory for one test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="function")
def test_settings(temp_db_path: str, temp_upload_dir: Path) -> Settings:
    """Create settings with temporary test paths."""
    return Settings(
        APP_ENV="test",
        DATABASE_URL=f"sqlite:///{temp_db_path}",
        UPLOAD_DIR=str(temp_upload_dir),
        MAX_UPLOAD_MB=10,
        MAX_PDF_PAGES=5,
        ALLOWED_MIME_TYPES=[
            "image/jpeg",
            "image/png",
            "application/pdf",
        ],
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
        CHAIN_EVENT_SALT="test_salt_" + "0" * 56,
        RETENTION_DAYS=7,
        LOG_LEVEL="DEBUG",
    )


@pytest.fixture(scope="function")
def db_session(temp_db_path: str):
    """Provide a SQLAlchemy session connected to an isolated test DB."""
    test_engine = make_test_engine(f"sqlite:///{temp_db_path}")

    Base.metadata.create_all(bind=test_engine)

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        test_engine.dispose()


@pytest.fixture(scope="function")
def client(test_settings: Settings, monkeypatch: pytest.MonkeyPatch):
    """Create a TestClient using the temporary database."""
    from app import db
    from app.api import health
    from app.main import app
    import app.main as main_module
    import app.config as config_module
    import app.services.upload_service as upload_service
    from app.db import Base

    test_engine = make_test_engine(test_settings.DATABASE_URL)

    # Create all tables in the test engine
    Base.metadata.create_all(bind=test_engine)

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    # Ensure all database access uses the same temporary test engine.
    monkeypatch.setattr(db, "engine", test_engine)
    monkeypatch.setattr(db, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(main_module, "engine", test_engine)
    monkeypatch.setattr(health, "engine", test_engine)
    # Replace global settings object entirely so upload_service sees test settings
    # (upload_service imports settings at module level, so we must replace the reference)
    monkeypatch.setattr(config_module, "settings", test_settings)
    monkeypatch.setattr(upload_service, "settings", test_settings)

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        test_engine.dispose()


@pytest.fixture(scope="session")
def fake_ocr_adapter():
    """Placeholder for the fake OCR adapter implemented in Task 05."""
    return None


@pytest.fixture(scope="session")
def fake_blockchain_adapter():
    """Placeholder for the fake blockchain adapter implemented in Task 09."""
    return None