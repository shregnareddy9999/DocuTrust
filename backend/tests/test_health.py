"""Tests owned by Task 01 — see tasks/01-foundation.md."""

import re
from fastapi.testclient import TestClient


def test_health_endpoint_returns_200(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_endpoint_has_all_four_keys(client: TestClient):
    response = client.get("/api/v1/health")
    data = response.json()
    assert set(data.keys()) == {"status", "database", "ocr_adapter", "blockchain"}


def test_health_status_is_ok(client: TestClient):
    response = client.get("/api/v1/health")
    data = response.json()
    assert data["status"] == "ok"


def test_health_database_not_configured(client: TestClient):
    response = client.get("/api/v1/health")
    data = response.json()
    assert data["database"] == "ok"


def test_health_ocr_adapter_shows_engine_name(client: TestClient):
    response = client.get("/api/v1/health")
    data = response.json()
    # OCR adapter should show the engine name from settings
    assert data["ocr_adapter"] in ("paddleocr", "fake")


def test_health_blockchain_enabled_or_disabled(client: TestClient):
    response = client.get("/api/v1/health")
    data = response.json()
    assert data["blockchain"] in ("enabled", "disabled")


def test_health_no_secrets_or_paths_leaked(client: TestClient):
    response = client.get("/api/v1/health")
    data = response.json()
    response_text = response.text

    # Check no filesystem paths
    assert "/data/" not in response_text
    assert "/app/" not in response_text
    assert "sqlite://" not in response_text
    assert ".db" not in response_text

    # Check no connection strings
    assert "postgresql://" not in response_text
    assert "mysql://" not in response_text

    # Check no secrets (CHAIN_EVENT_SALT, etc.)
    assert "CHAIN_EVENT_SALT" not in response_text
    assert "BLOCKCHAIN_RPC_URL" not in response_text
    assert "DATABASE_URL" not in response_text