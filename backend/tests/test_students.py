"""Core Task 1 tests: students, document links, government records, marksheet history."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy.exc import OperationalError

from app.domain.academic_summary import LIMITED_HISTORY_NOTE, summarize
from app.models import Document, DocumentCategory, ProcessingState
from app.repositories import documents_repo
from app.services import student_service as svc


def _session():
    from app import db
    return db.SessionLocal()


def _png() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (64, 64), color=(255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _make_document(session, category=DocumentCategory.ACADEMIC_CERTIFICATE) -> str:
    doc = Document(category=category, original_filename="x.png", storage_key="k", sha256="0" * 64,
                   mime_type="image/png", byte_size=1, page_count=1,
                   processing_state=ProcessingState.UPLOADED, uploaded_at=datetime.now(timezone.utc))
    documents_repo.create(session, doc)
    session.commit()
    return doc.id


@pytest.fixture
def seeded(client):
    s = _session()
    svc.create_student(s, "DEMO-STU-101", "Aarav Demo", "0000 0000 0001")
    svc.create_student(s, "DEMO-STU-103", "Kabir Demo", "0000 0000 0003")
    svc.add_government_record(s, "DEMO-STU-101", "Caste Certificate (demo)", {"issuer": "Demo Office"})
    for sem, cg in ((1, 6.8), (2, 7.3), (3, 7.9)):
        svc.add_marksheet(s, "DEMO-STU-101", sem, {"Mathematics": 60 + sem * 5, "Physics": 70 - sem}, cgpa=cg)
    yield s
    s.close()


# ---- students / privacy ----
def test_students_list_masks_aadhaar_and_hides_hash(client, seeded):
    body = client.get("/api/v1/students").json()
    assert [s["student_ref"] for s in body] == ["DEMO-STU-101", "DEMO-STU-103"]
    assert body[0]["aadhaar_masked"] == "XXXX XXXX 0001"
    assert all("aadhaar_hash" not in s and "0000 0000 0001" not in str(s) for s in body)
    assert all(s["source_label"] == "synthetic-demo" for s in body)


def test_find_student_by_aadhaar_hit_and_neutral_miss(client, seeded):
    assert svc.find_student_by_aadhaar(seeded, "0000 0000 0001") == "DEMO-STU-101"
    assert svc.find_student_by_aadhaar(seeded, "000000000001") == "DEMO-STU-101"
    assert svc.find_student_by_aadhaar(seeded, "0000 0000 0099") is None


def test_unknown_student_is_404_with_error_envelope(client, seeded):
    r = client.get("/api/v1/students/NOPE/documents")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "STUDENT_NOT_FOUND", "message": "Student not found", "details": {}}}


# ---- document links + history ----
def test_link_documents_creates_versions_and_keeps_history(client, seeded):
    d1, d2 = _make_document(seeded), _make_document(seeded)
    r1 = client.post("/api/v1/students/DEMO-STU-101/documents", json={"document_id": d1})
    r2 = client.post("/api/v1/students/DEMO-STU-101/documents", json={"document_id": d2})
    assert (r1.status_code, r1.json()["version"]) == (201, 1)
    assert r2.json()["version"] == 2
    listed = client.get("/api/v1/students/DEMO-STU-101/documents").json()
    assert {d["document_id"] for d in listed} == {d1, d2}          # old version still present
    assert client.get("/api/v1/students/DEMO-STU-103/documents").json() == []


def test_link_errors(client, seeded):
    d1 = _make_document(seeded)
    assert client.post("/api/v1/students/DEMO-STU-101/documents", json={"document_id": "missing"}).status_code == 404
    client.post("/api/v1/students/DEMO-STU-101/documents", json={"document_id": d1})
    dup = client.post("/api/v1/students/DEMO-STU-101/documents", json={"document_id": d1})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DOCUMENT_ALREADY_LINKED"


def test_upload_then_link_end_to_end(client, seeded):
    up = client.post("/api/v1/documents", files={"file": ("a.png", _png(), "image/png")},
                     data={"category": "academic_certificate"})
    assert up.status_code == 201
    r = client.post("/api/v1/students/DEMO-STU-101/documents", json={"document_id": up.json()["document_id"]})
    assert r.status_code == 201 and r.json()["category"] == "academic_certificate"


# ---- government records ----
def test_government_records_found_and_neutral_no_record(client, seeded):
    found = client.get("/api/v1/students/DEMO-STU-101/government-records").json()
    assert found["status"] == "FOUND" and found["source_label"] == "synthetic-demo"
    assert found["records"][0]["is_synthetic"] is True
    none = client.get("/api/v1/students/DEMO-STU-103/government-records").json()
    assert none["status"] == "NO_LINKED_DOCUMENTS_FOUND" and none["records"] == []
    text = str(none).lower()
    assert "fraud" not in text and "forged" not in text


def test_create_government_record(client, seeded):
    r = client.post("/api/v1/students/DEMO-STU-103/government-records",
                    json={"record_type": "Domicile (demo)", "fields": {"issuer": "Demo"}})
    assert r.status_code == 201 and r.json()["is_synthetic"] is True
    assert client.get("/api/v1/students/DEMO-STU-103/government-records").json()["status"] == "FOUND"


# ---- marksheets ----
def test_marksheet_history_chronological_with_derived_summary(client, seeded):
    body = client.get("/api/v1/students/DEMO-STU-101/marksheets").json()
    assert [m["semester"] for m in body["history"]] == [1, 2, 3]
    assert body["summary"]["cgpa_trend"] == "improving" and body["summary"]["derived"] is True


def test_new_marksheet_never_overwrites_history(client, seeded):
    before = client.get("/api/v1/students/DEMO-STU-101/marksheets").json()["history"]
    r = client.post("/api/v1/students/DEMO-STU-101/marksheets",
                    json={"semester": 4, "subjects": {"Mathematics": 90}, "cgpa": 8.4})
    assert r.status_code == 201
    after = client.get("/api/v1/students/DEMO-STU-101/marksheets").json()["history"]
    assert len(after) == len(before) + 1 and after[:3] == before


def test_limited_history_is_stated(client, seeded):
    body = client.get("/api/v1/students/DEMO-STU-103/marksheets").json()
    assert body["history"] == [] and body["summary"]["available"] is False
    svc.add_marksheet(seeded, "DEMO-STU-103", 1, {"Mathematics": 60}, cgpa=6.1)
    body = client.get("/api/v1/students/DEMO-STU-103/marksheets").json()
    assert LIMITED_HISTORY_NOTE in body["summary"]["points"] and body["summary"]["limited_history"] is True


def test_summary_is_deterministic_and_grounded():
    h = [{"semester": 1, "subjects": {"A": 50, "B": 90}, "cgpa": 7.0},
         {"semester": 2, "subjects": {"A": 55, "B": 80}, "cgpa": 6.5}]
    assert summarize(h) == summarize(h)
    out = summarize(h)
    assert out["cgpa_trend"] == "declining"
    joined = " ".join(out["points"])
    assert "B (80)" in joined and "A (55)" in joined and "Chemistry" not in joined


def test_marksheet_validation(client, seeded):
    assert client.post("/api/v1/students/DEMO-STU-101/marksheets",
                       json={"semester": 0, "subjects": {}}).status_code == 422


# ---- failure isolation ----
def test_database_failure_is_processing_failed_not_a_verdict(client, monkeypatch):
    def boom(*a, **k):
        raise OperationalError("SELECT", {}, Exception("db down"))
    monkeypatch.setattr(svc.student_repo, "list_all", boom)
    r = client.get("/api/v1/students")
    assert r.status_code == 503
    err = r.json()["error"]
    assert err["code"] == "PROCESSING_FAILED" and "not a verification result" in err["message"]
    assert "db down" not in err["message"]


def test_seed_is_idempotent(client, monkeypatch):
    from app.fixtures import seed_students
    created, unchanged = seed_students.seed()
    assert len(created) == 3 and unchanged == []
    created2, unchanged2 = seed_students.seed()
    assert created2 == [] and len(unchanged2) == 3
    g = client.get("/api/v1/students/DEMO-STU-103/government-records").json()
    assert g["status"] == "NO_LINKED_DOCUMENTS_FOUND"
    assert len(client.get("/api/v1/students/DEMO-STU-102/marksheets").json()["history"]) == 4
