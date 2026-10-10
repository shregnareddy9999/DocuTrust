"""Aadhaar-link synthetic demo lookup and asset helpers."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import UploadFile

from app.config import settings
from app.fixtures.aadhaar_link_data import (
    AADHAAR_UPLOAD_MARKER,
    DOCUMENT_ORDER,
    DOCUMENT_TYPE_LABELS,
    LINKED_ASSETS,
)
from app.services.upload_service import (
    CHUNK_SIZE,
    UploadError,
    generate_temp_key,
    safe_upload_path,
    sniff_mime_type,
    validate_image,
    validate_pdf,
)


AADHAAR_REF_PATTERN = re.compile(r"AAD-1000[12]", re.IGNORECASE)


class AadhaarLinkError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AadhaarAssetNotFoundError(Exception):
    """Requested demo asset reference is not whitelisted or the file is missing."""


def _require_supabase_config() -> tuple[str, str]:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise AadhaarLinkError(
            code="AADHAAR_LINK_UNAVAILABLE",
            message="Aadhaar Link demo lookup is not configured on the backend.",
            status_code=503,
        )
    return settings.SUPABASE_URL.rstrip("/"), settings.SUPABASE_SERVICE_ROLE_KEY


def _headers(service_role_key: str) -> dict[str, str]:
    return {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }


async def validate_temporary_aadhaar_upload(file: UploadFile) -> str | None:
    """Validate an Aadhaar demo upload, then delete the temp file in all cases."""

    temp_key = generate_temp_key()
    temp_path = safe_upload_path(temp_key)
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    byte_count = 0
    scanned = bytearray()

    try:
        with open(temp_path, "wb") as out:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break

                byte_count += len(chunk)
                if byte_count > max_bytes:
                    raise UploadError(
                        code="FILE_TOO_LARGE",
                        message=f"File size exceeds maximum allowed ({settings.MAX_UPLOAD_MB} MB)",
                        status_code=413,
                    )

                if len(scanned) < 2 * 1024 * 1024:
                    scanned.extend(chunk[: max(0, 2 * 1024 * 1024 - len(scanned))])
                out.write(chunk)

        if byte_count == 0:
            raise UploadError(
                code="EMPTY_OR_CORRUPT_FILE",
                message="Uploaded file is empty",
                status_code=422,
            )

        sniffed_mime = sniff_mime_type(temp_path)
        allowed = set(settings.ALLOWED_MIME_TYPES)
        if not sniffed_mime or sniffed_mime not in allowed:
            raise UploadError(
                code="UNSUPPORTED_MEDIA_TYPE",
                message=f"Unsupported file type. Allowed: {', '.join(sorted(allowed))}",
                status_code=415,
            )

        declared_mime = file.content_type
        if declared_mime and declared_mime != sniffed_mime:
            raise UploadError(
                code="UNSUPPORTED_MEDIA_TYPE",
                message=(
                    f"Declared MIME type '{declared_mime}' does not match "
                    f"detected type '{sniffed_mime}'"
                ),
                status_code=415,
            )

        filename = Path((file.filename or "").replace("\\", "/")).name
        ext = Path(filename).suffix.lower()
        expected_exts = {
            "application/pdf": {".pdf"},
            "image/png": {".png"},
            "image/jpeg": {".jpg", ".jpeg"},
        }
        if ext and ext not in expected_exts.get(sniffed_mime, set()):
            raise UploadError(
                code="UNSUPPORTED_MEDIA_TYPE",
                message="Filename extension does not match detected file type",
                status_code=415,
            )

        if sniffed_mime.startswith("image/"):
            validate_image(temp_path)
        else:
            validate_pdf(temp_path)

        scanned_text = scanned.decode("latin-1", errors="ignore")
        if AADHAAR_UPLOAD_MARKER not in scanned_text:
            raise UploadError(
                code="AADHAAR_DEMO_CARD_REQUIRED",
                message=(
                    "Upload a DocuTrust synthetic Aadhaar demo card. Other document "
                    "types are not accepted on this page."
                ),
                status_code=422,
            )

        match = AADHAAR_REF_PATTERN.search(scanned_text)
        if not match:
            raise UploadError(
                code="AADHAAR_DEMO_REFERENCE_NOT_FOUND",
                message="The synthetic Aadhaar demo reference could not be read from the uploaded card.",
                status_code=422,
            )

        return match.group(0).upper()
    finally:
        temp_path.unlink(missing_ok=True)


def _safe_supabase_error(exc: httpx.HTTPStatusError) -> AadhaarLinkError:
    message = "Supabase could not read the Aadhaar Link demo tables."
    try:
        payload = exc.response.json()
        safe = payload.get("message") or payload.get("hint") or payload.get("code")
        if safe:
            message = f"{message} {safe}"
    except ValueError:
        pass
    return AadhaarLinkError(
        code="AADHAAR_LINK_UNAVAILABLE",
        message=message,
        status_code=503,
    )


def _get_json(client: httpx.Client, url: str, params: dict[str, str]) -> list[dict[str, Any]]:
    response = client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise AadhaarLinkError(
            code="AADHAAR_LINK_UNAVAILABLE",
            message="Supabase returned an unexpected Aadhaar Link demo response.",
            status_code=503,
        )
    return payload


def lookup_aadhaar_link(aadhaar_ref: str | None) -> dict[str, Any]:
    if not aadhaar_ref:
        raise AadhaarLinkError(
            code="AADHAAR_DEMO_REFERENCE_NOT_FOUND",
            message="The synthetic Aadhaar demo reference could not be read from the uploaded card.",
            status_code=422,
        )

    supabase_url, service_role_key = _require_supabase_config()
    headers = _headers(service_role_key)

    try:
        with httpx.Client(headers=headers, timeout=20) as client:
            citizen_params = {
                "select": "*",
                "order": "demo_ref.asc",
                "limit": "1",
                "demo_aadhaar_ref": f"eq.{aadhaar_ref}",
            }

            citizens = _get_json(
                client,
                f"{supabase_url}/rest/v1/demo_citizens",
                citizen_params,
            )
            if not citizens:
                raise AadhaarLinkError(
                    code="AADHAAR_REFERENCE_NOT_FOUND",
                    message="No matching synthetic Aadhaar reference was found in the demo registry.",
                    status_code=404,
                )

            citizen = citizens[0]
            linked_documents = _get_json(
                client,
                f"{supabase_url}/rest/v1/demo_linked_documents",
                {
                    "select": "*",
                    "citizen_id": f"eq.{citizen['id']}",
                    "order": "demo_document_ref.asc",
                },
            )
    except AadhaarLinkError:
        raise
    except httpx.HTTPStatusError as exc:
        raise _safe_supabase_error(exc) from exc
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise AadhaarLinkError(
            code="AADHAAR_LINK_UNAVAILABLE",
            message="Could not complete the Aadhaar Link demo lookup.",
            status_code=503,
        ) from exc

    return _build_response(citizen, linked_documents)


def _build_response(
    citizen: dict[str, Any],
    linked_documents: list[dict[str, Any]],
) -> dict[str, Any]:
    citizen_mobile_number = _citizen_mobile_placeholder(citizen)
    rows = []
    for row in linked_documents:
        document_ref = str(row.get("demo_document_ref", ""))
        asset = LINKED_ASSETS.get(document_ref)
        document_type = str(row.get("document_type", "UNKNOWN"))
        rows.append(
            {
                "id": str(row.get("id", document_ref)),
                "document_type": document_type,
                "document_type_label": DOCUMENT_TYPE_LABELS.get(document_type, "Synthetic Demo Record"),
                "demo_document_ref": document_ref,
                "display_value": str(row.get("display_value", "")),
                "issuer_label": asset.issuer_label if asset else "Synthetic demo registry",
                "asset_ref": document_ref if asset else None,
                "asset_mime_type": asset.mime_type if asset else None,
                "status_label": asset.status_label if asset else "Listed in synthetic registry",
                "demo_mobile_placeholder": _mobile_placeholder(
                    document_type,
                    citizen_mobile_number,
                    str(row.get("display_value", "")),
                ),
            }
        )

    rows.sort(key=lambda item: DOCUMENT_ORDER.get(item["demo_document_ref"], 999))

    return {
        "lookup_id": f"aadhaar-link-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "source": "synthetic-demo",
        "reference_detected": True,
        "citizen": {
            "citizen_ref": str(citizen.get("demo_ref", "")),
            "demo_name": str(citizen.get("demo_name", "")),
            "aadhaar_ref": str(citizen.get("demo_aadhaar_ref", "")),
            "masked_aadhaar": _masked_aadhaar(str(citizen.get("demo_aadhaar_ref", ""))),
            "demo_mobile_placeholder": citizen_mobile_number,
        },
        "linked_documents": rows,
        "summary": {
            "linked_record_count": len(rows),
            "blockchain_seed": "local-demo-seed",
            "last_sync_label": "Synthetic demo registry snapshot",
        },
    }


def _masked_aadhaar(aadhaar_ref: str) -> str:
    suffix = aadhaar_ref[-4:] if len(aadhaar_ref) >= 4 else "0000"
    return f"DEMO-XXXX-{suffix}"


def _citizen_mobile_placeholder(citizen: dict[str, Any]) -> str | None:
    mobile_number = citizen.get("mobile_number")
    if not isinstance(mobile_number, str):
        return None
    match = re.search(r"\b\d{10}\b", mobile_number)
    return match.group(0) if match else None


def _mobile_placeholder(
    document_type: str,
    citizen_mobile_number: str | None,
    display_value: str,
) -> str | None:
    if document_type != "MOBILE":
        return None
    if citizen_mobile_number:
        return citizen_mobile_number
    match = re.search(r"\b\d{10}\b", display_value)
    return match.group(0) if match else "No fictional demo mobile number stored in Supabase"


def get_asset_file(document_ref: str) -> tuple[Path, str, str]:
    asset = LINKED_ASSETS.get(document_ref)
    if asset is None:
        raise AadhaarAssetNotFoundError(document_ref)

    base_dir = (Path(__file__).resolve().parents[1] / "fixtures" / "sample_documents").resolve()
    path = (base_dir / asset.asset_filename).resolve()
    if base_dir not in path.parents or not path.exists():
        raise AadhaarAssetNotFoundError(document_ref)

    return path, asset.mime_type, asset.asset_filename
