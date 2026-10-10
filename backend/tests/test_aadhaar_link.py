import io
from pathlib import Path

import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo

import app.services.aadhaar_link_service as aadhaar_service
import app.services.aadhaar_messaging_service as messaging_service
from app.fixtures.aadhaar_link_data import AADHAAR_UPLOAD_MARKER


def _png_bytes(aadhaar_ref: str | None = None) -> bytes:
    buf = io.BytesIO()
    metadata = None
    if aadhaar_ref:
        metadata = PngInfo()
        metadata.add_text("DocuTrustDemoMarker", AADHAAR_UPLOAD_MARKER)
        metadata.add_text("AadhaarDemoReference", aadhaar_ref)
    Image.new("RGB", (120, 80), "white").save(buf, format="PNG", pnginfo=metadata)
    return buf.getvalue()


class FakeSupabaseResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            request = httpx.Request("GET", "https://example.test")
            response = httpx.Response(self.status_code, request=request, json=self._payload)
            raise httpx.HTTPStatusError("error", request=request, response=response)


class FakeSupabaseClient:
    def __init__(self, *args, **kwargs):
        self.citizens = [
            {
                "id": "citizen-1",
                "demo_ref": "CIT-10001",
                "demo_name": "Aarav Demo",
                "demo_aadhaar_ref": "AAD-10001",
                "mobile_number": "9000005001",
            },
            {
                "id": "citizen-2",
                "demo_ref": "CIT-10002",
                "demo_name": "Meera Demo",
                "demo_aadhaar_ref": "AAD-10002",
                "mobile_number": "9000005002",
            },
            {
                "id": "citizen-3",
                "demo_ref": "CIT-20999",
                "demo_name": "Nisha Demo",
                "demo_aadhaar_ref": "AAD-20999",
                "mobile_number": "9000005999",
            },
            {
                "id": "citizen-4",
                "demo_ref": "CIT-10004",
                "demo_name": "Siya Demo",
                "demo_aadhaar_ref": "AAD-10004",
                "mobile_number": "9000005004",
            },
            {
                "id": "citizen-5",
                "demo_ref": "CIT-30000",
                "demo_name": "Dev Demo",
                "demo_aadhaar_ref": "AAD-30000",
                "mobile_number": None,
            },
        ]
        self.linked = [
            {
                "id": "link-pan",
                "citizen_id": "citizen-1",
                "document_type": "PAN",
                "demo_document_ref": "PAN-20001",
                "display_value": "PAN Card reference: PAN-20001",
            },
            {
                "id": "link-mobile",
                "citizen_id": "citizen-1",
                "document_type": "MOBILE",
                "demo_document_ref": "MOB-50001",
                "display_value": "Mobile Connection reference: MOB-50001",
            },
            {
                "id": "link-bank",
                "citizen_id": "citizen-2",
                "document_type": "BANK_ACCOUNT",
                "demo_document_ref": "BNK-60002",
                "display_value": "Bank Account reference: BNK-60002",
            },
            {
                "id": "link-custom",
                "citizen_id": "citizen-3",
                "document_type": "SCHOLARSHIP",
                "demo_document_ref": "SCH-99001",
                "display_value": "Scholarship reference: SCH-99001",
            },
            {
                "id": "link-pan-20004",
                "citizen_id": "citizen-4",
                "document_type": "PAN",
                "demo_document_ref": "PAN-20004",
                "display_value": "PAN Card reference: PAN-20004",
            },
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None, headers=None):
        if url.endswith("/auth/v1/user"):
            auth = (headers or {}).get("Authorization", "")
            if auth == "Bearer valid-user-token":
                return FakeSupabaseResponse({"id": "user-demo-001", "email": "operator@example.test"})
            return FakeSupabaseResponse({"message": "unauthorized"}, status_code=401)

        if url.endswith("/demo_citizens"):
            params = params or {}
            citizen_filter = params.get("demo_ref")
            if citizen_filter:
                ref = citizen_filter.replace("eq.", "")
                return FakeSupabaseResponse([row for row in self.citizens if row["demo_ref"] == ref])
            aadhaar_filter = params.get("demo_aadhaar_ref")
            if aadhaar_filter:
                ref = aadhaar_filter.replace("eq.", "")
                return FakeSupabaseResponse([row for row in self.citizens if row["demo_aadhaar_ref"] == ref])
            return FakeSupabaseResponse([self.citizens[0]])

        if url.endswith("/demo_linked_documents"):
            citizen_id = params["citizen_id"].replace("eq.", "")
            return FakeSupabaseResponse([row for row in self.linked if row["citizen_id"] == citizen_id])

        return FakeSupabaseResponse({"message": "not found"}, status_code=404)


