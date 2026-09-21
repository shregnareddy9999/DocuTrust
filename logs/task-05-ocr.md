# Task 05 — PaddleOCR Adapter and Preprocessing — Development Log

**Owner:** Member A / AI session
**Branch:** `feature/task-05-ocr`
**Started:** 2026-09-20
**Status:** Ready for review

---

## Contracts this task implements

- `docs/document-processing.md` — Pipeline steps 1–8, PaddleOCR boundaries, failure states
- `docs/backend.md` — `adapters/ocr/`, `services/ocr_service.py`
- `docs/architecture.md` — Adapters are the only place external runtimes are imported
- `docs/configuration.md` — `OCR_ENGINE`, `OCR_LANGUAGE`, `OCR_TIMEOUT_SECONDS`, `LOW_CONFIDENCE_THRESHOLD`, `MAX_PDF_PAGES`
- `docs/data-model.md` — `extraction_results` columns, `documents.processing_state`
- `docs/testing.md` — Integration marker convention
- `docs/decisions.md` — D-02 (PaddleOCR), D-06 (no mandatory LLM), D-16 (synchronous for MVP)
- `docs/ENVIRONMENT-REPORT.md` — Pinned versions, Python 3.11 requirement
- `docs/workflow.md` Stages 2–3
- `AGENTS.md` — Rules 3, 5, 10, 11
- `tasks/05-ocr-adapter.md` — Full work order

---

## Interfaces I published for other tasks

```python
# backend/app/adapters/ocr/base.py — stabilized 2026-09-20

@dataclass
class OcrRegion:
    text: str
    confidence: float          # 0.0–1.0
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)
    page: int                  # 1-indexed

@dataclass
class OcrResult:
    text: str                  # all regions joined in reading order
    regions: list[OcrRegion]
    mean_confidence: float | None
    engine_name: str
    engine_version: str
    warnings: list[str]

class OcrAdapter(ABC):
    @abstractmethod
    def run(self, image: PIL.Image) -> OcrResult: ...
```

```python
# backend/app/adapters/ocr/__init__.py — factory
def get_ocr_adapter() -> OcrAdapter:
    # OCR_ENGINE=paddleocr → PaddleOcrAdapter
    # OCR_ENGINE=fake → FakeOcrAdapter(mode="clean")
    # Unknown → ValueError (fail-fast)
```

```python
# backend/app/services/ocr_service.py — main entry point
def process_document(document_id: str, session) -> ExtractionResult:
    # Implements document-processing.md steps 1–8
    # Returns ExtractionResult with status SUCCEEDED/FAILED
    # Updates documents.processing_state to OCR_DONE/OCR_FAILED
```

---

## Decisions I made inside my own scope

| Date | Decision | Why | Reversible? |
|------|----------|-----|-------------|
| 2026-09-20 | BBox format: `(x1, y1, x2, y2)` | Explicitly required by task constraints; min/max of PaddleOCR quadrilateral | Yes |
| 2026-09-20 | Preprocessing: Pillow-only (no OpenCV) | Conservative: EXIF orient, grayscale, median filter 3x3, contrast 1.2x | Yes |
| 2026-09-20 | PDF rendering: pypdfium2 (same as Task 04) | Already in requirements; Task 04 validated | Yes (with coordination) |
| 2026-09-20 | Timeout: ThreadPoolExecutor (not signals) | Windows-compatible per AGENTS.md Rule 10 | Yes |
| 2026-09-20 | `extracted_fields_json` = `{}` | Task 06 responsibility; this task only persists raw OCR | Yes |
| 2026-09-20 | `LOW_CONFIDENCE_THRESHOLD` not read | Task 07 decision; this task passes confidence through unaltered | Yes |
| 2026-09-20 | `extracted_fields_json` left empty for Task 06 | Task 06 owns extraction mapping | Yes |
| 2026-09-20 | Dependencies: `paddlepaddle==2.6.1`, `paddleocr==2.8.1` | Compatible with Python 3.11 (required per ENVIRONMENT-REPORT) | Yes (requires verification on 3.11) |

