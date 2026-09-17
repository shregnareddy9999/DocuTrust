# Category Schemas and Synthetic Registry Fixtures

This file is the single source of truth for field names, types, and required/optional status per
category. `GET /document-types` (see `api.md`) must return exactly this data — never a hand-copied
subset. Extraction mappers, matching rules, and frontend forms all derive from this file. Do not
add, rename, or remove a field here without a project-lead-approved doc update — every task that
touches extraction or matching depends on these names being stable.

## Common field metadata shape

Every field is declared as:
```json
{ "name": "string", "label": "string", "type": "text|date|integer", "required": true, "match_field": true }
```
`match_field: true` means this field participates in registry comparison (`verification-rules.md`).
A field can be extracted and shown (`required: false`) without being part of matching.

---

## 1. `academic_certificate`

| Field | Type | Required | Match field |
|---|---|---|---|
| `student_name` | text | yes | yes |
| `institution_name` | text | yes | yes |
| `student_id` | text | yes | yes |
| `course_name` | text | yes | yes |
| `semester_or_year` | text | yes | yes |
| `certificate_or_marksheet_id` | text | yes | yes |
| `issue_date` | date | no | no |

**Synthetic registry fixture (`DEMO-STU-001`):**
```json
{
  "student_name": "Aarav Demo",
  "institution_name": "Example Technical Institute",
  "student_id": "DEMO-STU-001",
  "course_name": "B.Tech CSE",
  "semester_or_year": "5",
  "certificate_or_marksheet_id": "DEMO-MARK-001"
}
```
Matching document fixture: `backend/app/fixtures/sample_documents/academic_certificate_match.png`
(and a deliberately mismatching sibling `..._mismatch.png` with a different `semester_or_year`).

---

## 2. `institutional_id`

| Field | Type | Required | Match field |
|---|---|---|---|
| `holder_name` | text | yes | yes |
| `institution_name` | text | yes | yes |
| `id_number` | text | yes | yes |
| `designation_or_role` | text | no | no |
| `valid_until` | date | no | no |

**Synthetic registry fixture (`DEMO-ID-001`):**
```json
{
  "holder_name": "Priya Demo",
  "institution_name": "Example Technical Institute",
  "id_number": "DEMO-ID-001",
  "designation_or_role": "Student"
}
```

---

## 3. `pan_like_demo`

Field names deliberately avoid the real PAN format/label to prevent any confusion with a real
document. `demo_pan_code` values are always 6 characters, letters+digits, **never** matching the
real 10-character alphanumeric PAN pattern (`AAAAA9999A`) — this is enforced in the extraction
mapper's format validator, not just by convention.

| Field | Type | Required | Match field |
|---|---|---|---|
| `holder_name` | text | yes | yes |
| `demo_pan_code` | text | yes | yes |
| `date_of_birth` | date | yes | yes |
| `father_or_guardian_name` | text | no | no |

**Synthetic registry fixture (`DEMO-PAN-001`):**
```json
{
  "holder_name": "Rohan Demo",
  "demo_pan_code": "DP1234",
  "date_of_birth": "1999-01-15"
}
```

---

## 4. `government_certificate`

Generic category for any other synthetic government-style certificate (e.g., a demo income/caste/
domicile-style certificate template built for this project — never a real template).

| Field | Type | Required | Match field |
|---|---|---|---|
| `holder_name` | text | yes | yes |
| `certificate_type_label` | text | yes | yes |
| `certificate_number` | text | yes | yes |
| `issuing_authority_label` | text | yes | yes |
| `issue_date` | date | no | no |

**Synthetic registry fixture (`DEMO-GOV-001`):**
```json
{
  "holder_name": "Meera Demo",
  "certificate_type_label": "Demo Residence Certificate",
  "certificate_number": "DEMO-GOV-001",
  "issuing_authority_label": "Example Demo Authority"
}
```

---

## Rules for all categories

- Every registry fixture's `synthetic_record_key` and every identifier field value must be
  obviously synthetic (`DEMO-` prefix, or fictional names like "Aarav Demo") — never a realistic-
  looking real-world identifier.
- Date fields accept `YYYY-MM-DD` only. Any other observed format is stored as extracted but marked
  `warnings: ["unrecognized_date_format"]` and excluded from date-consistency rules until a reviewer
  resolves it.
- Adding a 5th category or changing a required/optional flag is a documentation change (this file +
  `data-model.md` if columns are affected) that must ship with the code change in the same PR, and
  is exactly the kind of "shared contract change" that needs project-lead approval per
  `AI-CONTEXT.md`.
