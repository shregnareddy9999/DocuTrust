"""Tests for Supabase-backed account deletion."""

from __future__ import annotations

import json

import httpx


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://docutrust-test.supabase.co")
            response = httpx.Response(
                self.status_code,
                request=request,
                content=json.dumps(self._payload).encode("utf-8"),
            )
            raise httpx.HTTPStatusError("Supabase error", request=request, response=response)


class _FakeSupabaseClient:
    calls: list[tuple[str, str]]

    def __init__(self, timeout: int):
        self.timeout = timeout
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def get(self, url: str, headers: dict):
        self.calls.append(("GET", url))
        return _FakeResponse(200, {"id": "user-demo-001"})

    def delete(self, url: str, **kwargs):
        self.calls.append(("DELETE", url))
        return _FakeResponse(204)


def test_delete_account_requires_auth(client):
    response = client.delete("/api/v1/account")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_delete_account_deletes_current_supabase_user(client, monkeypatch):
    fake = _FakeSupabaseClient(timeout=20)
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake)

    response = client.delete(
        "/api/v1/account",
        headers={"Authorization": "Bearer user-access-token"},
    )

    assert response.status_code == 204
    assert ("GET", "https://docutrust-test.supabase.co/auth/v1/user") in fake.calls
    assert (
        "DELETE",
        "https://docutrust-test.supabase.co/auth/v1/admin/users/user-demo-001",
    ) in fake.calls
