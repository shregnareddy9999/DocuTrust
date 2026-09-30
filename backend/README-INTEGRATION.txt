Dev Task 2 - Upload/OCR + Aadhaar linkage (synthetic demo data only)

Drop-in files (same flat layout as Rehan's Task 1 package):
  ocr.py                    extract_fields(file, filename=None) -> dict   (MOCK; Shregna reuses this)
  routers/aadhaar.py        POST /aadhaar/link
  static/aadhaar.html       served at /static/aadhaar.html
  tests/test_aadhaar.py     EXTRA (not in Dev's file list) - 24 tests

ONE LINE needed in Rehan's main.py (not Dev's file - Rehan/lead to apply):
  ROUTER_MODULES = ["routers.documents", "routers.aadhaar"]

Requires Rehan's db.py (get_db) and seed.py (students + government_records tables).
Run tests:  python -m pytest tests/test_aadhaar.py -q -p no:asyncio
Run app:    uvicorn main:app --port 8000   (from this folder)

extract_fields return shape (stable):
  {"aadhaar_number": str|None, "name": str|None, "ocr_confidence": float, "engine": "mock"}
  Raises ocr.OCRError (.code is a fixed string, never extracted text).
Mock demo hints by filename: default=linked demo number, 'unregistered'=linked to nobody,
  'nonumber'=no number found, 'ocrfail'=simulated engine crash.
