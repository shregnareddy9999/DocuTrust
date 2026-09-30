"""Queries for students."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.student import Student


def create(session: Session, student: Student) -> Student:
    session.add(student)
    session.flush()
    return student


def get_by_ref(session: Session, student_ref: str) -> Student | None:
    return session.scalars(select(Student).where(Student.student_ref == student_ref)).first()


def get_by_aadhaar_hash(session: Session, aadhaar_hash: str) -> Student | None:
    return session.scalars(select(Student).where(Student.aadhaar_hash == aadhaar_hash)).first()


def list_all(session: Session) -> list[Student]:
    return list(session.scalars(select(Student).order_by(Student.student_ref)).all())
