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


def _row(y: int, x1: int, x2: int) -> tuple[int, int, int, int]:
    return (x1, y, x2, y + 20)


def split_column_academic():
    """Task 03-style two-column OCR: labels left, values right."""
    rows = [
        ("Student Name", "Aarav Demo", 0.94),
        ("Institution Name", "Demo University", 0.93),
        ("Student ID", "STU001", 0.92),
        ("Course", "BCA AI", 0.91),
        ("Semester / Year", "2", 0.90),
        ("Certificate / Marksheet ID", "CERT001", 0.89),
        ("Issue Date", "2026-07-15", 0.88),
    ]
    regions = []
    y = 80
    for label, value, confidence in rows:
        regions.append(FakeRegion(label, 0.99, _row(y, 60, 320)))
        regions.append(FakeRegion(value, confidence, _row(y, 400, 740)))
        y += 55
    return FakeOcrResult(text=" ".join(r.text for r in regions), regions=regions)


def test_split_column_academic_maps_value_region_confidence():
    result, warnings = map_ocr_to_fields(
        split_column_academic(),
        "academic_certificate",
    )

    assert result["student_name"]["value"] == "Aarav Demo"
    assert result["student_name"]["confidence"] == 0.94
    assert result["institution_name"]["value"] == "Demo University"
    assert result["student_id"]["value"] == "STU001"
    assert result["course_name"]["value"] == "BCA AI"
    assert result["semester_or_year"]["value"] == "2"
    assert result["certificate_or_marksheet_id"]["value"] == "CERT001"
    assert result["issue_date"]["value"] == "2026-07-15"
    assert "missing_field:student_name" not in warnings


def test_institutional_id_split_column_mapping():
    y = 80
    pairs = [
        ("Holder Name", "Priya Demo", 0.95),
        ("Institution Name", "Example Technical Institute", 0.94),
        ("ID Number", "DEMO-ID-001", 0.93),
        ("Designation / Role", "Student", 0.92),
        ("Valid Until", "2027-06-30", 0.91),
    ]
    regions = []
    for label, value, confidence in pairs:
        regions.append(FakeRegion(label, 0.99, _row(y, 60, 320)))
        regions.append(FakeRegion(value, confidence, _row(y, 400, 740)))
        y += 55
    result, warnings = map_ocr_to_fields(
        FakeOcrResult(text="", regions=regions),
        "institutional_id",
    )
    assert result["holder_name"]["value"] == "Priya Demo"
    assert result["institution_name"]["value"] == "Example Technical Institute"
    assert result["id_number"]["value"] == "DEMO-ID-001"
    assert result["designation_or_role"]["value"] == "Student"
    assert result["valid_until"]["value"] == "2027-06-30"
    assert result["designation_or_role"]["confidence"] == 0.92


def test_pan_like_split_column_mapping():
    y = 80
    pairs = [
        ("Holder Name", "Rohan Demo", 0.95),
        ("Demo PAN-Like Code", "DP1234", 0.94),
        ("Date of Birth", "1999-01-15", 0.93),
        ("Father or Guardian Name", "Suresh Demo", 0.92),
    ]
    regions = []
    for label, value, confidence in pairs:
        regions.append(FakeRegion(label, 0.99, _row(y, 60, 320)))
        regions.append(FakeRegion(value, confidence, _row(y, 400, 740)))
        y += 55
    result, warnings = map_ocr_to_fields(
        FakeOcrResult(text="", regions=regions),
        "pan_like_demo",
    )
    assert result["holder_name"]["value"] == "Rohan Demo"
    assert result["demo_pan_code"]["value"] == "DP1234"
    assert result["date_of_birth"]["value"] == "1999-01-15"
    assert result["father_or_guardian_name"]["value"] == "Suresh Demo"
    assert "invalid_format:demo_pan_code" not in warnings


def test_government_split_column_mapping():
    y = 80
    pairs = [
        ("Holder Name", "Meera Demo", 0.95),
        ("Certificate Type", "Demo Residence Certificate", 0.94),
        ("Certificate Number", "DEMO-GOV-001", 0.93),
        ("Issuing Authority", "Example Demo Authority", 0.92),
        ("Issue Date", "2026-03-01", 0.91),
    ]
    regions = []
    for label, value, confidence in pairs:
        regions.append(FakeRegion(label, 0.99, _row(y, 60, 320)))
        regions.append(FakeRegion(value, confidence, _row(y, 400, 740)))
        y += 55
    result, warnings = map_ocr_to_fields(
        FakeOcrResult(text="", regions=regions),
        "government_certificate",
    )
    assert result["holder_name"]["value"] == "Meera Demo"
    assert result["certificate_type_label"]["value"] == "Demo Residence Certificate"
    assert result["certificate_number"]["value"] == "DEMO-GOV-001"
    assert result["issuing_authority_label"]["value"] == "Example Demo Authority"
    assert result["issue_date"]["value"] == "2026-03-01"


