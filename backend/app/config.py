"""Settings loading and fail-fast validation.

Owned by Task 01 — see tasks/01-foundation.md.
"""

from typing import Literal
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid",
    )

    APP_ENV: Literal["development", "test", "demo"] = "development"
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    DATABASE_URL: str = "sqlite:///./data/app.db"

    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_MB: int = 10
    MAX_PDF_PAGES: int = 5
    ALLOWED_MIME_TYPES: list[str] = Field(default_factory=lambda: ["image/jpeg", "image/png", "application/pdf"])

    @field_validator("ALLOWED_MIME_TYPES", mode="before")
    @classmethod
    def parse_allowed_mime_types(cls, v):
        if isinstance(v, str):
            return [mime.strip() for mime in v.split(",") if mime.strip()]
        return v

    OCR_ENGINE: Literal["paddleocr"] = "paddleocr"
    OCR_LANGUAGE: str = "en"
    OCR_TIMEOUT_SECONDS: int = 30
    LOW_CONFIDENCE_THRESHOLD: float = 0.70

    REGISTRY_MODE: Literal["synthetic_demo"] = "synthetic_demo"

    BLOCKCHAIN_ENABLED: bool = True
    BLOCKCHAIN_RPC_URL: str = "http://127.0.0.1:8545"
    BLOCKCHAIN_CHAIN_ID: int = 31337
    BLOCKCHAIN_CONTRACT_ADDRESS: str = ""
    BLOCKCHAIN_TX_TIMEOUT_SECONDS: int = 30
    BLOCKCHAIN_MAX_RETRIES: int = 2
    CHAIN_EVENT_SALT: str = ""

    RETENTION_DAYS: int = 7
    LOG_LEVEL: str = "INFO"

    @field_validator("MAX_UPLOAD_MB")
    @classmethod
    def validate_max_upload_mb(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("MAX_UPLOAD_MB must be > 0")
        return v

    @field_validator("MAX_PDF_PAGES")
    @classmethod
    def validate_max_pdf_pages(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("MAX_PDF_PAGES must be > 0")
        return v

    @field_validator("ALLOWED_MIME_TYPES")
    @classmethod
    def validate_allowed_mime_types(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("ALLOWED_MIME_TYPES must be non-empty")
        return v

    @field_validator("LOW_CONFIDENCE_THRESHOLD")
    @classmethod
    def validate_low_confidence_threshold(cls, v: float) -> float:
        if not (0 < v < 1):
            raise ValueError("LOW_CONFIDENCE_THRESHOLD must be in (0, 1)")
        return v

    @field_validator("OCR_TIMEOUT_SECONDS")
    @classmethod
    def validate_ocr_timeout(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("OCR_TIMEOUT_SECONDS must be > 0")
        return v

    @field_validator("BLOCKCHAIN_CHAIN_ID")
    @classmethod
    def validate_chain_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("BLOCKCHAIN_CHAIN_ID must be > 0")
        return v

    @field_validator("BLOCKCHAIN_TX_TIMEOUT_SECONDS")
    @classmethod
    def validate_tx_timeout(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("BLOCKCHAIN_TX_TIMEOUT_SECONDS must be > 0")
        return v

    @field_validator("BLOCKCHAIN_MAX_RETRIES")
    @classmethod
    def validate_max_retries(cls, v: int) -> int:
        if v < 0:
            raise ValueError("BLOCKCHAIN_MAX_RETRIES must be >= 0")
        return v

    @field_validator("RETENTION_DAYS")
    @classmethod
    def validate_retention_days(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("RETENTION_DAYS must be > 0")
        return v

    @model_validator(mode="after")
    def validate_blockchain_config(self) -> "Settings":
        if self.BLOCKCHAIN_ENABLED:
            if not self.BLOCKCHAIN_RPC_URL:
                raise ValueError("BLOCKCHAIN_RPC_URL must be set when BLOCKCHAIN_ENABLED=true")
            if not self.BLOCKCHAIN_CONTRACT_ADDRESS:
                raise ValueError("BLOCKCHAIN_CONTRACT_ADDRESS must be set when BLOCKCHAIN_ENABLED=true")
            if not self.CHAIN_EVENT_SALT:
                raise ValueError("CHAIN_EVENT_SALT must be set when BLOCKCHAIN_ENABLED=true")
        return self


settings = Settings()