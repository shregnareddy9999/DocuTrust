"""Tests owned by Task 01 — see tasks/01-foundation.md."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_valid_environment_loads_settings():
    """Valid environment -> Settings loads with correct types."""
    settings = Settings(
        APP_ENV="development",
        API_HOST="127.0.0.1",
        API_PORT=8000,
        DATABASE_URL="sqlite:///./data/app.db",
        UPLOAD_DIR="./data/uploads",
        MAX_UPLOAD_MB=10,
        MAX_PDF_PAGES=5,
        ALLOWED_MIME_TYPES=["image/jpeg", "image/png", "application/pdf"],
        OCR_ENGINE="paddleocr",
        OCR_LANGUAGE="en",
        OCR_TIMEOUT_SECONDS=30,
        LOW_CONFIDENCE_THRESHOLD=0.70,
        REGISTRY_MODE="synthetic_demo",
        BLOCKCHAIN_ENABLED=True,
        BLOCKCHAIN_RPC_URL="http://127.0.0.1:8545",
        BLOCKCHAIN_CHAIN_ID=31337,
        BLOCKCHAIN_CONTRACT_ADDRESS="0x1234567890123456789012345678901234567890",
        BLOCKCHAIN_TX_TIMEOUT_SECONDS=30,
        BLOCKCHAIN_MAX_RETRIES=2,
        CHAIN_EVENT_SALT="0" * 64,
        RETENTION_DAYS=7,
        LOG_LEVEL="INFO",
    )
    assert settings.MAX_UPLOAD_MB == 10
    assert settings.MAX_PDF_PAGES == 5
    assert isinstance(settings.ALLOWED_MIME_TYPES, list)
    assert settings.LOW_CONFIDENCE_THRESHOLD == 0.70
    assert settings.BLOCKCHAIN_ENABLED is True


def test_max_upload_mb_zero_raises():
    """MAX_UPLOAD_MB=0 -> raises with variable name."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(MAX_UPLOAD_MB=0)
    assert "MAX_UPLOAD_MB" in str(exc_info.value)
    assert "must be > 0" in str(exc_info.value)


def test_max_pdf_pages_zero_raises():
    """MAX_PDF_PAGES=0 -> raises with variable name."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(MAX_PDF_PAGES=0)
    assert "MAX_PDF_PAGES" in str(exc_info.value)
    assert "must be > 0" in str(exc_info.value)


def test_allowed_mime_types_empty_raises():
    """ALLOWED_MIME_TYPES empty -> raises with variable name."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(ALLOWED_MIME_TYPES=[])
    assert "ALLOWED_MIME_TYPES" in str(exc_info.value)
    assert "non-empty" in str(exc_info.value)


def test_low_confidence_threshold_above_one_raises():
    """LOW_CONFIDENCE_THRESHOLD=1.5 -> raises with variable name."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(LOW_CONFIDENCE_THRESHOLD=1.5)
    assert "LOW_CONFIDENCE_THRESHOLD" in str(exc_info.value)
    assert "in (0, 1)" in str(exc_info.value)


def test_low_confidence_threshold_zero_raises():
    """LOW_CONFIDENCE_THRESHOLD=0 -> raises with variable name."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(LOW_CONFIDENCE_THRESHOLD=0)
    assert "LOW_CONFIDENCE_THRESHOLD" in str(exc_info.value)
    assert "in (0, 1)" in str(exc_info.value)


def test_blockchain_enabled_with_empty_contract_address_raises():
    """BLOCKCHAIN_ENABLED=true with empty BLOCKCHAIN_CONTRACT_ADDRESS -> raises."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            BLOCKCHAIN_ENABLED=True,
            BLOCKCHAIN_RPC_URL="http://127.0.0.1:8545",
            BLOCKCHAIN_CONTRACT_ADDRESS="",
            CHAIN_EVENT_SALT="0" * 64,
        )
    assert "BLOCKCHAIN_CONTRACT_ADDRESS" in str(exc_info.value)
    assert "must be set when BLOCKCHAIN_ENABLED=true" in str(exc_info.value)


def test_blockchain_enabled_with_empty_chain_event_salt_raises():
    """BLOCKCHAIN_ENABLED=true with empty CHAIN_EVENT_SALT -> raises."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            BLOCKCHAIN_ENABLED=True,
            BLOCKCHAIN_RPC_URL="http://127.0.0.1:8545",
            BLOCKCHAIN_CONTRACT_ADDRESS="0x1234567890123456789012345678901234567890",
            CHAIN_EVENT_SALT="",
        )
    assert "CHAIN_EVENT_SALT" in str(exc_info.value)
    assert "must be set when BLOCKCHAIN_ENABLED=true" in str(exc_info.value)


def test_blockchain_enabled_with_empty_rpc_url_raises():
    """BLOCKCHAIN_ENABLED=true with empty BLOCKCHAIN_RPC_URL -> raises."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            BLOCKCHAIN_ENABLED=True,
            BLOCKCHAIN_RPC_URL="",
            BLOCKCHAIN_CONTRACT_ADDRESS="0x1234567890123456789012345678901234567890",
            CHAIN_EVENT_SALT="0" * 64,
        )
    assert "BLOCKCHAIN_RPC_URL" in str(exc_info.value)
    assert "must be set when BLOCKCHAIN_ENABLED=true" in str(exc_info.value)


def test_blockchain_disabled_with_empty_fields_loads():
    """BLOCKCHAIN_ENABLED=false with all three empty -> loads successfully."""
    settings = Settings(
        BLOCKCHAIN_ENABLED=False,
        BLOCKCHAIN_RPC_URL="",
        BLOCKCHAIN_CONTRACT_ADDRESS="",
        CHAIN_EVENT_SALT="",
    )
    assert settings.BLOCKCHAIN_ENABLED is False
    assert settings.BLOCKCHAIN_RPC_URL == ""
    assert settings.BLOCKCHAIN_CONTRACT_ADDRESS == ""
    assert settings.CHAIN_EVENT_SALT == ""


def test_env_example_keys_match_settings_fields():
    """Every key in .env.example has a corresponding field on Settings."""
    # Read .env.example and parse keys
    from pathlib import Path
    env_example_path = Path(__file__).parent.parent / ".env.example"
    with open(env_example_path) as f:
        content = f.read()

    # Extract keys (lines with = that aren't comments)
    env_keys = set()
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key = line.split("=")[0].strip()
            env_keys.add(key)

    # Get Settings model fields
    settings_fields = set(Settings.model_fields.keys())

    # Check all env keys have corresponding fields (case-sensitive match)
    # Note: .env.example uses same names as Settings fields
    missing_fields = env_keys - settings_fields
    assert not missing_fields, f"Settings missing fields for .env.example keys: {missing_fields}"

    # Check all Settings fields are documented in .env.example (optional but good practice)
    # Some fields may have defaults and not be in .env.example, that's OK