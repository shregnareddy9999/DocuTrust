"""Authenticated account operations backed by Supabase Auth."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Header, HTTPException, status

from app.config import settings

router = APIRouter()


def _http_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": {}}},
    )


def _require_bearer_token(authorization: str | None) -> str:
    if not authorization:
        _http_error(401, "AUTH_REQUIRED", "Sign in before deleting the account.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        _http_error(401, "AUTH_REQUIRED", "Sign in before deleting the account.")

    return token.strip()


def _require_supabase_admin_config() -> tuple[str, str]:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        _http_error(
            503,
            "ACCOUNT_DELETION_UNAVAILABLE",
            "Account deletion is not configured on the backend.",
        )

    return settings.SUPABASE_URL.rstrip("/"), settings.SUPABASE_SERVICE_ROLE_KEY


def _admin_headers(service_role_key: str) -> dict[str, str]:
    return {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }


@router.delete(
    "/account",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def delete_current_account(authorization: str | None = Header(default=None)) -> None:
    """Delete the signed-in Supabase Auth user using server-side admin credentials."""

    user_token = _require_bearer_token(authorization)
    supabase_url, service_role_key = _require_supabase_admin_config()

    try:
        with httpx.Client(timeout=20) as client:
            user_response = client.get(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "apikey": service_role_key,
                    "Authorization": f"Bearer {user_token}",
                },
            )
            if user_response.status_code in {401, 403}:
                _http_error(401, "AUTH_REQUIRED", "Sign in before deleting the account.")
            user_response.raise_for_status()
            user_payload = user_response.json()
            user_id = user_payload.get("id")
            if not isinstance(user_id, str) or not user_id:
                _http_error(401, "AUTH_REQUIRED", "Sign in before deleting the account.")

            # Best-effort cleanup for optional profile rows; auth deletion remains authoritative.
            client.delete(
                f"{supabase_url}/rest/v1/profiles",
                params={"id": f"eq.{user_id}"},
                headers={
                    **_admin_headers(service_role_key),
                    "Prefer": "return=minimal",
                },
            )

            delete_response = client.delete(
                f"{supabase_url}/auth/v1/admin/users/{user_id}",
                headers=_admin_headers(service_role_key),
            )
            if delete_response.status_code in {404, 410}:
                return
            delete_response.raise_for_status()
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            _http_error(
                503,
                "ACCOUNT_DELETION_UNAVAILABLE",
                "Account deletion is not authorized on the backend.",
            )
        _http_error(
            503,
            "ACCOUNT_DELETION_UNAVAILABLE",
            "Supabase could not delete the account. Try again later.",
        )
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "ACCOUNT_DELETION_UNAVAILABLE",
                    "message": "Could not reach Supabase account deletion service.",
                    "details": {},
                }
            },
        ) from exc
