"""Aadhaar Link SMS and voice reminder workflow."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from html import escape
from typing import Any, Literal, Protocol

import httpx

from app.config import settings
from app.services.auth_service import AuthenticatedUser


VOICE_REMINDER_TEXT = "namashkar, ap please apka sms dekhiye. namaste, please check your sms."
MOBILE_PATTERN = re.compile(r"\b\d{10}\b")

SmsStatus = Literal["accepted", "failed"]
VoiceStatus = Literal["initiated", "failed", "not_attempted"]


class AadhaarMessagingError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class MessagingRecipient:
    citizen_ref: str
    demo_name: str
    mobile_number: str


@dataclass(frozen=True)
class ProviderResult:
    status: Literal["accepted", "failed"]
    provider_ref: str | None = None


class AadhaarMessagingProvider(Protocol):
    def send_sms(self, *, to_mobile: str, message: str) -> ProviderResult:
        ...

    def initiate_voice_reminder(self, *, to_mobile: str, script: str) -> ProviderResult:
        ...


class FakeAadhaarMessagingProvider:
    """Fake provider used for all automated tests and local demo wiring."""

    def __init__(
        self,
        *,
        sms_status: Literal["accepted", "failed"] = "accepted",
        voice_status: Literal["accepted", "failed"] = "accepted",
    ):
        self.sms_status = sms_status
        self.voice_status = voice_status
        self.sms_requests: list[tuple[str, str]] = []
        self.voice_requests: list[tuple[str, str]] = []

    def send_sms(self, *, to_mobile: str, message: str) -> ProviderResult:
        self.sms_requests.append((to_mobile, message))
        if self.sms_status == "failed":
            return ProviderResult(status="failed")
        return ProviderResult(status="accepted", provider_ref="fake-sms-request")

    def initiate_voice_reminder(self, *, to_mobile: str, script: str) -> ProviderResult:
        self.voice_requests.append((to_mobile, script))
        if self.voice_status == "failed":
            return ProviderResult(status="failed")
        return ProviderResult(status="accepted", provider_ref="fake-voice-request")


class TwilioAadhaarMessagingProvider:
    """Twilio REST provider for real SMS and voice request submission."""

    def __init__(self) -> None:
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_PHONE_NUMBER
        if not self.account_sid or not self.auth_token or not self.from_number:
            raise AadhaarMessagingError(
                "AADHAAR_MESSAGING_UNAVAILABLE",
                "Aadhaar messaging provider is not configured.",
                503,
            )

    @property
    def _base_url(self) -> str:
        return f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"

    def send_sms(self, *, to_mobile: str, message: str) -> ProviderResult:
        return self._post_twilio_resource(
            "Messages.json",
            {
                "From": self.from_number,
                "To": _to_e164(to_mobile),
                "Body": message,
            },
        )

    def initiate_voice_reminder(self, *, to_mobile: str, script: str) -> ProviderResult:
        return self._post_twilio_resource(
            "Calls.json",
            {
                "From": self.from_number,
                "To": _to_e164(to_mobile),
                "Twiml": _voice_twiml(script),
            },
        )

    def _post_twilio_resource(self, resource: str, data: dict[str, str]) -> ProviderResult:
        try:
            with httpx.Client(timeout=20, auth=(self.account_sid, self.auth_token)) as client:
                response = client.post(f"{self._base_url}/{resource}", data=data)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            return ProviderResult(status="failed")

        provider_ref = payload.get("sid") if isinstance(payload, dict) else None
        if not isinstance(provider_ref, str) or not provider_ref:
            return ProviderResult(status="failed")
        return ProviderResult(status="accepted", provider_ref=provider_ref)


_PROCESSED_KEYS: dict[str, float] = {}


def reset_message_guards() -> None:
    _PROCESSED_KEYS.clear()


def mask_mobile(mobile_number: str) -> str:
    digits = re.sub(r"\D", "", mobile_number)
    if len(digits) < 4:
        return "XXXX"
    return f"XXXXXX{digits[-4:]}"


def _to_e164(mobile_number: str) -> str:
    stripped = mobile_number.strip()
    if stripped.startswith("+"):
        return stripped

    digits = re.sub(r"\D", "", stripped)
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    return f"+{digits}"


def _voice_twiml(script: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Say>{escape(script)}</Say></Response>'


def _require_supabase_config() -> tuple[str, str]:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise AadhaarMessagingError(
            "AADHAAR_MESSAGING_UNAVAILABLE",
            "Aadhaar messaging is not configured on the backend.",
            503,
        )
    return settings.SUPABASE_URL.rstrip("/"), settings.SUPABASE_SERVICE_ROLE_KEY


def _headers(service_role_key: str) -> dict[str, str]:
    return {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }


def resolve_recipient(citizen_ref: str) -> MessagingRecipient:
    supabase_url, service_role_key = _require_supabase_config()

    try:
        with httpx.Client(headers=_headers(service_role_key), timeout=20) as client:
            response = client.get(
                f"{supabase_url}/rest/v1/demo_citizens",
                params={
                    "select": "demo_ref,demo_name,mobile_number",
                    "demo_ref": f"eq.{citizen_ref}",
                    "limit": "1",
                },
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AadhaarMessagingError(
            "AADHAAR_MESSAGING_UNAVAILABLE",
            "Could not resolve the synthetic citizen record.",
            503,
        ) from exc

    if not isinstance(payload, list) or not payload:
        raise AadhaarMessagingError(
            "AADHAAR_RECIPIENT_NOT_FOUND",
            "No matching synthetic citizen was found for messaging.",
            404,
        )

    row: dict[str, Any] = payload[0]
    mobile = row.get("mobile_number")
    if not isinstance(mobile, str) or not MOBILE_PATTERN.search(mobile):
        raise AadhaarMessagingError(
            "AADHAAR_RECIPIENT_NOT_ELIGIBLE",
            "This synthetic citizen does not have an eligible registered mobile number.",
            422,
        )

    return MessagingRecipient(
        citizen_ref=str(row.get("demo_ref", citizen_ref)),
        demo_name=str(row.get("demo_name", "Synthetic citizen")),
        mobile_number=MOBILE_PATTERN.search(mobile).group(0),  # type: ignore[union-attr]
    )


def _guard_duplicate(user: AuthenticatedUser, citizen_ref: str, idempotency_key: str) -> None:
    now = time.monotonic()
    ttl = settings.AADHAAR_MESSAGE_RATE_LIMIT_SECONDS
    expired = [key for key, expires_at in _PROCESSED_KEYS.items() if expires_at <= now]
    for key in expired:
        _PROCESSED_KEYS.pop(key, None)

    key = f"{user.user_id}:{citizen_ref}:{idempotency_key}"
    if key in _PROCESSED_KEYS:
        raise AadhaarMessagingError(
            "DUPLICATE_MESSAGE_REQUEST",
            "This reminder request was already submitted. Wait before trying again.",
            409,
        )
    _PROCESSED_KEYS[key] = now + max(ttl, 1)


def _select_provider(provider: AadhaarMessagingProvider | None) -> AadhaarMessagingProvider:
    if provider is not None:
        return provider
    if settings.AADHAAR_MESSAGING_PROVIDER == "fake":
        return FakeAadhaarMessagingProvider()
    if settings.AADHAAR_MESSAGING_PROVIDER == "twilio":
        return TwilioAadhaarMessagingProvider()
    raise AadhaarMessagingError(
        "AADHAAR_MESSAGING_UNAVAILABLE",
        "Aadhaar messaging provider is not available.",
        503,
    )


def send_custom_message(
    *,
    user: AuthenticatedUser,
    citizen_ref: str,
    message: str,
    idempotency_key: str,
    provider: AadhaarMessagingProvider | None = None,
) -> dict[str, Any]:
    if not settings.AADHAAR_MESSAGING_ENABLED:
        raise AadhaarMessagingError(
            "AADHAAR_MESSAGING_DISABLED",
            "Aadhaar messaging is disabled on this backend.",
            503,
        )
    normalized_message = message.strip()
    if not normalized_message:
        raise AadhaarMessagingError(
            "EMPTY_MESSAGE",
            "Enter a message before sending.",
            422,
        )
    if len(normalized_message) > settings.AADHAAR_MESSAGE_MAX_CHARS:
        raise AadhaarMessagingError(
            "MESSAGE_TOO_LONG",
            f"Message must be {settings.AADHAAR_MESSAGE_MAX_CHARS} characters or fewer.",
            422,
        )
    if not idempotency_key.strip():
        raise AadhaarMessagingError(
            "MISSING_IDEMPOTENCY_KEY",
            "A request key is required for messaging.",
            422,
        )

    recipient = resolve_recipient(citizen_ref)
    _guard_duplicate(user, recipient.citizen_ref, idempotency_key.strip())

    active_provider = _select_provider(provider)
    sms = active_provider.send_sms(
        to_mobile=recipient.mobile_number,
        message=normalized_message,
    )
    if sms.status != "accepted":
        return {
            "citizen_ref": recipient.citizen_ref,
            "recipient_name": recipient.demo_name,
            "masked_mobile": mask_mobile(recipient.mobile_number),
            "sms_status": "failed",
            "voice_status": "not_attempted",
            "message": "SMS request failed; reminder call was not attempted.",
        }

    voice = active_provider.initiate_voice_reminder(
        to_mobile=recipient.mobile_number,
        script=VOICE_REMINDER_TEXT,
    )
    voice_status: VoiceStatus = "initiated" if voice.status == "accepted" else "failed"
    return {
        "citizen_ref": recipient.citizen_ref,
        "recipient_name": recipient.demo_name,
        "masked_mobile": mask_mobile(recipient.mobile_number),
        "sms_status": "accepted",
        "voice_status": voice_status,
        "message": (
            "SMS request accepted; reminder call request initiated."
            if voice_status == "initiated"
            else "SMS request accepted; reminder call request failed."
        ),
    }
