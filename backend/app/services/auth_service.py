"""Supabase bearer-token authentication helpers."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import settings


class AuthError(Exception):
    """Raised when a request lacks a usable authenticated Supabase user."""


class AuthUnavailableError(Exception):
    """Raised when backend auth configuration is unavailable."""


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None = None


def require_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AuthError

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthError

    return token.strip()


def require_authenticated_user(authorization: str | None) -> AuthenticatedUser:
    token = require_bearer_token(authorization)
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise AuthUnavailableError

    try:
        with httpx.Client(timeout=20) as client:
            response = client.get(
                f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {token}",
                },
            )
            if response.status_code in {401, 403}:
                raise AuthError
            response.raise_for_status()
            payload = response.json()
    except AuthError:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise AuthUnavailableError from exc

    user_id = payload.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise AuthError

    email = payload.get("email")
    return AuthenticatedUser(
        user_id=user_id,
        email=email if isinstance(email, str) else None,
    )
