"""Synthetic Aadhaar-link demo endpoints."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.services.aadhaar_link_service import (
    AadhaarAssetNotFoundError,
    AadhaarLinkError,
    lookup_aadhaar_link,
    get_asset_file,
    validate_temporary_aadhaar_upload,
)
from app.services.upload_service import UploadError


router = APIRouter()


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