def test_anti_invention_values_must_appear_in_source_regions():
    ocr = split_column_academic()
    result, _ = map_ocr_to_fields(ocr, "academic_certificate")
    source_texts = [region.text for region in ocr.regions]
    for field in result.values():
        if field["value"] is None:
            continue
        assert any(field["value"] in text for text in source_texts)


def test_unrecognized_date_dd_mm_yyyy_is_kept():
    ocr = FakeOcrResult(
        text="Date of Birth: 15-01-1999",
        regions=[FakeRegion("Date of Birth: 15-01-1999", 0.9)],
    )
    result, warnings = map_ocr_to_fields(ocr, "pan_like_demo")
    assert result["date_of_birth"]["value"] == "15-01-1999"
    assert "unrecognized_date_format:date_of_birth" in warnings


def test_iso_date_of_birth_is_accepted():
    ocr = FakeOcrResult(
        text="Date of Birth: 1999-01-15",
        regions=[FakeRegion("Date of Birth: 1999-01-15", 0.9)],
    )
    result, warnings = map_ocr_to_fields(ocr, "pan_like_demo")
    assert result["date_of_birth"]["value"] == "1999-01-15"
    assert "unrecognized_date_format:date_of_birth" not in warnings


def test_integer_validator_preserves_ocr_string():
    from app.domain.schemas import FieldDef
    from app.services.extraction_service import _validate

    field = FieldDef(
        name="count",
        label="Count",
        type="integer",
        required=False,
        match_field=False,
        labels=("count",),
    )
    value, warning = _validate(field, "12")
    assert value == "12"
    assert warning is None
    value, warning = _validate(field, "12a")
    assert value == "12a"
    assert warning == "invalid_format"


def test_longest_label_wins_over_short_name():
    ocr = FakeOcrResult(
        text="",
        regions=[
            FakeRegion("Institution Name", 0.99, _row(80, 60, 320)),
            FakeRegion("Demo University", 0.93, _row(80, 400, 740)),
            FakeRegion("Student Name", 0.99, _row(135, 60, 320)),
            FakeRegion("Aarav Demo", 0.94, _row(135, 400, 740)),
        ],
    )
    result, _ = map_ocr_to_fields(ocr, "academic_certificate")
    assert result["institution_name"]["value"] == "Demo University"
    assert result["student_name"]["value"] == "Aarav Demo"


def test_nearest_below_when_no_right_value():
    ocr = FakeOcrResult(
        text="",
        regions=[
            FakeRegion("Student Name", 0.99, _row(80, 60, 320)),
            FakeRegion("Aarav Demo", 0.94, _row(140, 60, 320)),
        ],
    )
    result, _ = map_ocr_to_fields(ocr, "academic_certificate")
    assert result["student_name"]["value"] == "Aarav Demo"
    assert result["student_name"]["confidence"] == 0.94


def _make_document(session, **overrides):
    from datetime import datetime, timezone

    from app.models.document import Document, DocumentCategory, ProcessingState
    from app.repositories import documents_repo

    values = {
        "category": DocumentCategory.ACADEMIC_CERTIFICATE,
        "original_filename": "certificate.png",
        "storage_key": "uploads/certificate.png",
        "sha256": "b" * 64,
        "mime_type": "image/png",
        "byte_size": 2048,
        "page_count": 1,
        "processing_state": ProcessingState.OCR_DONE,
        "uploaded_at": datetime.now(timezone.utc).replace(tzinfo=None),
    }
    values.update(overrides)
    return documents_repo.create(session, Document(**values))


def _ocr_dump(ocr: FakeOcrResult) -> str:
    import json

    return json.dumps(
        {
            "text": ocr.text,
            "regions": [
                {
                    "text": region.text,
                    "confidence": region.confidence,
                    "bbox": list(region.bbox),
                    "page": region.page,
                }
                for region in ocr.regions
            ],
            "warnings": list(ocr.warnings or []),
        }
    )


