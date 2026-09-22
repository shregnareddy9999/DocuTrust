# Task 03 — Synthetic Registry and Seed Fixtures

## Status
Implementation tested; final specification review and Git review remain.

## Branch
`feature/task-03-registry`

## Automated Tests
- Task 03 tests: 8 passed.
- Full backend test suite: 78 passed after the degraded-image changes.
- Normal pytest command works without `-p no:asyncio`.

## Dependencies
- Pillow 12.3.0 installed in the active virtual environment.
- Added `Pillow` to `backend/requirements.txt`.
- Dependency change is local and uncommitted.

## Sample Documents
- Confirmed all 11 required sample files were present.
- First three academic PNG samples were visually checked and readable.
- Latest `academic_certificate_degraded.png` was visually checked by the team lead; text and footer are readable.
- Remaining sample documents and the academic PDF were visually checked and reported readable.
- The academic PDF was accidentally deleted during inspection and restored with `git restore`.

## Degraded Image Settings
Latest settings reported by Cursor:
- `DEGRADED_DOWNSCALE_FACTOR = 1.0`
- `DEGRADED_BLUR_RADIUS = 0.7`
- `DEGRADED_CONTRAST_FACTOR = 0.90`
- `DEGRADED_NOISE_STDDEV = 5`
- `DEGRADED_SEED = 20240301`

The latest image is visually readable. Its behavior against real OCR has not been verified here; coordinate with the OCR task owner when that implementation is available.

## Remaining Verification
1. Review the complete Task 03 implementation against the authoritative specification and locked category schemas.
2. Confirm the seeder's create/unchanged/divergent behavior and exact fixture values against the specification.
3. Confirm the generated samples' field-level values, exact footer, and mismatch-only differences against the specification.
4. Confirm the Pillow dependency is appropriate and reproducible for project setup.
5. Review the final diff and ensure only intended Task 03 changes are included.
6. Update this log with any additional verified results before marking the task complete.

## Current Git Status
- Branch: `feature/task-03-registry`
- Modified: `backend/app/fixtures/generate_samples.py`
- Modified: `backend/app/fixtures/sample_documents/academic_certificate_degraded.png`
- Modified: `backend/requirements.txt`
- Untracked: `logs/task-03-registry.md`
- No commit or push has been made for these local changes.

## 2026-09-21 — TrueType fonts for PaddleOCR (not mapper)

- `_font()` now tries Windows Arial/Calibri, macOS Arial, Linux DejaVu/Liberation. If none load, it raises. It never uses `ImageFont.load_default()` (bitmap default was unreadably small; Paddle det still boxed specks and rec emitted garbage at ~0.65).
- Regenerated all files under `backend/app/fixtures/sample_documents/` with `python -m app.fixtures.generate_samples` (venv). Layout, 22/34pt, two-column `MARGIN` / `MARGIN+340`, and `FIXTURES` values unchanged.
- Live Paddle on these PNGs was not run here (Python 3.14, no paddle wheel).

## 2026-09-22 — Regenerated samples again after diagnosis plan

- `_font(22)` loads `FreeTypeFont` from `C:\Windows\Fonts\arialbd.ttf`.
- Command: `cd backend && .\venv\Scripts\python.exe -m app.fixtures.generate_samples` — 12 files including the 11 required samples.
- Visual check of `academic_certificate_match.png`: readable labels (`Student Name:`) and values (`Aarav Demo`), 1000×700, high contrast.
- Document `37c9ce9304ad458cb433b22fc196ef29` was OCR'd against the **old** bitmap-default PNG. Re-upload the **new** PNG on Python 3.11 + Paddle 2.6.2 / 2.8.1; do not claim live rec on this 3.14 interpreter.

## Completion
Task 03 is not yet marked complete. Final completion depends on the remaining specification review and confirmation that all acceptance criteria are satisfied.
