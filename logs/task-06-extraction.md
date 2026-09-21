# Task 06  Category-specific field extraction  Development Log

**Owner:** Task 06
**Branch:** current checkout is `main`. Do not commit here; move to `feature/task-06-extraction` before any commit.
**Started:** 2026-09-21
**Status:** Ready for review (do not mark the task complete in the tracker)

---

## Contracts this task implements

- `docs/category-schemas.md`  four categories, field names/types/required/match_field
- `docs/api.md`  `GET /document-types`, `GET /documents/{id}/extraction` (404 / 409 / 200 FAILED)
- `docs/data-model.md`  `extraction_results.extracted_fields_json` shape `{field: {value, confidence, source}}`
- `docs/document-processing.md`  GET does not run OCR; mapping is a separate writer
- `tasks/06-field-extraction.md`  deterministic mapping, never invent values

## Decisions I made inside my own scope

| Date | Decision | Why | Reversible? |
|---|---|---|---|
| 2026-09-21 | Label match is equality or prefix then `:` / `=` / end-of-string; longest label wins, including across fields | Stops `"name"` stealing `"Institution Name"` and `"certificate"` stealing `"Certificate Number"` | Yes, mapper-only |
| 2026-09-21 | Same-region remainder, else nearest right (same page, `x1 >= label.x2` with 8px slack, vertical overlap), else nearest below (`y1 >= label.y2`, horizontal overlap preferred) | Task 03 samples draw labels at `MARGIN` and values at `MARGIN + 340` as two OCR regions | Yes |
| 2026-09-21 | Do not reuse a value region; do not use a label-only region as a value | Prevents one number filling two fields | Yes |
| 2026-09-21 | `GET /extraction` is read-only; `extract_fields(document_id, session)` is the writer | Matches the plan and Task 05 leaving `extracted_fields_json="{}"` until mapping runs | No without API change |
| 2026-09-21 | Malformed `raw_ocr_json` ? all schema fields `null` + warning `malformed_raw_ocr_json`; no crash | Technical failure must not become a verdict | Yes (warning string is mapper-owned) |
| 2026-09-21 | Extra alias labels only (`semester / year`, `certificate / marksheet id`, `demo pan-like code`, `designation / role`). No new schema fields | Task 03 `FIELD_LABELS` text | Yes |

## Interfaces I published for other tasks

`extracted_fields` (persisted JSON and GET body):

```json
{
  "student_name": { "value": "Aarav Demo", "confidence": 0.94, "source": "ocr" }
}
```

- `value` is the exact adjacent OCR string (or same-region remainder), or `null`.
- `confidence` is the **value region**'s OCR confidence (or the same-region confidence), never a fraud score.
- `source` is always `"ocr"` at this stage.
- Invalid date/PAN/integer: **keep the OCR string**, add `unrecognized_date_format:<name>` or `invalid_format:<name>`.
- Missing required field: `value`/`confidence` null + `missing_field:<name>`.

Writer:

```python
extract_fields(document_id: str, session) -> ExtractionResult | None
```

- Loads document; unknown category ? `UnknownCategoryError` (API maps to 500 `INTERNAL_ERROR` if a caller surfaces it).
- Latest extraction `FAILED` ? return that row unchanged (Task 07 ? `PROCESSING_FAILED`).
- Else latest successful row: deserialize `raw_ocr_json` (`text`, `regions[{text,confidence,bbox,page}]`, `warnings` per Task 05 dump).
- Merge row `warnings_json` with mapping warnings (append, do not replace).
- Flush, no commit. Does not change extraction `status`. Does not read `LOW_CONFIDENCE_THRESHOLD`.

GET `/api/v1/documents/{document_id}/extraction` does **not** call `extract_fields` or OCR. If Task 05 left `extracted_fields_json="{}"`, GET returns `"extracted_fields": {}`.

## Adjacency strategy

For each schema field, in schema order:

1. Find a region whose normalized text **equals** a label or **starts with** that label followed by `:` / `=` / end-of-string (case-insensitive, collapsed whitespace). Prefer the **longest** matching label. If a longer label from another field matches the same region, skip it for this field.
2. If leftover text remains in that same region after the label, that is the value. Confidence = that region's confidence.
3. Else nearest unused region **to the right** on the same page: `x1 >= label.x2` (8px slack), vertical overlap, smallest horizontal gap then smallest `|y1 - label.y1|`.
4. Else nearest unused region **below**: `y1 >= label.y2`, horizontal overlap preferred, smallest vertical gap.
5. No match ? `{value: null, confidence: null, source: "ocr"}`. `missing_field:<name>` only if `required`.
6. Never invent: every non-null value is the exact adjacent region's text or the same-region remainder.
7. Do not reuse a value region. Do not use a label-only region as a value.

## Progress

### 2026-09-21
- Did: same-region-only mapper existed; extended adjacency + Task 03 aliases; `extract_fields`; GET extraction; tests; this log.
- Verified by running: `cd backend && .\venv\Scripts\python.exe -m pytest tests/test_extraction.py -v` ? `36 passed in 0.55s`
- Next: Task 07 should call `extract_fields` after successful OCR. GET remains read-only.

## Blockers and open questions

| # | Question | Asked on | Answer | Resolved |
|---|---|---|---|---|
| 1 | None for mapper/GET | | | ? |

## Tests

| Command | Last run | Result |
|---|---|---|
| `cd backend && .\venv\Scripts\python.exe -m pytest tests/test_extraction.py -v` | 2026-09-21 | 36 passed in 0.55s |

Exact output:

```
============================= 36 passed in 0.55s ==============================
```

Bare `python -m pytest` on this machine uses a system interpreter without SQLAlchemy. Use `backend\venv\Scripts\python.exe`.

## Known limitations at handoff

- Task 05 still stores `extracted_fields_json="{}"` until something calls `extract_fields`. Verify and GET extraction will look empty unless Task 07 (or a test) runs the writer.
- No live PaddleOCR run. Degraded-sample OCR confidence was **not** invented.
- Domain `FieldDef.validator` remains unused; format checks live in `extraction_service._validate`.
- `ocr_service.py` was not modified (out of allowed files).

## Handoff notes

- Files changed: `backend/app/services/extraction_service.py`, `backend/app/api/documents.py` (GET extraction only), `backend/app/domain/schemas/*.py` (alias labels only), `backend/tests/test_extraction.py`, `logs/task-06-extraction.md`. `GET /document-types` and `main.py` router registration were already present.
- What the next task needs to know: call `extract_fields(document_id, session)` after a successful OCR row; do not treat GET as a pipeline trigger.
- What I did **not** do: frontend, registry matching, verification status, commit/push, live OCR, changing Task 05 `ocr_service.py`.
