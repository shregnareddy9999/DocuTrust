"""POST /aadhaar/link: upload -> validate -> OCR -> look up student + government records.

Outcomes: FOUND | NO_LINKED_DOCUMENTS_FOUND | PROCESSING_FAILED (AGENTS.md Rules 3-4):
  * NO_LINKED_DOCUMENTS_FOUND is a neutral 200, never "forged" or "invalid".
  * PROCESSING_FAILED (503) is a technical failure only; it is never a verdict.

Privacy (hard requirements):
  * The number is masked in every response (XXXX XXXX 1234).
  * The number is never logged, never stored in plain text, never written to disk, never on-chain.
    Lookup uses a SHA-256 of the synthetic demo number; the uploaded file is never persisted.
  * This module contains no blockchain code.
"""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

import ocr
from db import get_db

router = APIRouter(prefix="/aadhaar")
log = logging.getLogger("ps21.aadhaar")  # only ever logs a status word, never a number

MAX_BYTES = 5 * 1024 * 1024
_MAGIC = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"%PDF-")  # PNG, JPEG, PDF
_DIGITS12 = re.compile(r"^\d{12}$")

SYNTHETIC_NOTE = "Synthetic / Demo Data. Matched against a synthetic demo registry only."

# Synthetic demo numbers (start with 0000: cannot be a real Aadhaar). Stored hashed, in our own
# table so `GET /government-records` can never expose them.
DEMO_LINKS = {
    "000000001001": "DEMO-STU-001",
    "000000001002": "DEMO-STU-002",
    "000000001003": "DEMO-STU-003",
}


def mask(number: str) -> str:
    """'000000001001' -> 'XXXX XXXX 1001'."""
    return f"XXXX XXXX {number[-4:]}"


def _digest(number: str) -> str:
    return hashlib.sha256(number.encode()).hexdigest()


def _no_store(resp: JSONResponse) -> JSONResponse:
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _failed(reason: str) -> JSONResponse:
    log.warning("aadhaar link: PROCESSING_FAILED (%s)", reason)
    return _no_store(JSONResponse(status_code=503, content={
        "status": "PROCESSING_FAILED",
        "reason": reason,
        "message": "Could not complete the lookup (technical error). No outcome was produced.",
        "synthetic_data": True,
    }))


def _ensure_demo_links(db: sqlite3.Connection) -> None:
    db.execute(
        "CREATE TABLE IF NOT EXISTS aadhaar_links ("
        " number_sha256 TEXT PRIMARY KEY, last4 TEXT NOT NULL,"
        " student_id TEXT NOT NULL REFERENCES students(id))"
    )
    for number, student_id in DEMO_LINKS.items():
        db.execute(
            "INSERT OR IGNORE INTO aadhaar_links VALUES (?,?,?)",
            (_digest(number), number[-4:], student_id),
        )


def _lookup(db: sqlite3.Connection, number: str) -> tuple[dict | None, list[dict]]:
    _ensure_demo_links(db)
    link = db.execute(
        "SELECT s.id, s.name, s.program FROM aadhaar_links a JOIN students s ON s.id = a.student_id"
        " WHERE a.number_sha256 = ?", (_digest(number),)).fetchone()
    if link is None:
        return None, []
    records = db.execute(
        "SELECT id, record_type, record_ref, holder_name FROM government_records"
        " WHERE student_id = ? ORDER BY id", (link["id"],)).fetchall()
    return dict(link), [dict(r) for r in records]


@router.post("/link")
async def link_aadhaar(file: UploadFile = File(...), db: sqlite3.Connection = Depends(get_db)):
    # 1. Validate the file (client errors are plain 4xx, not technical failures).
    data = await file.read(MAX_BYTES + 1)  # bounded read
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 5 MB)")
    if not data.startswith(_MAGIC):
        raise HTTPException(415, "Unsupported file type (PNG, JPEG or PDF only)")

    # 2. Extract the number. Technical failure -> PROCESSING_FAILED.
    try:
        fields = ocr.extract_fields(data, filename=file.filename)
    except ocr.OCRError as exc:
        return _failed(exc.code)
    except Exception:  # noqa: BLE001 - never let an OCR bug become a verdict or leak text
        return _failed("OCR_UNEXPECTED_ERROR")

    raw = fields.get("aadhaar_number")
    if not raw:
        return _failed("AADHAAR_NUMBER_NOT_EXTRACTED")
    number = re.sub(r"[\s-]", "", str(raw))
    if not _DIGITS12.match(number):
        return _failed("AADHAAR_NUMBER_MALFORMED")

    # 3. Look up student + government records.
    try:
        student, records = _lookup(db, number)
    except sqlite3.Error:
        return _failed("DATABASE_ERROR")

    base = {"aadhaar_masked": mask(number), "synthetic_data": True, "note": SYNTHETIC_NOTE}

    # 4. Neutral outcome: no student, or a student with no government records.
    if student is None or not records:
        log.info("aadhaar link: NO_LINKED_DOCUMENTS_FOUND")
        return _no_store(JSONResponse(content={
            "status": "NO_LINKED_DOCUMENTS_FOUND", "student": None, "records": [], **base}))

    log.info("aadhaar link: FOUND")
    return _no_store(JSONResponse(content={
        "status": "FOUND", "student": student, "records": records, **base}))
