# Task 07 — Registry matching and deterministic rules — Development Log

**Owner:** Task 07
**Branch:** `feature/task-07-rules`
**Started:** 2026-09-21
**Status:** Ready for review (do not mark the task complete in the tracker)

---

## Contracts this task implements

- `docs/verification-rules.md` — normalization, matching steps 1–6, five rules, status vocabulary, precedence D-15
- `docs/category-schemas.md` — `match_field` flags and identifying keys
- `docs/data-model.md` — `verification_results` JSON columns; new row per run; `supersedes_verification_id` null
- `docs/api.md` — `POST /documents/{id}/verify`, `GET /verifications/{id}`
- `docs/architecture.md` — domain purity; registry query error ≠ no record
- `docs/configuration.md` — `LOW_CONFIDENCE_THRESHOLD=0.70`
- `logs/task-06-extraction.md` — `extracted_fields` `{value, confidence, source}`

## Decisions I made inside my own scope

| Date | Decision | Why | Reversible? |
|---|---|---|---|
| 2026-09-21 | Domain `VerificationStatus` / `RecordingStatus` in `status.py`; models keep Task 02 SQLAlchemy enums; service maps by `.value` | Changing models is out of allowed files; domain cannot import SQLAlchemy | Yes if Task 02 later re-exports |
| 2026-09-21 | Registry-load `except` writes `PROCESSING_FAILED` / `REGISTRY_ERROR` without calling `evaluate()` precedence | `evaluate()` would otherwise assign `NO_TRUSTED_RECORD` or `REVIEW_REQUIRED` | No without violating Rule 3 |
| 2026-09-21 | `POST .../verify` runs `process_document` when no successful extraction exists; `409` only if `OCR_IN_PROGRESS` | Matches `api.md` / `document-processing.md`. Upload still does not run OCR. | No without contract change |
| 2026-09-21 | Successful path calls Task 06 `extract_fields` before matching | Task 05 leaves `extracted_fields_json="{}"` | Yes |
| 2026-09-21 | Reason codes: `EXTRACTION_FAILED`, `REGISTRY_ERROR`, `REGISTRY_DATA_ERROR`, `NO_TRUSTED_RECORD`, `MISSING_REQUIRED:<field>`, `LOW_CONFIDENCE:<field>`, `FIELD_MISMATCH:<field>` | Task error table + `api.md` example pattern | Yes if project lead names a closed set |
| 2026-09-21 | Multiple identifying-key hits (no unique full match) → `registry_data_error` | Ambiguous applicable reference is a seeding bug, not a mismatch | Yes |

## Interfaces I published for other tasks

```python
def evaluate(
    extraction_status: str,
    extracted_fields: dict,
    match_result: MatchResult,
    schema: list[FieldDef],
    low_confidence_threshold: float,
) -> VerificationOutcome
```

`extraction_status` is `"FAILED"` or `"SUCCEEDED"` (extraction row status).

```python
@dataclass
class VerificationOutcome:
    status: VerificationStatus
    field_comparisons: list[dict]  # {field, extracted_value, registry_value, matched}
    rule_results: list[RuleResult]  # five entries, documented rule_id order
    reason_codes: list[str]
    registry_record: dict | None

@dataclass
class RuleResult:
    rule_id: str
    passed: bool
    reason: str  # human-readable; never a score
```

Task 08 must call this same `evaluate()` after corrections. Do not hand-assign a status. Task 09/10: verification never touches the chain. `supersedes_verification_id` is always null on rows this task writes.

Precedence in `evaluate()` (first match wins):

1. Extraction failed → `PROCESSING_FAILED` (`EXTRACTION_FAILED`)
2. Rule exception → `PROCESSING_FAILED` (`RULE_EXCEPTION:<rule_id>`)
3. `match_result.registry_data_error` → `PROCESSING_FAILED` (`REGISTRY_DATA_ERROR`)
4. Missing required field or match-field confidence below threshold → `REVIEW_REQUIRED`
5. No applicable record → `NO_TRUSTED_RECORD`
6. Any match-field comparison fails → `INTEGRITY_MISMATCH`
7. All match-field comparisons pass → `VERIFIED_MATCH`

Registry **query exception** is handled in the service (`REGISTRY_ERROR`), not as a miss.

