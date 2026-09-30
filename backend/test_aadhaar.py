import io, logging, re, sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import db, ocr
import routers.aadhaar as aad

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
FULL = "000000001001"
SPACED = "0000 0000 1001"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(db, "UPLOAD_DIR", tmp_path / "up")
    import main
    with TestClient(main.app, raise_server_exceptions=False) as c:
        yield c


def post(c, name="card.png", data=PNG, ctype="image/png"):
    return c.post("/aadhaar/link", files={"file": (name, data, ctype)})


def test_found_masks_number_and_lists_records(client):
    r = post(client)
    b = r.json()
    assert r.status_code == 200 and b["status"] == "FOUND"
    assert b["aadhaar_masked"] == "XXXX XXXX 1001"
    assert b["student"]["id"] == "DEMO-STU-001" and b["student"]["name"] == "Aarav Demo"
    assert [x["id"] for x in b["records"]] == ["DEMO-GOV-001", "DEMO-GOV-004"]
    assert b["synthetic_data"] is True
    assert FULL not in r.text and SPACED not in r.text
    assert r.headers["cache-control"] == "no-store"


def test_unregistered_number_is_neutral_200(client):
    r = post(client, "unregistered.png")
    b = r.json()
    assert r.status_code == 200 and b["status"] == "NO_LINKED_DOCUMENTS_FOUND"
    assert b["records"] == [] and b["student"] is None
    assert b["aadhaar_masked"] == "XXXX XXXX 9999"
    assert not any(w in r.text.lower() for w in ("forged", "fake", "invalid", "fraud", "authentic"))


def test_student_without_government_records_is_no_linked(client, monkeypatch):
    post(client)  # first request creates the aadhaar_links table
    conn = db.get_conn()
    conn.execute("INSERT INTO students VALUES ('DEMO-STU-900','Nora Demo','Demo Program')")
    conn.execute("INSERT INTO aadhaar_links VALUES (?,?,?)",
                 (aad._digest("000000001900"), "1900", "DEMO-STU-900"))
    assert conn.execute("SELECT COUNT(*) FROM government_records WHERE student_id='DEMO-STU-900'").fetchone()[0] == 0
    conn.close()
    monkeypatch.setattr(ocr, "extract_fields",
                        lambda d, filename=None: {"aadhaar_number": "000000001900"})
    b = post(client).json()
    assert b["status"] == "NO_LINKED_DOCUMENTS_FOUND" and b["records"] == []
    assert b["student"] is None  # neutral outcome does not disclose the student


def test_ocr_crash_is_processing_failed_not_a_verdict(client):
    r = post(client, "ocrfail.png")
    b = r.json()
    assert r.status_code == 503 and b["status"] == "PROCESSING_FAILED" and b["reason"] == "OCR_ENGINE_ERROR"
    assert "NO_LINKED" not in r.text and "FOUND" not in b["status"].replace("PROCESSING_FAILED", "")


def test_number_not_found_is_processing_failed(client):
    b = post(client, "nonumber.png").json()
    assert b["status"] == "PROCESSING_FAILED" and b["reason"] == "AADHAAR_NUMBER_NOT_EXTRACTED"


def test_malformed_number_is_processing_failed_and_not_echoed(client, monkeypatch):
    monkeypatch.setattr(ocr, "extract_fields", lambda d, filename=None: {"aadhaar_number": "123-SECRET"})
    r = post(client)
    assert r.json()["reason"] == "AADHAAR_NUMBER_MALFORMED" and "SECRET" not in r.text


def test_unexpected_ocr_exception_does_not_leak_text(client, monkeypatch):
    def boom(d, filename=None): raise RuntimeError("leaked 000000001001")
    monkeypatch.setattr(ocr, "extract_fields", boom)
    r = post(client)
    assert r.status_code == 503 and r.json()["reason"] == "OCR_UNEXPECTED_ERROR" and FULL not in r.text


def test_database_failure_is_processing_failed(client, monkeypatch):
    def bad(conn, number): raise sqlite3.OperationalError("disk I/O error")
    monkeypatch.setattr(aad, "_lookup", bad)
    r = post(client)
    assert r.status_code == 503 and r.json() == {
        "status": "PROCESSING_FAILED", "reason": "DATABASE_ERROR",
        "message": "Could not complete the lookup (technical error). No outcome was produced.",
        "synthetic_data": True}


