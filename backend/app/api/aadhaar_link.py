"""Synthetic Aadhaar-link demo endpoints."""

from fastapi import APIRouter, File, Header, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.auth_service import AuthError, AuthUnavailableError, require_authenticated_user
from app.services.aadhaar_link_service import (
    AadhaarAssetNotFoundError,
    AadhaarLinkError,
    lookup_aadhaar_link,
    get_asset_file,
    validate_temporary_aadhaar_upload,
)
from app.services.aadhaar_messaging_service import AadhaarMessagingError, send_custom_message
from app.services.upload_service import UploadError


router = APIRouter()


class AadhaarMessageRequest(BaseModel):
    message: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


def _http_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": {}}},
    )


@router.post("/aadhaar-link", status_code=status.HTTP_200_OK)
async def upload_aadhaar_link(file: UploadFile = File(...)):
    try:
        aadhaar_ref = await validate_temporary_aadhaar_upload(file)
        return lookup_aadhaar_link(aadhaar_ref)
    except UploadError as exc:
        _http_error(exc.status_code, exc.code, exc.message)
    except AadhaarLinkError as exc:
        _http_error(exc.status_code, exc.code, exc.message)


@router.get("/aadhaar-link/assets/{document_ref}")
async def get_aadhaar_link_asset(document_ref: str):
    try:
        path, mime_type, filename = get_asset_file(document_ref)
        return FileResponse(
            path=path,
            media_type=mime_type,
            filename=filename,
            content_disposition_type="inline",
        )
    except AadhaarAssetNotFoundError:
        _http_error(404, "AADHAAR_ASSET_NOT_FOUND", "Synthetic demo asset not found.")


@router.post("/aadhaar-link/{citizen_ref}/message", status_code=status.HTTP_200_OK)
def send_aadhaar_link_message(
    citizen_ref: str,
    payload: AadhaarMessageRequest,
    authorization: str | None = Header(default=None),
):
    try:
        user = require_authenticated_user(authorization)
        return send_custom_message(
            user=user,
            citizen_ref=citizen_ref,
            message=payload.message,
            idempotency_key=payload.idempotency_key,
        )
    except AuthError:
        _http_error(401, "AUTH_REQUIRED", "Sign in before sending a reminder.")
    except AuthUnavailableError:
        _http_error(503, "AUTH_UNAVAILABLE", "Authentication is not configured on the backend.")
    except AadhaarMessagingError as exc:
        _http_error(exc.status_code, exc.code, exc.message)