def test_extract_fields_persists_merged_warnings(db_session):
    import json
    from datetime import datetime, timezone

    from app.models.extraction import ExtractionResult, ExtractionStatus
    from app.repositories import extraction_repo
    from app.services.extraction_service import extract_fields

    document = _make_document(db_session)
    ocr = academic_ocr()
    row = ExtractionResult(
        document_id=document.id,
        engine_name="fake",
        engine_version="1.0",
        raw_ocr_json=_ocr_dump(ocr),
        extracted_fields_json="{}",
        warnings_json=json.dumps(["low_confidence:student_name"]),
        status=ExtractionStatus.SUCCEEDED,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    extraction_repo.create(db_session, row)

    persisted = extract_fields(document.id, db_session)
    fields = json.loads(persisted.extracted_fields_json)
    warnings = json.loads(persisted.warnings_json)

    assert persisted.status == ExtractionStatus.SUCCEEDED
    assert fields["student_name"]["value"] == "Aarav Demo"
    assert "low_confidence:student_name" in warnings
    assert persisted.extracted_fields_json != "{}"


def test_extract_fields_returns_failed_row_unchanged(db_session):
    import json
    from datetime import datetime, timezone

    from app.models.extraction import ExtractionResult, ExtractionStatus
    from app.repositories import extraction_repo
    from app.services.extraction_service import extract_fields

    document = _make_document(db_session)
    row = ExtractionResult(
        document_id=document.id,
        engine_name="fake",
        engine_version="1.0",
        raw_ocr_json=_ocr_dump(academic_ocr()),
        extracted_fields_json="{}",
        warnings_json=json.dumps(["ocr_timeout"]),
        status=ExtractionStatus.FAILED,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    extraction_repo.create(db_session, row)

    persisted = extract_fields(document.id, db_session)
    assert persisted.status == ExtractionStatus.FAILED
    assert persisted.extracted_fields_json == "{}"
    assert json.loads(persisted.warnings_json) == ["ocr_timeout"]


def test_extract_fields_malformed_ocr_json_does_not_crash(db_session):
    import json
    from datetime import datetime, timezone

    from app.models.extraction import ExtractionResult, ExtractionStatus
    from app.repositories import extraction_repo
    from app.services.extraction_service import MALFORMED_OCR_WARNING, extract_fields

    document = _make_document(db_session)
    row = ExtractionResult(
        document_id=document.id,
        engine_name="fake",
        engine_version="1.0",
        raw_ocr_json="{not-json",
        extracted_fields_json="{}",
        warnings_json=json.dumps(["engine_warning"]),
        status=ExtractionStatus.SUCCEEDED,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    extraction_repo.create(db_session, row)

    persisted = extract_fields(document.id, db_session)
    fields = json.loads(persisted.extracted_fields_json)
    warnings = json.loads(persisted.warnings_json)
    assert fields["student_name"]["value"] is None
    assert "engine_warning" in warnings
    assert MALFORMED_OCR_WARNING in warnings


def _seed_via_client_db(**overrides):
    from datetime import datetime, timezone
    import json

    from app.db import SessionLocal
    from app.models.document import Document, DocumentCategory, ProcessingState
    from app.models.extraction import ExtractionResult, ExtractionStatus
    from app.repositories import documents_repo, extraction_repo

    session = SessionLocal()
    try:
        processing_state = overrides.pop("processing_state", ProcessingState.OCR_DONE)
        extraction_status = overrides.pop("extraction_status", ExtractionStatus.SUCCEEDED)
        extracted_fields_json = overrides.pop("extracted_fields_json", "{}")
        warnings_json = overrides.pop("warnings_json", "[]")
        skip_extraction = overrides.pop("skip_extraction", False)
        document = documents_repo.create(
            session,
            Document(
                category=DocumentCategory.ACADEMIC_CERTIFICATE,
                original_filename="certificate.png",
                storage_key="uploads/certificate.png",
                sha256="c" * 64,
                mime_type="image/png",
                byte_size=2048,
                page_count=1,
                processing_state=processing_state,
                uploaded_at=datetime.now(timezone.utc).replace(tzinfo=None),
            ),
        )
        if not skip_extraction:
            extraction_repo.create(
                session,
                ExtractionResult(
                    document_id=document.id,
                    engine_name="fake",
                    engine_version="1.0",
                    raw_ocr_json=_ocr_dump(academic_ocr()),
                    extracted_fields_json=extracted_fields_json,
                    warnings_json=warnings_json,
                    status=extraction_status,
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                ),
            )
        session.commit()
        return document.id
    finally:
        session.close()


def test_get_document_types_matches_category_schemas(client):
    response = client.get("/api/v1/document-types")
    assert response.status_code == 200
    body = response.json()
    by_category = {item["category"]: item for item in body}
    assert set(by_category) == {
        "academic_certificate",
        "institutional_id",
        "pan_like_demo",
        "government_certificate",
    }

    expected = {
        "academic_certificate": [
            ("student_name", "Student Name", "text", True, True),
            ("institution_name", "Institution Name", "text", True, True),
            ("student_id", "Student ID", "text", True, True),
            ("course_name", "Course Name", "text", True, True),
            ("semester_or_year", "Semester or Year", "text", True, True),
            ("certificate_or_marksheet_id", "Certificate or Marksheet ID", "text", True, True),
            ("issue_date", "Issue Date", "date", False, False),
        ],
        "institutional_id": [
            ("holder_name", "Holder Name", "text", True, True),
            ("institution_name", "Institution Name", "text", True, True),
            ("id_number", "ID Number", "text", True, True),
            ("designation_or_role", "Designation or Role", "text", False, False),
            ("valid_until", "Valid Until", "date", False, False),
        ],
        "pan_like_demo": [
            ("holder_name", "Holder Name", "text", True, True),
            ("demo_pan_code", "Demo PAN Code", "text", True, True),
            ("date_of_birth", "Date of Birth", "date", True, True),
            ("father_or_guardian_name", "Father or Guardian Name", "text", False, False),
        ],
        "government_certificate": [
            ("holder_name", "Holder Name", "text", True, True),
            ("certificate_type_label", "Certificate Type", "text", True, True),
            ("certificate_number", "Certificate Number", "text", True, True),
            ("issuing_authority_label", "Issuing Authority", "text", True, True),
            ("issue_date", "Issue Date", "date", False, False),
        ],
    }

    for category, fields in expected.items():
        payload_fields = [
            (
                field["name"],
                field["label"],
                field["type"],
                field["required"],
                field["match_field"],
            )
            for field in by_category[category]["fields"]
        ]
        assert payload_fields == fields


def test_get_extraction_200_shape(client):
    import json

    fields = {
        "student_name": {"value": "Aarav Demo", "confidence": 0.94, "source": "ocr"},
    }
    document_id = _seed_via_client_db(extracted_fields_json=json.dumps(fields))
    response = client.get(f"/api/v1/documents/{document_id}/extraction")
    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document_id
    assert body["engine_name"] == "fake"
    assert body["engine_version"] == "1.0"
    assert body["extracted_fields"]["student_name"]["value"] == "Aarav Demo"
    assert body["status"] == "SUCCEEDED"
    assert isinstance(body["warnings"], list)


def test_get_extraction_empty_fields_does_not_run_mapping(client):
    document_id = _seed_via_client_db(extracted_fields_json="{}")
    response = client.get(f"/api/v1/documents/{document_id}/extraction")
    assert response.status_code == 200
    assert response.json()["extracted_fields"] == {}


def test_get_extraction_404(client):
    response = client.get("/api/v1/documents/ffffffffffffffffffffffffffffffff/extraction")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_get_extraction_409_ocr_in_progress(client):
    from app.models.document import ProcessingState

    document_id = _seed_via_client_db(
        processing_state=ProcessingState.OCR_IN_PROGRESS,
        skip_extraction=True,
    )
    response = client.get(f"/api/v1/documents/{document_id}/extraction")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EXTRACTION_NOT_READY"


def test_get_extraction_200_failed(client):
    import json

    from app.models.document import ProcessingState
    from app.models.extraction import ExtractionStatus

    document_id = _seed_via_client_db(
        processing_state=ProcessingState.OCR_FAILED,
        extraction_status=ExtractionStatus.FAILED,
        warnings_json=json.dumps(["ocr_timeout"]),
        extracted_fields_json="{}",
    )
    response = client.get(f"/api/v1/documents/{document_id}/extraction")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert "ocr_timeout" in body["warnings"]


def test_schema_package_has_no_framework_imports():
    from pathlib import Path

    schema_dir = Path(__file__).resolve().parents[1] / "app" / "domain" / "schemas"
    forbidden = ("fastapi", "sqlalchemy", "paddleocr", "web3")
    for path in schema_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in source, f"{path.name} contains {token}"

