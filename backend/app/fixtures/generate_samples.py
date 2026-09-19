"""
Renders the eleven synthetic sample documents required by Task 03 §7
Requirement 3, programmatically from `fixture_data.FIXTURES` so they can be
regenerated and can never drift from the registry values.

    python -m app.fixtures.generate_samples

Documents are plain, high-contrast, OCR-friendly renders (a title, then
labelled field rows) -- fancy fonts, watermarks, and textures hurt OCR and
are deliberately avoided (Task 03 §10 Known Risks).
"""

from __future__ import annotations

import copy
from pathlib import Path

import random

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .fixture_data import FIXTURES

OUTPUT_DIR = Path(__file__).parent / "sample_documents"

FOOTER_TEXT = "SYNTHETIC DEMO DOCUMENT \u2014 NOT A REAL CERTIFICATE"

# First-pass degraded-sample tuning (Task 03 §7 Requirement 3 / §11 Open
# Questions). NOT yet validated against real PaddleOCR -- Task 05 doesn't
# exist in this checkout. Tune together with Member A once it does, and
# record the final values used in logs/task-03-registry.md.
DEGRADED_DOWNSCALE_FACTOR = 1.0    # keep source resolution so text stays crisp
DEGRADED_BLUR_RADIUS = 0.7
DEGRADED_CONTRAST_FACTOR = 0.90
DEGRADED_NOISE_STDDEV = 5
DEGRADED_SEED = 20240301           # fixed seed -> deterministic re-runs

CATEGORY_TITLES = {
    "academic_certificate": "Demo Academic Certificate",
    "institutional_id": "Demo Institutional ID Card",
    "pan_like_demo": "Demo PAN-Like Identifier",
    "government_certificate": "Demo Government-Style Certificate",
}

FIELD_LABELS = {
    "student_name": "Student Name",
    "institution_name": "Institution Name",
    "student_id": "Student ID",
    "course_name": "Course",
    "semester_or_year": "Semester / Year",
    "certificate_or_marksheet_id": "Certificate / Marksheet ID",
    "holder_name": "Holder Name",
    "id_number": "ID Number",
    "designation_or_role": "Designation / Role",
    "demo_pan_code": "Demo PAN-Like Code",
    "date_of_birth": "Date of Birth",
    "certificate_type_label": "Certificate Type",
    "certificate_number": "Certificate Number",
    "issuing_authority_label": "Issuing Authority",
}

WIDTH, HEIGHT = 1000, 700
MARGIN = 60
ROW_HEIGHT = 55

# Values chosen here (for *_mismatch and *_unregistered variants) are free
# choices, not locked contract values -- category-schemas.md only requires
# that they differ from the registry fixture in the stated field.
_MISMATCH_OVERRIDES = {
    "academic_certificate": {"semester_or_year": "6"},
    "institutional_id": {"holder_name": "Divya Demo"},
    "pan_like_demo": {"date_of_birth": "1999-02-20"},
    "government_certificate": {"issuing_authority_label": "Example Alternate Demo Authority"},
}
_UNREGISTERED_OVERRIDE = {"student_id": "DEMO-STU-999"}


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                pass
    return ImageFont.load_default()


def render_document(category: str, fields: dict) -> Image.Image:
    """Plain, high-contrast, OCR-friendly render: title, field rows, footer."""
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    title_font = _font(34)
    label_font = _font(22)
    footer_font = _font(18)

    draw.text((MARGIN, 40), CATEGORY_TITLES[category], fill="black", font=title_font)
    draw.line([(MARGIN, 95), (WIDTH - MARGIN, 95)], fill="black", width=2)

    y = 140
    for field_name, value in fields.items():
        label = FIELD_LABELS.get(field_name, field_name)
        display_value = "" if value is None else str(value)
        draw.text((MARGIN, y), f"{label}:", fill="black", font=label_font)
        draw.text((MARGIN + 340, y), display_value, fill="black", font=label_font)
        y += ROW_HEIGHT

    draw.line([(MARGIN, HEIGHT - 90), (WIDTH - MARGIN, HEIGHT - 90)], fill="black", width=1)
    draw.text((MARGIN, HEIGHT - 70), FOOTER_TEXT, fill="black", font=footer_font)

    return img


def degrade(img: Image.Image) -> Image.Image:
    """Downscale + low-res noise + blur + reduced contrast: aims to read like
    a bad phone photo (per Task 03 manual-verification step 5) with per-field
    OCR confidence below LOW_CONFIDENCE_THRESHOLD (0.70), while staying
    visibly a document rather than pure noise.

    Noise is applied at the downscaled resolution, before the upscale/blur
    pass -- this makes it spatially smooth ("blotchy" sensor-noise-like)
    instead of independent per-output-pixel static, which both looks more
    like a real bad photo and compresses far better as a PNG (independent
    per-pixel noise defeats PNG's compression almost entirely; smoothed
    noise doesn't -- keeps this file in the "few hundred KB" range the task
    calls for instead of multiple megabytes).
    """
    w, h = img.size
    sw = max(1, int(w * DEGRADED_DOWNSCALE_FACTOR))
    sh = max(1, int(h * DEGRADED_DOWNSCALE_FACTOR))
    small = img.resize((sw, sh), Image.BILINEAR)

    rng = random.Random(DEGRADED_SEED)
    pixels = small.load()
    for y in range(sh):
        for x in range(sw):
            r, g, b = pixels[x, y]
            n = rng.gauss(0, DEGRADED_NOISE_STDDEV)
            pixels[x, y] = (
                min(255, max(0, int(r + n))),
                min(255, max(0, int(g + n))),
                min(255, max(0, int(b + n))),
            )

    upscaled = small.resize((w, h), Image.BILINEAR)
    blurred = upscaled.filter(ImageFilter.GaussianBlur(radius=DEGRADED_BLUR_RADIUS))
    return ImageEnhance.Contrast(blurred).enhance(DEGRADED_CONTRAST_FACTOR)


def build_variant(category: str, overrides: dict | None = None) -> Image.Image:
    fields = copy.deepcopy(FIXTURES[category]["fields"])
    if overrides:
        fields.update(overrides)
    return render_document(category, fields)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # academic_certificate carries the demo narrative -> full set of four.
    match_img = build_variant("academic_certificate")
    match_img.save(OUTPUT_DIR / "academic_certificate_match.png", optimize=True)
    match_img.convert("RGB").save(OUTPUT_DIR / "academic_certificate_match.pdf", "PDF")

    build_variant("academic_certificate", _MISMATCH_OVERRIDES["academic_certificate"]).save(
        OUTPUT_DIR / "academic_certificate_mismatch.png", optimize=True
    )
    build_variant("academic_certificate", _UNREGISTERED_OVERRIDE).save(
        OUTPUT_DIR / "academic_certificate_unregistered.png", optimize=True
    )
    degrade(match_img).save(OUTPUT_DIR / "academic_certificate_degraded.png", optimize=True)

    # Remaining three categories: match + mismatch only.
    for category in ("institutional_id", "pan_like_demo", "government_certificate"):
        build_variant(category).save(OUTPUT_DIR / f"{category}_match.png", optimize=True)
        build_variant(category, _MISMATCH_OVERRIDES[category]).save(
            OUTPUT_DIR / f"{category}_mismatch.png", optimize=True
        )

    generated = sorted(p.name for p in OUTPUT_DIR.iterdir())
    print(f"Generated {len(generated)} sample documents in {OUTPUT_DIR}:")
    for name in generated:
        print(f"  {name}")


if __name__ == "__main__":
    main()