## Progress

### 2026-09-21 (OCR-on-verify)
- Did: `verify_document` calls Task 05 `process_document` when `get_latest_successful_for_document` is None, then `extract_fields`, then matching. Concurrent `OCR_IN_PROGRESS` still `409`.
- Verified: `test_upload_then_verify_runs_ocr_and_returns_terminal_status`; `test_verify_skips_ocr_when_successful_extraction_exists`.
- Fake OCR canned text is not Task 03 two-column labels — upload+verify with `OCR_ENGINE=fake` completes with a **terminal** status; it is not claimed as `VERIFIED_MATCH`.

## Tests

| Command | Last run | Result |
|---|---|---|
| `cd backend && .\venv\Scripts\python.exe -m pytest tests/test_matching_rules.py tests/test_ocr_pipeline.py tests/test_extraction.py tests/test_upload.py -v` | 2026-09-21 | 111 passed, 1 deselected in 4.64s |
| `cd backend && .\venv\Scripts\python.exe -m pytest tests/test_matching_rules.py -v` | 2026-09-21 | 40 passed (included in focused run) |
| `cd backend && .\venv\Scripts\python.exe -m pytest -v --tb=no -q` | 2026-09-21 | 189 passed, 1 deselected in 7.72s |

Exact focused output footer:

```
====================== 111 passed, 1 deselected in 4.64s ======================
```

Exact full-suite footer:

```
====================== 189 passed, 1 deselected in 7.72s ======================
```

(1 deselected = `@pytest.mark.integration`.)

## Manual scenarios

These used seeded `FIXTURES` from `fixture_data.py` and `verify_document` on a temp DB (not a live PaddleOCR upload of the PNG files). Identifying keys and field values are the locked demo strings.

| Sample | Result | Evidence |
|---|---|---|
| `academic_certificate_match.png` analog (all six match fields = fixture) | `VERIFIED_MATCH`; six comparisons `matched: true` | `test_manual_fixture_match_mismatch_unregistered` |
| `academic_certificate_mismatch.png` analog (`semester_or_year` = `6`) | `INTEGRITY_MISMATCH`; `FIELD_MISMATCH:semester_or_year`; extracted `6`, registry `5` | same test + `test_get_verification_full_shape` |
| `academic_certificate_unregistered.png` analog (`DEMO-STU-999`) | `NO_TRUSTED_RECORD` | same test |
| `academic_certificate_degraded.png` | **Not run against live PaddleOCR.** Fake-adapter / hand-built fields: match-field confidence `0.69` / `0.50` → `REVIEW_REQUIRED` with `LOW_CONFIDENCE:<field>`. Real degraded-PNG confidence was not measured this session. | `test_review_required_low_confidence`, `test_low_confidence_beats_verified_match` |
| Database stopped during verification | Registry `list_active_by_category` raised `RuntimeError("database stopped")` → `PROCESSING_FAILED`, reason `REGISTRY_ERROR`, **not** `NO_TRUSTED_RECORD`. SQLite file was not actually unmounted mid-request. | `test_registry_error_is_not_no_trusted_record` |

## Known limitations at handoff

- `POST .../verify` now runs OCR when there is no successful extraction. `409 EXTRACTION_NOT_READY` remains only for concurrent `OCR_IN_PROGRESS`.
- Fake adapter text is not two-column Task 03 layout, so upload+verify with `OCR_ENGINE=fake` is not a `VERIFIED_MATCH` demo of the PNGs.
- Domain status enums duplicate model enum *values* (not classes).
- Degraded PNG + real PaddleOCR not executed (no integration run).
- `GET /documents/{id}/verifications` not implemented (Task 10). Review and blockchain are Task 08/09.

## Handoff notes

- Files changed: `backend/app/domain/status.py`, `normalization.py`, `matching.py`, `rules.py`, `backend/app/services/verification_service.py`, `backend/app/api/verifications.py`, `backend/app/main.py`, `backend/tests/test_matching_rules.py`, this log.
- Next task needs: call `evaluate()` only; persist a new row; leave `supersedes_verification_id` for Task 08.
- What I did **not** do: frontend, human review, blockchain, commit/push, loosening comparison to make a demo pass.
