"""
Idempotently seeds synthetic demo students, government records and marksheet history.

    python -m app.fixtures.seed_students

Existing students (by student_ref) are left untouched. All identifiers are DEMO-prefixed or
obviously fictional (AGENTS.md Rule 7). The placeholder "Aadhaar" values are invalid by
construction (they start with 0), so they can never be a real number.
"""

from __future__ import annotations

import sys

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.repositories import student_repo
from app.services import student_service as svc

STUDENTS = [
    # student_ref, display_name, placeholder identifier
    ("DEMO-STU-101", "Aarav Demo", "0000 0000 0001"),
    ("DEMO-STU-102", "Diya Demo", "0000 0000 0002"),
    ("DEMO-STU-103", "Kabir Demo", "0000 0000 0003"),
]

GOV = {  # DEMO-STU-103 intentionally has none -> NO_LINKED_DOCUMENTS_FOUND
    "DEMO-STU-101": [("Caste Certificate (demo)", {"issuer": "Demo Tehsil Office", "certificate_no": "DEMO-CC-001"}),
                     ("Income Certificate (demo)", {"issuer": "Demo Revenue Dept", "income_band": "3-5 LPA"})],
    "DEMO-STU-102": [("Domicile Certificate (demo)", {"issuer": "Demo District Office", "certificate_no": "DEMO-DM-002"})],
}


def _m(a, b, c):
    return {"Mathematics": a, "Physics": b, "Programming": c}


MARKSHEETS = {
    "DEMO-STU-101": [(1, _m(68, 62, 75), 6.8), (2, _m(72, 66, 80), 7.3), (3, _m(78, 71, 85), 7.9)],
    "DEMO-STU-102": [(1, _m(85, 88, 90), 8.8), (2, _m(82, 84, 91), 8.6), (3, _m(74, 70, 88), 7.9), (4, _m(70, 66, 86), 7.5)],
    "DEMO-STU-103": [(1, _m(60, 58, 64), 6.1)],
}


def seed() -> tuple[list[str], list[str]]:
    created, unchanged = [], []
    session = db.SessionLocal()
    try:
        for ref, name, ident in STUDENTS:
            if student_repo.get_by_ref(session, ref) is not None:
                unchanged.append(ref)
                continue
            svc.create_student(session, ref, name, ident)
            for rtype, fields in GOV.get(ref, []):
                svc.add_government_record(session, ref, rtype, fields)
            for sem, subjects, cgpa in MARKSHEETS.get(ref, []):
                svc.add_marksheet(session, ref, sem, subjects, cgpa=cgpa)
            created.append(ref)
    finally:
        session.close()
    return created, unchanged


def main() -> int:
    try:
        created, unchanged = seed()
    except SQLAlchemyError as exc:
        print(f"Database unavailable: {exc.__class__.__name__}", file=sys.stderr)
        return 1
    for ref in created:
        print(f"  CREATED    {ref}")
    for ref in unchanged:
        print(f"  UNCHANGED  {ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