---

## Progress

### 2026-09-20 — Phase 1: Contract, Fakes, Pipeline, Tests

**Did:**
- Implemented `OcrAdapter`, `OcrRegion`, `OcrResult` in `base.py`
- Implemented `FakeOcrAdapter` with 5 deterministic modes: `clean`, `low_confidence`, `empty`, `raises`, `timeout`
- Implemented adapter factory in `__init__.py` with fail-fast on unknown `OCR_ENGINE`
- Implemented full OCR pipeline in `ocr_service.py`:
  - PDF page rendering via pypdfium2 (capped at `MAX_PDF_PAGES`)
  - Long-edge capped at 2000px
  - Conservative preprocessing (EXIF, grayscale, median filter, contrast)
  - Per-page adapter invocation with timeout
  - Multi-page assembly with reading-order sort
  - `extraction_results` persistence with `raw_ocr_json`, `warnings_json`, `engine_name`, `engine_version`, `status`
  - `processing_state` transitions: `UPLOADED` → `OCR_IN_PROGRESS` → `OCR_DONE`/`OCR_FAILED`
- Wrote 15 default-suite tests in `test_ocr_pipeline.py` covering all required semantics
- Updated `conftest.py` with `OCR_ENGINE="fake"` and fake adapter fixtures
- Approved config change: `OCR_ENGINE: Literal["paddleocr", "fake"]` in `config.py`

**Verified by running:**
```bash
cd backend && .venv\Scripts\python -m pytest tests/test_ocr_pipeline.py -v
# 15 passed
cd backend && .venv\Scripts\python -m pytest -v --tb=no -q
# 113 passed, 1 deselected
```

### 2026-09-20 — Phase 2: Real PaddleOCR Adapter

**Did:**
- Implemented `PaddleOcrAdapter` in `paddleocr_adapter.py` with lazy initialization
- PaddleOCR imported ONLY inside this module
- Normalizes PaddleOCR quadrilateral `[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]` → `(min(x), min(y), max(x), max(y))`
- Reading order: top-to-bottom (y1), then left-to-right (x1)
- Engine version captured at runtime from `paddleocr.__version__`
- Added dependencies to `requirements.txt`: `paddlepaddle==2.6.1`, `paddleocr==2.8.1`
- Integration test already present in `test_ocr_pipeline.py` marked `@pytest.mark.integration`

**Verified by running:**
```bash
cd backend && .venv\Scripts\python -m pytest -v --tb=no -q
# 113 passed, 1 deselected
cd backend && .venv\Scripts\python -m pytest tests/test_ocr_pipeline.py::TestOcrPipeline::test_no_paddleocr_import_in_default_suite -v
# PASSED
```

---

## Blockers and open questions

| # | Question | Asked on | Answer | Resolved |
|---|----------|----------|--------|----------|
| 1 | BBox format | 2026-09-20 | `(x1, y1, x2, y2)` per task constraint | ✅ |
| 2 | OpenCV for preprocessing? | 2026-09-20 | No — Pillow only per constraints | ✅ |
| 3 | PaddleOCR versions | 2026-09-20 | `paddlepaddle==2.6.1`, `paddleocr==2.8.1` (Python 3.11 compatible) | ✅ (unverified on 3.11) |
| 4 | `OCR_ENGINE=fake` config support | 2026-09-20 | Approved: modified `config.py` Literal | ✅ |
| 5 | Development log scope | 2026-09-20 | Approved: created `logs/task-05-ocr.md` | ✅ |

---

## Tests

