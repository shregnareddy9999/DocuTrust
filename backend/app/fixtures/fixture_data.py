"""
Single source of truth for the four locked synthetic registry fixtures.

Values are copied character-for-character from `docs/category-schemas.md`.
Both `seed_registry.py` and `generate_samples.py` import this module — do not
hand-copy these values anywhere else. Task 07's tests and the demo depend on
these being byte-for-byte identical wherever they are used.

Do not edit these values without project-lead approval (AGENTS.md §5 — this
file mirrors a locked contract, `category-schemas.md`).
"""

from __future__ import annotations

# registry_records.source_label is always this value (data-model.md, AGENTS.md Rule 7).
SOURCE_LABEL = "synthetic-demo"

# One entry per category. `synthetic_record_key` is the identifying key used
# both for idempotent seeding (category, synthetic_record_key) and for the
# "unregistered" sample document, which deliberately uses a key that is NOT
# in this dict's fields.
FIXTURES: dict[str, dict] = {
    "academic_certificate": {
        "synthetic_record_key": "DEMO-STU-001",
        "fields": {
            "student_name": "Aarav Demo",
            "institution_name": "Example Technical Institute",
            "student_id": "DEMO-STU-001",
            "course_name": "B.Tech CSE",
            "semester_or_year": "5",
            "certificate_or_marksheet_id": "DEMO-MARK-001",
        },
    },
    "institutional_id": {
        "synthetic_record_key": "DEMO-ID-001",
        "fields": {
            "holder_name": "Priya Demo",
            "institution_name": "Example Technical Institute",
            "id_number": "DEMO-ID-001",
            "designation_or_role": "Student",
        },
    },
    "pan_like_demo": {
        "synthetic_record_key": "DEMO-PAN-001",
        "fields": {
            "holder_name": "Rohan Demo",
            "demo_pan_code": "DP1234",
            "date_of_birth": "1999-01-15",
        },
    },
    "government_certificate": {
        "synthetic_record_key": "DEMO-GOV-001",
        "fields": {
            "holder_name": "Meera Demo",
            "certificate_type_label": "Demo Residence Certificate",
            "certificate_number": "DEMO-GOV-001",
            "issuing_authority_label": "Example Demo Authority",
        },
    },
}
