"""
Tests for `app.fixtures.seed_registry`, per Task 03 §8 Automated Tests.

Runs against an isolated temp-file SQLite DB per test using Task 02's
`db_session` fixture from `tests/conftest.py`.

Expected literal values are duplicated here from `docs/category-schemas.md`
rather than imported from `fixture_data.FIXTURES`, per the task's explicit
instruction: "assert against the literal expected dict, not the same
constant the seeder used, or the test proves nothing."
"""

from __future__ import annotations

import json
import re

import pytest

from app.fixtures import generate_samples, seed_registry
from app.models.document import DocumentCategory
from app.models.registry import RegistryRecord
from app.repositories import registry_repo

# Copied independently from docs/category-schemas.md -- do NOT import
# fixture_data here; see module docstring.
EXPECTED_FIELDS = {
    "academic_certificate": {
        "student_name": "Aarav Demo",
        "institution_name": "Example Technical Institute",
        "student_id": "DEMO-STU-001",
        "course_name": "B.Tech CSE",
        "semester_or_year": "5",
        "certificate_or_marksheet_id": "DEMO-MARK-001",
    },
    "institutional_id": {
        "holder_name": "Priya Demo",
        "institution_name": "Example Technical Institute",
        "id_number": "DEMO-ID-001",
        "designation_or_role": "Student",
    },
    "pan_like_demo": {
        "holder_name": "Rohan Demo",
        "demo_pan_code": "DP1234",
        "date_of_birth": "1999-01-15",
    },
    "government_certificate": {
        "holder_name": "Meera Demo",
        "certificate_type_label": "Demo Residence Certificate",
        "certificate_number": "DEMO-GOV-001",
        "issuing_authority_label": "Example Demo Authority",
    },
}

REAL_PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def _all_records(session):
    return session.query(RegistryRecord).all()


def test_fresh_database_creates_exactly_four_active_records(db_session):
    summary = seed_registry.seed(db_session)

    assert len(summary.created) == 4
    assert summary.unchanged == []
    assert summary.divergent == []

    records = _all_records(db_session)
    assert len(records) == 4
    assert all(r.active is True for r in records)


def test_running_twice_is_idempotent(db_session):
    seed_registry.seed(db_session)
    summary_second_run = seed_registry.seed(db_session)

    assert len(summary_second_run.created) == 0
    assert len(summary_second_run.unchanged) == 4
    assert len(summary_second_run.divergent) == 0

    records = _all_records(db_session)
    assert len(records) == 4  # nothing duplicated


def test_fields_match_category_schemas_exactly(db_session):
    seed_registry.seed(db_session)

    records = {r.category.value: r for r in _all_records(db_session)}
    for category, expected in EXPECTED_FIELDS.items():
        actual = json.loads(records[category].fields_json)
        assert actual == expected, f"{category} fields_json diverges from category-schemas.md"


def test_source_label_and_active_on_every_record(db_session):
    seed_registry.seed(db_session)

    for record in _all_records(db_session):
        assert record.source_label == "synthetic-demo"
        assert record.active is True


def test_every_synthetic_record_key_starts_with_demo(db_session):
    seed_registry.seed(db_session)

    for record in _all_records(db_session):
        assert record.synthetic_record_key.startswith("DEMO-")


def test_demo_pan_code_is_six_chars_and_not_a_real_pan(db_session):
    seed_registry.seed(db_session)

    pan_record = (
        db_session.query(RegistryRecord)
        .filter_by(category=DocumentCategory.PAN_LIKE_DEMO)
        .one()
    )
    demo_pan_code = json.loads(pan_record.fields_json)["demo_pan_code"]

    assert len(demo_pan_code) == 6
    assert not REAL_PAN_PATTERN.match(demo_pan_code)


def test_divergent_record_is_reported_and_not_overwritten(db_session):
    seed_registry.seed(db_session)

    # Simulate a hand-edited record, as if someone touched the DB directly.
    tampered = (
        db_session.query(RegistryRecord)
        .filter_by(category=DocumentCategory.GOVERNMENT_CERTIFICATE)
        .one()
    )
    tampered.fields_json = json.dumps({"tampered": True})
    db_session.commit()

    summary = seed_registry.seed(db_session)

    assert len(summary.divergent) == 1
    assert summary.divergent[0][0] == "government_certificate"
    assert summary.ok is False

    # Confirm it truly was not overwritten.
    reloaded = (
        db_session.query(RegistryRecord)
        .filter_by(category=DocumentCategory.GOVERNMENT_CERTIFICATE)
        .one()
    )
    assert json.loads(reloaded.fields_json) == {"tampered": True}


def test_sample_font_is_truetype_not_bitmap_default():
    from PIL import ImageFont

    font = generate_samples._font(22)
    assert isinstance(font, ImageFont.FreeTypeFont)


def test_all_eleven_sample_documents_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_samples, "OUTPUT_DIR", tmp_path)
    generate_samples.main()

    expected_files = {
        "academic_certificate_match.png",
        "academic_certificate_mismatch.png",
        "academic_certificate_unregistered.png",
        "academic_certificate_degraded.png",
        "institutional_id_match.png",
        "institutional_id_mismatch.png",
        "pan_like_demo_match.png",
        "pan_like_demo_mismatch.png",
        "government_certificate_match.png",
        "government_certificate_mismatch.png",
        "academic_certificate_match.pdf",
    }
    actual_files = {p.name for p in tmp_path.iterdir()}
    assert expected_files == actual_files