| Command | Last run | Result |
|---------|----------|--------|
| `cd backend && .venv\Scripts\python -m pytest -v --tb=no -q` | 2026-09-20 | 113 passed, 1 deselected |
| `cd backend && .venv\Scripts\python -m pytest tests/test_ocr_pipeline.py -v` | 2026-09-20 | 15 passed, 1 deselected |
| `cd backend && .venv\Scripts\python -m pytest tests/test_ocr_pipeline.py::TestOcrPipeline::test_no_paddleocr_import_in_default_suite -v` | 2026-09-20 | PASSED |
| `cd backend && .venv\Scripts\python -m pytest tests/test_ocr_pipeline.py::TestOcrPipelineIntegration -v -m integration --collect-only` | 2026-09-20 | 1 collected (marked integration) |

---

## 2026-09-21 — Recognition quality vs mapping

Document evidence (`raw_ocr_json`, not a DB re-query): PaddleOCR 2.8.1, extraction **SUCCEEDED**, warnings `[]`, 11 regions, mean confidence ~0.65, strings like `Acae` / `Sii`. Mapper then correctly left academic fields `{value: null, confidence: null, source: "ocr"}` and Task 07 returned **REVIEW_REQUIRED** (missing required fields). That is not a fraud verdict and not a mapping bug.

**SUCCEEDED ≠ usable text.** Zero-or-garbage rec with a successful adapter call is still SUCCEEDED.

Fixes in this adapter:

- Convert the preprocessed page to RGB (`H×W×3`) before `ocr()`. Preprocess still uses mode `L`; grayscale restore is adapter-side only.
- `parse_paddle_ocr_payload` handles `None` / `[]` / page `None` / malformed lines without inventing text.
- Fake `clean` / `low_confidence` now emit two-column Task 03 labels+values so Task 06 can map without live Paddle. Engine strings are not hardcoded in the Paddle adapter.

Live Paddle still skipped on Python 3.14.

## Known limitations at handoff

- **Real PaddleOCR execution NOT verified** — Current machine uses Python 3.14.6; `docs/ENVIRONMENT-REPORT.md` confirms no PaddlePaddle wheel exists for Python 3.14. Integration test is implemented but will only run on a Python 3.11.x machine with working PaddlePaddle.
- **No degraded-sample confidence values recorded** — Requires real PaddleOCR run on `academic_certificate_degraded.png` (Task 03/07 need these).
- **No single-page timing recorded** — NFR-09 budget (15s total chain) not measured; requires real OCR run.
- **Dependencies pinned by version-series compatibility** — `paddlepaddle==2.6.1` + `paddleocr==2.8.1` assumed correct for Python 3.11; not install-tested on this machine.
- **Development log created** — `logs/task-05-ocr.md` created per AGENTS.md requirement with explicit approval (scope conflict resolved).

---

## Handoff notes

- **Files changed:** 9 files (see `git diff --stat`)
- **What Task 06 needs:** `OcrResult` contract is stable; `process_document()` returns `ExtractionResult` with `raw_ocr_json` containing full OCR output; `extracted_fields_json` is `{}` waiting for Task 06.
- **What Task 07 needs:** Confidence values passed through unaltered; `LOW_CONFIDENCE_THRESHOLD` not read here.
- **What Task 10 needs:** `process_document(document_id, session)` is the entry point; returns `ExtractionResult`; updates `processing_state`.
- **What I did NOT do:** Field mapping, confidence thresholding, authenticity scoring, registry matching, blockchain submission, Task 10 orchestration — all out of scope.

---

## Remaining environment limitation

**Python 3.14.6 cannot run real PaddleOCR.** Per `docs/ENVIRONMENT-REPORT.md`:
- No PaddlePaddle wheel for Python 3.14
- PaddleOCR 3.x imports but fails at runtime without PaddlePaddle
- **Demo machine must be Python 3.11.x** with verified PaddlePaddle/PaddleOCR installation
- Integration test `test_real_paddleocr_academic_certificate_match` is correctly marked `@pytest.mark.integration` and excluded from default suite