@pytest.fixture()
def fake_supabase(monkeypatch):
    monkeypatch.setattr(aadhaar_service.httpx, "Client", FakeSupabaseClient)
    monkeypatch.setattr(messaging_service.httpx, "Client", FakeSupabaseClient)


@pytest.fixture()
def messaging_enabled(monkeypatch):
    monkeypatch.setattr(messaging_service.settings, "AADHAAR_MESSAGING_ENABLED", True)
    monkeypatch.setattr(messaging_service.settings, "AADHAAR_MESSAGING_PROVIDER", "fake")
    monkeypatch.setattr(messaging_service.settings, "AADHAAR_MESSAGE_RATE_LIMIT_SECONDS", 30)
    messaging_service.reset_message_guards()
    yield
    messaging_service.reset_message_guards()


class CaptureProvider(messaging_service.FakeAadhaarMessagingProvider):
    last_instance = None

    def __init__(self, *, sms_status="accepted", voice_status="accepted"):
        super().__init__(sms_status=sms_status, voice_status=voice_status)
        CaptureProvider.last_instance = self


def _message_payload(key="request-1", message="Please visit the demo counter."):
    return {"message": message, "idempotency_key": key}


def test_aadhaar_message_requires_auth(client, fake_supabase, messaging_enabled):
    response = client.post(
        "/api/v1/aadhaar-link/CIT-10001/message",
        json=_message_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_aadhaar_message_rejects_invalid_auth(client, fake_supabase, messaging_enabled):
    response = client.post(
        "/api/v1/aadhaar-link/CIT-10001/message",
        headers={"Authorization": "Bearer invalid-user-token"},
        json=_message_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_aadhaar_message_disabled_by_default(client, fake_supabase):
    response = client.post(
        "/api/v1/aadhaar-link/CIT-10001/message",
        headers={"Authorization": "Bearer valid-user-token"},
        json=_message_payload(),
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AADHAAR_MESSAGING_DISABLED"


def test_aadhaar_message_resolves_recipient_server_side(client, monkeypatch, fake_supabase, messaging_enabled):
    monkeypatch.setattr(messaging_service, "FakeAadhaarMessagingProvider", CaptureProvider)

    response = client.post(
        "/api/v1/aadhaar-link/CIT-10001/message",
        headers={"Authorization": "Bearer valid-user-token"},
        json={
            **_message_payload(),
            "mobile_number": "0000000000",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sms_status"] == "accepted"
    assert body["voice_status"] == "initiated"
    assert body["masked_mobile"] == "XXXXXX5001"
    assert "9000005001" not in str(body)
    assert CaptureProvider.last_instance is not None
    assert CaptureProvider.last_instance.sms_requests == [
        ("9000005001", "Please visit the demo counter.")
    ]
    assert CaptureProvider.last_instance.voice_requests == [
        ("9000005001", messaging_service.VOICE_REMINDER_TEXT)
    ]


def test_aadhaar_message_sms_failure_prevents_voice(client, monkeypatch, fake_supabase, messaging_enabled):
    class SmsFailureProvider(CaptureProvider):
        def __init__(self):
            super().__init__(sms_status="failed")

    monkeypatch.setattr(messaging_service, "FakeAadhaarMessagingProvider", SmsFailureProvider)

    response = client.post(
        "/api/v1/aadhaar-link/CIT-10001/message",
        headers={"Authorization": "Bearer valid-user-token"},
        json=_message_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sms_status"] == "failed"
    assert body["voice_status"] == "not_attempted"
    assert CaptureProvider.last_instance is not None
    assert CaptureProvider.last_instance.voice_requests == []


def test_aadhaar_message_sms_success_voice_failure(client, monkeypatch, fake_supabase, messaging_enabled):
    class VoiceFailureProvider(CaptureProvider):
        def __init__(self):
            super().__init__(voice_status="failed")

    monkeypatch.setattr(messaging_service, "FakeAadhaarMessagingProvider", VoiceFailureProvider)

    response = client.post(
        "/api/v1/aadhaar-link/CIT-10001/message",
        headers={"Authorization": "Bearer valid-user-token"},
        json=_message_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sms_status"] == "accepted"
    assert body["voice_status"] == "failed"
    assert body["message"] == "SMS request accepted; reminder call request failed."


def test_aadhaar_message_duplicate_submission_is_blocked(client, fake_supabase, messaging_enabled):
    headers = {"Authorization": "Bearer valid-user-token"}
    first = client.post(
        "/api/v1/aadhaar-link/CIT-10001/message",
        headers=headers,
        json=_message_payload(key="same-key"),
    )
    second = client.post(
        "/api/v1/aadhaar-link/CIT-10001/message",
        headers=headers,
        json=_message_payload(key="same-key"),
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DUPLICATE_MESSAGE_REQUEST"


def test_twilio_provider_submits_sms_then_voice(monkeypatch):
    calls = []

    class FakeTwilioResponse:
        def __init__(self, sid):
            self._sid = sid

        def raise_for_status(self):
            return None

        def json(self):
            return {"sid": self._sid, "status": "queued"}

    class FakeTwilioClient:
        def __init__(self, *args, **kwargs):
            self.auth = kwargs.get("auth")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, data):
            calls.append((url, data, self.auth))
            return FakeTwilioResponse(f"SM{len(calls)}")

    monkeypatch.setattr(messaging_service.httpx, "Client", FakeTwilioClient)
    monkeypatch.setattr(messaging_service.settings, "TWILIO_ACCOUNT_SID", "AC_test")
    monkeypatch.setattr(messaging_service.settings, "TWILIO_AUTH_TOKEN", "auth-token")
    monkeypatch.setattr(messaging_service.settings, "TWILIO_PHONE_NUMBER", "+15551230000")

    provider = messaging_service.TwilioAadhaarMessagingProvider()
    sms = provider.send_sms(to_mobile="9000005001", message="Please visit the demo counter.")
    voice = provider.initiate_voice_reminder(
        to_mobile="9000005001",
        script=messaging_service.VOICE_REMINDER_TEXT,
    )

    assert sms.status == "accepted"
    assert voice.status == "accepted"
    assert calls[0][0].endswith("/Messages.json")
    assert calls[0][1]["To"] == "+919000005001"
    assert calls[0][1]["Body"] == "Please visit the demo counter."
    assert calls[1][0].endswith("/Calls.json")
    assert calls[1][1]["To"] == "+919000005001"
    assert calls[1][1]["Twiml"].endswith(
        "<Response><Say>namashkar, ap please apka sms dekhiye. namaste, please check your sms.</Say></Response>"
    )
    assert calls[0][2] == ("AC_test", "auth-token")


def test_twilio_provider_sms_failure_prevents_voice(client, monkeypatch, fake_supabase, messaging_enabled):
    class SmsFailureProvider(CaptureProvider):
        def __init__(self):
            super().__init__(sms_status="failed")

    monkeypatch.setattr(messaging_service.settings, "AADHAAR_MESSAGING_PROVIDER", "twilio")
    monkeypatch.setattr(messaging_service, "TwilioAadhaarMessagingProvider", SmsFailureProvider)

    response = client.post(
        "/api/v1/aadhaar-link/CIT-10001/message",
        headers={"Authorization": "Bearer valid-user-token"},
        json=_message_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sms_status"] == "failed"
    assert body["voice_status"] == "not_attempted"
    assert CaptureProvider.last_instance is not None
    assert CaptureProvider.last_instance.voice_requests == []


def test_aadhaar_link_upload_reads_supabase_and_cleans_temp_files(
    client,
    temp_upload_dir: Path,
    test_settings,
    monkeypatch,
    fake_supabase,
):
    monkeypatch.setattr(aadhaar_service, "settings", test_settings)

    response = client.post(
        "/api/v1/aadhaar-link",
        files={"file": ("aadhaar_AAD-10001.png", _png_bytes("AAD-10001"), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "synthetic-demo"
    assert data["reference_detected"] is True
    assert data["citizen"]["citizen_ref"] == "CIT-10001"
    assert data["citizen"]["demo_name"] == "Aarav Demo"
    assert data["citizen"]["demo_mobile_placeholder"] == "9000005001"
    assert data["summary"]["linked_record_count"] == 2
    assert [row["demo_document_ref"] for row in data["linked_documents"]] == ["PAN-20001", "MOB-50001"]
    assert data["linked_documents"][1]["asset_ref"] is None
    assert data["linked_documents"][1]["demo_mobile_placeholder"] == "9000005001"
    assert list(temp_upload_dir.iterdir()) == []


def test_aadhaar_link_upload_accepts_supabase_only_reference_without_code_fixture(
    client,
    temp_upload_dir: Path,
    test_settings,
    monkeypatch,
    fake_supabase,
):
    monkeypatch.setattr(aadhaar_service, "settings", test_settings)

    response = client.post(
        "/api/v1/aadhaar-link",
        files={"file": ("aadhaar_AAD-20999.png", _png_bytes("AAD-20999"), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["citizen"]["citizen_ref"] == "CIT-20999"
    assert data["citizen"]["demo_mobile_placeholder"] == "9000005999"
    assert data["summary"]["linked_record_count"] == 1
    assert data["linked_documents"][0]["demo_document_ref"] == "SCH-99001"
    assert data["linked_documents"][0]["document_type_label"] == "Synthetic Demo Record"
    assert data["linked_documents"][0]["issuer_label"] == "Synthetic demo registry"
    assert data["linked_documents"][0]["asset_ref"] is None
    assert data["linked_documents"][0]["status_label"] == "Listed in synthetic registry"
    assert list(temp_upload_dir.iterdir()) == []


def test_aadhaar_link_upload_uses_convention_based_sample_preview_for_new_supabase_record(
    client,
    temp_upload_dir: Path,
    test_settings,
    monkeypatch,
    fake_supabase,
):
    monkeypatch.setattr(aadhaar_service, "settings", test_settings)

    response = client.post(
        "/api/v1/aadhaar-link",
        files={"file": ("aadhaar_AAD-10004.png", _png_bytes("AAD-10004"), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["citizen"]["citizen_ref"] == "CIT-10004"
    assert data["linked_documents"][0]["demo_document_ref"] == "PAN-20004"
    assert data["linked_documents"][0]["asset_ref"] == "PAN-20004"
    assert data["linked_documents"][0]["asset_mime_type"] == "image/png"
    assert list(temp_upload_dir.iterdir()) == []


def test_aadhaar_link_upload_returns_not_found_for_unknown_supabase_reference(
    client,
    temp_upload_dir: Path,
    test_settings,
    monkeypatch,
    fake_supabase,
):
    monkeypatch.setattr(aadhaar_service, "settings", test_settings)

    response = client.post(
        "/api/v1/aadhaar-link",
        files={"file": ("aadhaar_AAD-99999.png", _png_bytes("AAD-99999"), "image/png")},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AADHAAR_REFERENCE_NOT_FOUND"
    assert "No matching synthetic Aadhaar reference" in response.json()["error"]["message"]
    assert list(temp_upload_dir.iterdir()) == []


def test_aadhaar_link_upload_handles_citizen_with_no_linked_records(
    client,
    temp_upload_dir: Path,
    test_settings,
    monkeypatch,
    fake_supabase,
):
    monkeypatch.setattr(aadhaar_service, "settings", test_settings)

    response = client.post(
        "/api/v1/aadhaar-link",
        files={"file": ("aadhaar_AAD-30000.png", _png_bytes("AAD-30000"), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["citizen"]["citizen_ref"] == "CIT-30000"
    assert data["summary"]["linked_record_count"] == 0
    assert data["linked_documents"] == []
    assert list(temp_upload_dir.iterdir()) == []


def test_aadhaar_link_upload_rejects_non_aadhaar_demo_card(
    client,
    temp_upload_dir: Path,
    test_settings,
    monkeypatch,
    fake_supabase,
):
    monkeypatch.setattr(aadhaar_service, "settings", test_settings)

    response = client.post(
        "/api/v1/aadhaar-link",
        files={"file": ("aadhaar-demo.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "AADHAAR_DEMO_CARD_REQUIRED"
    assert "synthetic Aadhaar demo card" in response.json()["error"]["message"]
    assert list(temp_upload_dir.iterdir()) == []


def test_aadhaar_link_upload_rejects_bad_file_and_cleans_temp_file(
    client,
    temp_upload_dir: Path,
    test_settings,
    monkeypatch,
    fake_supabase,
):
    monkeypatch.setattr(aadhaar_service, "settings", test_settings)

    response = client.post(
        "/api/v1/aadhaar-link",
        files={"file": ("not-a-doc.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert list(temp_upload_dir.iterdir()) == []


def test_aadhaar_link_asset_serves_whitelisted_sample(client):
    response = client.get("/api/v1/aadhaar-link/assets/PAN-20001")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content.startswith(b"\x89PNG")


def test_aadhaar_link_asset_unknown_reference_returns_404(client):
    response = client.get("/api/v1/aadhaar-link/assets/UNKNOWN-1")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AADHAAR_ASSET_NOT_FOUND"


def test_aadhaar_link_asset_serves_convention_based_sample(client):
    response = client.get("/api/v1/aadhaar-link/assets/PAN-20004")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content.startswith(b"\x89PNG")