@pytest.mark.parametrize("data,ctype,code", [
    (b"", "image/png", 400),
    (b"just text, not an image", "text/plain", 415),
    (b"MZ\x90\x00" + b"0" * 50, "image/png", 415),          # wrong magic despite claimed type
    (PNG + b"x" * (5 * 1024 * 1024), "image/png", 413),
])
def test_file_validation(client, data, ctype, code):
    assert post(client, data=data, ctype=ctype).status_code == code


def test_missing_file_is_422(client):
    assert client.post("/aadhaar/link").status_code == 422


def test_jpeg_and_pdf_accepted(client):
    assert post(client, "a.jpg", b"\xff\xd8\xff\xe0" + b"0" * 20, "image/jpeg").status_code == 200
    assert post(client, "a.pdf", b"%PDF-1.4 " + b"0" * 20, "application/pdf").status_code == 200


def test_number_never_appears_in_logs(client, caplog):
    caplog.set_level(logging.DEBUG)
    for name in ("card.png", "unregistered.png", "ocrfail.png", "nonumber.png"):
        post(client, name)
    assert FULL not in caplog.text and SPACED not in caplog.text
    assert "000000009999" not in caplog.text and "1001" not in caplog.text


def test_number_not_stored_in_plaintext_and_file_not_persisted(client, tmp_path):
    post(client)
    raw = Path(tmp_path / "t.db").read_bytes()
    assert FULL.encode() not in raw
    up = tmp_path / "up"
    assert not any(up.iterdir()) if up.exists() else True


def test_aadhaar_numbers_not_exposed_by_government_records_endpoint(client):
    post(client)
    assert FULL not in client.get("/government-records").text


def test_no_blockchain_code_in_aadhaar_or_ocr_modules():
    for f in ("ocr.py", "routers/aadhaar.py"):
        code = Path(f).read_text()
        body = "\n".join(l for l in code.splitlines() if not l.lstrip().startswith(("#", '"""')))
        assert not re.search(r"^\s*(import|from)\s+(web3|eth_|brownie)", body, re.M), f
        assert not re.search(r"blockchain_service|send_transaction|contract\.functions", body), f


def test_demo_numbers_cannot_be_real_aadhaar():
    for n in aad.DEMO_LINKS:
        assert n.startswith("0000")   # real numbers never start with 0 or 1
    assert ocr.DEMO_NUMBER_LINKED.startswith("0000") and ocr.DEMO_NUMBER_UNREGISTERED.startswith("0000")


def test_mask():
    assert aad.mask("000000001001") == "XXXX XXXX 1001"


# ---- ocr.extract_fields: the function Shregna reuses ----
def test_extract_fields_contract_and_determinism():
    a = ocr.extract_fields(PNG, filename="x.png")
    assert set(a) == {"aadhaar_number", "name", "ocr_confidence", "engine"}
    assert a == ocr.extract_fields(PNG, filename="x.png") and a["engine"] == "mock"
    assert 0.0 <= a["ocr_confidence"] <= 1.0


def test_extract_fields_accepts_bytes_filelike_and_path(tmp_path):
    p = tmp_path / "card.png"; p.write_bytes(PNG)
    assert ocr.extract_fields(PNG)["aadhaar_number"] == ocr.DEMO_NUMBER_LINKED
    assert ocr.extract_fields(io.BytesIO(PNG))["aadhaar_number"] == ocr.DEMO_NUMBER_LINKED
    assert ocr.extract_fields(p)["aadhaar_number"] == ocr.DEMO_NUMBER_LINKED
    assert ocr.extract_fields(PNG, filename="unregistered.png")["aadhaar_number"] == ocr.DEMO_NUMBER_UNREGISTERED


def test_extract_fields_errors_carry_codes_only():
    for bad, code in ((b"", "EMPTY_INPUT"), (Path("/no/such/file.png"), "INPUT_UNREADABLE")):
        with pytest.raises(ocr.OCRError) as e:
            ocr.extract_fields(bad)
        assert e.value.code == code and str(e.value) == code
    with pytest.raises(ocr.OCRError):
        ocr.extract_fields(PNG, filename="ocrfail.png")


def test_static_page_served_with_badge(client):
    html = client.get("/static/aadhaar.html").text
    assert "Synthetic / Demo Data" in html and "/aadhaar/link" in html
