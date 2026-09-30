"""Student, government-record and marksheet-history endpoints (Core Task 1).

A database failure is a technical failure: it is returned as PROCESSING_FAILED (503),
never as a document verdict.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import student_service as svc

router = APIRouter()


def _err(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code,
                         detail={"error": {"code": code, "message": message, "details": {}}})


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except svc.StudentNotFoundError:
        raise _err(404, "STUDENT_NOT_FOUND", "Student not found") from None
    except svc.DocumentLinkError as e:
        raise _err(404 if e.code == "DOCUMENT_NOT_FOUND" else 409, e.code, e.message) from None
    except SQLAlchemyError:
        raise _err(503, "PROCESSING_FAILED",
                   "Database unavailable. This is a technical failure, not a verification result.") from None


class LinkDocumentIn(BaseModel):
    document_id: str


class GovernmentRecordIn(BaseModel):
    record_type: str = Field(min_length=1)
    fields: dict


class MarksheetIn(BaseModel):
    semester: int = Field(ge=1)
    subjects: dict[str, float]
    total: float | None = None
    cgpa: float | None = None


@router.get("/students")
def list_students(db: Session = Depends(get_db)):
    return _run(svc.list_students, db)


@router.get("/students/{student_ref}/documents")
def student_documents(student_ref: str, db: Session = Depends(get_db)):
    return _run(svc.list_student_documents, db, student_ref)


@router.post("/students/{student_ref}/documents", status_code=status.HTTP_201_CREATED)
def link_document(student_ref: str, body: LinkDocumentIn, db: Session = Depends(get_db)):
    return _run(svc.link_document, db, student_ref, body.document_id)


@router.get("/students/{student_ref}/government-records")
def government_records(student_ref: str, db: Session = Depends(get_db)):
    return _run(svc.get_government_records, db, student_ref)


@router.post("/students/{student_ref}/government-records", status_code=status.HTTP_201_CREATED)
def add_government_record(student_ref: str, body: GovernmentRecordIn, db: Session = Depends(get_db)):
    return _run(svc.add_government_record, db, student_ref, body.record_type, body.fields)


@router.get("/students/{student_ref}/marksheets")
def marksheet_history(student_ref: str, db: Session = Depends(get_db)):
    return _run(svc.get_marksheet_history, db, student_ref)


@router.post("/students/{student_ref}/marksheets", status_code=status.HTTP_201_CREATED)
def add_marksheet(student_ref: str, body: MarksheetIn, db: Session = Depends(get_db)):
    return _run(svc.add_marksheet, db, student_ref, body.semester, body.subjects, body.total, body.cgpa)
