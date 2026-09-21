"""Tests for Task 06 category-specific field extraction."""

from dataclasses import dataclass

import pytest

from app.domain.schemas import SCHEMA_REGISTRY, get_schema
from app.services.extraction_service import map_ocr_to_fields


@dataclass
class FakeRegion:
    text: str
    confidence: float
    bbox: tuple[int, int, int, int] = (0, 0, 100, 20)
    page: int = 1


@dataclass
class FakeOcrResult:
    text: str
    regions: list[FakeRegion]
    mean_confidence: float | None = 0.9
    engine_name: str = "fake"
    engine_version: str = "1.0"
    warnings: list[str] | None = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def academic_ocr():
    return FakeOcrResult(
        text=(
            "Student Name: Aarav Demo "
            "Institution Name: Demo University "
            "Student ID: STU001 "
            "Course Name: BCA AI "
            "Semester: 2 "
            "Certificate ID: CERT001 "
            "Issue Date: 2026-07-15"
        ),
        regions=[
            FakeRegion("Student Name: Aarav Demo", 0.94),
            FakeRegion("Institution Name: Demo University", 0.93),
            FakeRegion("Student ID: STU001", 0.92),
            FakeRegion("Course Name: BCA AI", 0.91),
            FakeRegion("Semester: 2", 0.90),
            FakeRegion("Certificate ID: CERT001", 0.89),
            FakeRegion("Issue Date: 2026-07-15", 0.88),
        ],
    )


def test_clean_academic_certificate_extracts_fields():
    result, warnings = map_ocr_to_fields(
        academic_ocr(),
        "academic_certificate",
    )

    assert result["student_name"]["value"] == "Aarav Demo"
    assert result["institution_name"]["value"] == "Demo University"
    assert result["student_id"]["value"] == "STU001"
    assert result["course_name"]["value"] == "BCA AI"
    assert result["semester_or_year"]["value"] == "2"
    assert result["certificate_or_marksheet_id"]["value"] == "CERT001"
    assert result["issue_date"]["value"] == "2026-07-15"

    assert result["student_name"]["confidence"] == 0.94
    assert result["student_name"]["source"] == "ocr"

    assert "unrecognized_date_format:issue_date" not in warnings


@pytest.mark.parametrize("category", SCHEMA_REGISTRY.keys())
def test_every_category_returns_all_schema_fields(category):
    result, _ = map_ocr_to_fields(
        FakeOcrResult(text="", regions=[]),
        category,
    )

    expected = {
        field.name
        for field in get_schema(category)
    }

    assert set(result.keys()) == expected


def test_missing_required_field_is_null_and_warned():
    ocr = academic_ocr()

    ocr.regions = [
        region
        for region in ocr.regions
        if "Certificate ID" not in region.text
    ]

    result, warnings = map_ocr_to_fields(
        ocr,
        "academic_certificate",
    )

    assert result["certificate_or_marksheet_id"]["value"] is None
    assert result["certificate_or_marksheet_id"]["confidence"] is None
    assert "missing_field:certificate_or_marksheet_id" in warnings


def test_empty_ocr_warns_for_every_required_field():
    result, warnings = map_ocr_to_fields(
        FakeOcrResult(text="", regions=[]),
        "academic_certificate",
    )

    required = [
        field.name
        for field in get_schema("academic_certificate")
        if field.required
    ]

    for name in required:
        assert result[name]["value"] is None
        assert f"missing_field:{name}" in warnings


def test_existing_warnings_are_preserved():
    ocr = FakeOcrResult(
        text="",
        regions=[],
        warnings=["ocr_warning"],
    )

    _, warnings = map_ocr_to_fields(
        ocr,
        "academic_certificate",
    )

    assert "ocr_warning" in warnings


def test_invalid_date_preserves_value_and_warns():
    ocr = FakeOcrResult(
        text="Issue Date: 15/07/2026",
        regions=[
            FakeRegion("Issue Date: 15/07/2026", 0.87),
        ],
    )

    result, warnings = map_ocr_to_fields(
        ocr,
        "academic_certificate",
    )

    assert result["issue_date"]["value"] == "15/07/2026"
    assert result["issue_date"]["confidence"] == 0.87
    assert result["issue_date"]["source"] == "ocr"
    assert "unrecognized_date_format:issue_date" in warnings


def test_valid_date_is_accepted():
    ocr = FakeOcrResult(
        text="Issue Date: 2026-07-15",
        regions=[
            FakeRegion("Issue Date: 2026-07-15", 0.91),
        ],
    )

    result, warnings = map_ocr_to_fields(
        ocr,
        "academic_certificate",
    )

    assert result["issue_date"]["value"] == "2026-07-15"
    assert "unrecognized_date_format:issue_date" not in warnings


def test_real_pan_shape_is_rejected():
    ocr = FakeOcrResult(
        text="Demo PAN Code: ABCDE1234F",
        regions=[
            FakeRegion("Demo PAN Code: ABCDE1234F", 0.95),
        ],
    )

    result, warnings = map_ocr_to_fields(
        ocr,
        "pan_like_demo",
    )

    assert result["demo_pan_code"]["value"] == "ABCDE1234F"
    assert "invalid_format:demo_pan_code" in warnings


def test_synthetic_six_character_code_is_accepted():
    ocr = FakeOcrResult(
        text="Demo PAN Code: DP1234",
        regions=[
            FakeRegion("Demo PAN Code: DP1234", 0.95),
        ],
    )

    result, warnings = map_ocr_to_fields(
        ocr,
        "pan_like_demo",
    )

    assert result["demo_pan_code"]["value"] == "DP1234"
    assert "invalid_format:demo_pan_code" not in warnings


def test_never_invents_missing_values():
    ocr = FakeOcrResult(
        text="Student Name: Aarav Demo",
        regions=[
            FakeRegion("Student Name: Aarav Demo", 0.94),
        ],
    )

    result, warnings = map_ocr_to_fields(
        ocr,
        "academic_certificate",
    )

    assert result["student_name"]["value"] == "Aarav Demo"

    for name, field in result.items():
        if name != "student_name":
            assert field["value"] is None

    assert "missing_field:institution_name" in warnings
    assert "missing_field:student_id" in warnings


def test_confidence_is_not_modified():
    ocr = FakeOcrResult(
        text="Student Name: Aarav Demo",
        regions=[
            FakeRegion("Student Name: Aarav Demo", 0.731),
        ],
    )

    result, _ = map_ocr_to_fields(
        ocr,
        "academic_certificate",
    )

    assert result["student_name"]["confidence"] == 0.731


def test_schema_registry_contains_exact_four_categories():
    assert set(SCHEMA_REGISTRY) == {
        "academic_certificate",
        "institutional_id",
        "pan_like_demo",
        "government_certificate",
    }


def test_unknown_category_is_rejected():
    with pytest.raises(ValueError):
        get_schema("unknown_category")
