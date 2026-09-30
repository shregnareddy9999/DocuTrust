"""Student, government-record and marksheet-history operations (Task 1 core data layer).

Everything here is synthetic demo data (AGENTS.md Rule 7). Other tasks (Aadhaar linkage, marksheet
AI) should call these functions rather than writing their own queries.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.domain.academic_summary import summarize
from app.models.government_record import GovernmentRecord
from app.models.marksheet import Marksheet
from app.models.student import Student
from app.models.student_document import StudentDocument
from app.repositories import (
    documents_repo,
    government_record_repo,
    marksheet_repo,
    student_document_repo,
    student_repo,
)

SOURCE_LABEL = "synthetic-demo"
# Demo-only obfuscation so the raw number is never stored; NOT a production-grade scheme.
_AADHAAR_DEMO_PREFIX = "docutrust-demo-aadhaar-v1:"


class StudentNotFoundError(ValueError):
    pass


class DocumentLinkError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_aadhaar(number: str) -> str:
    digits = "".join(ch for ch in str(number) if ch.isdigit())
    return hashlib.sha256((_AADHAAR_DEMO_PREFIX + digits).encode()).hexdigest()


def mask_aadhaar(last4: str | None) -> str | None:
    return f"XXXX XXXX {last4}" if last4 else None


def _iso_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    text = value.isoformat()
    return text if text.endswith("Z") or "+" in text else text + "Z"


def _require_student(session: Session, student_ref: str) -> Student:
    student = student_repo.get_by_ref(session, student_ref)
    if student is None:
        raise StudentNotFoundError(student_ref)
    return student


def create_student(session: Session, student_ref: str, display_name: str, aadhaar_number: str | None = None) -> Student:
    digits = "".join(ch for ch in (aadhaar_number or "") if ch.isdigit())
    student = Student(
        student_ref=student_ref, display_name=display_name,
        aadhaar_hash=hash_aadhaar(digits) if digits else None,
        aadhaar_last4=digits[-4:] if digits else None,
        source_label=SOURCE_LABEL, created_at=_now(),
    )
    student_repo.create(session, student)
    session.commit()
    return student


def find_student_by_aadhaar(session: Session, aadhaar_number: str) -> str | None:
    """Returns student_ref or None. None is the neutral 'no record' outcome, never a fraud signal."""
    student = student_repo.get_by_aadhaar_hash(session, hash_aadhaar(aadhaar_number))
    return student.student_ref if student else None


def list_students(session: Session) -> list[dict]:
    return [
        {"student_ref": s.student_ref, "display_name": s.display_name,
         "aadhaar_masked": mask_aadhaar(s.aadhaar_last4), "source_label": s.source_label}
        for s in student_repo.list_all(session)
    ]


def link_document(session: Session, student_ref: str, document_id: str) -> dict:
    student = _require_student(session, student_ref)
    document = documents_repo.get_by_id(session, document_id)
    if document is None:
        raise DocumentLinkError("DOCUMENT_NOT_FOUND", "Document not found")
    if student_document_repo.get(session, student.id, document_id) is not None:
        raise DocumentLinkError("DOCUMENT_ALREADY_LINKED", "Document is already linked to this student")
    link = StudentDocument(
        student_id=student.id, document_id=document_id, linked_at=_now(),
        version=student_document_repo.next_version(session, student.id, document.category),
    )
    student_document_repo.create(session, link)
    session.commit()
    return _document_view(link, document)


def _document_view(link: StudentDocument, document) -> dict:
    return {
        "document_id": document.id, "category": document.category.value,
        "processing_state": document.processing_state.value, "version": link.version,
        "uploaded_at": _iso_z(document.uploaded_at), "linked_at": _iso_z(link.linked_at),
    }


def list_student_documents(session: Session, student_ref: str) -> list[dict]:
    student = _require_student(session, student_ref)
    return [_document_view(link, doc) for link, doc in student_document_repo.list_for_student(session, student.id)]


def add_government_record(session: Session, student_ref: str, record_type: str, fields: dict) -> dict:
    student = _require_student(session, student_ref)
    record = GovernmentRecord(
        student_id=student.id, record_type=record_type, fields_json=json.dumps(fields),
        is_synthetic=True, source_label=SOURCE_LABEL, created_at=_now(),
    )
    government_record_repo.create(session, record)
    session.commit()
    return _record_view(record)


def _record_view(record: GovernmentRecord) -> dict:
    return {"id": record.id, "record_type": record.record_type, "fields": json.loads(record.fields_json),
            "is_synthetic": record.is_synthetic, "source_label": record.source_label,
            "created_at": _iso_z(record.created_at)}


def get_government_records(session: Session, student_ref: str) -> dict:
    """An empty list is NO_LINKED_DOCUMENTS_FOUND: an absent reference record, not evidence of a fake."""
    student = _require_student(session, student_ref)
    records = [_record_view(r) for r in government_record_repo.list_for_student(session, student.id)]
    return {"student_ref": student_ref, "status": "FOUND" if records else "NO_LINKED_DOCUMENTS_FOUND",
            "source_label": SOURCE_LABEL, "records": records}


def add_marksheet(session: Session, student_ref: str, semester: int, subjects: dict,
                  total: float | None = None, cgpa: float | None = None) -> dict:
    """Always inserts a new row; earlier marksheets are never overwritten."""
    student = _require_student(session, student_ref)
    if total is None:
        total = float(sum(v for v in subjects.values() if isinstance(v, (int, float))))
    row = Marksheet(student_id=student.id, semester=semester, subjects_json=json.dumps(subjects),
                    total=total, cgpa=cgpa, source_label=SOURCE_LABEL, uploaded_at=_now())
    marksheet_repo.create(session, row)
    session.commit()
    return _marksheet_view(row)


def _marksheet_view(row: Marksheet) -> dict:
    return {"id": row.id, "semester": row.semester, "subjects": json.loads(row.subjects_json),
            "total": row.total, "cgpa": row.cgpa, "uploaded_at": _iso_z(row.uploaded_at)}


def get_marksheet_history(session: Session, student_ref: str) -> dict:
    student = _require_student(session, student_ref)
    history = [_marksheet_view(r) for r in marksheet_repo.list_for_student(session, student.id)]
    return {"student_ref": student_ref, "source_label": SOURCE_LABEL, "history": history,
            "summary": {**summarize(history), "derived": True,
                        "note": "Derived from the stored records above; it does not change them."}}
