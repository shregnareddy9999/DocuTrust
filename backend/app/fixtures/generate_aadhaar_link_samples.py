"""Generate synthetic Aadhaar-link sample assets.

The outputs are permanent demo fixtures, separate from temporary uploads. They
avoid official seals, emblems, security features, and real personal data.

Run from backend/ with:
    python -m app.fixtures.generate_aadhaar_link_samples
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

from .aadhaar_link_data import AADHAAR_UPLOAD_MARKER, LINKED_ASSETS, WATERMARK_TEXT


OUTPUT_DIR = Path(__file__).parent / "sample_documents"
WIDTH = 1100
HEIGHT = 760
MARGIN = 62


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        Path(r"C:\Windows\Fonts\arialbd.ttf") if bold else Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibrib.ttf") if bold else Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        if bold
        else Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf") if bold else Path("/Library/Fonts/Arial.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    raise RuntimeError("No TrueType font found for Aadhaar-link sample generation.")


def _draw_watermark(draw: ImageDraw.ImageDraw) -> None:
    font = _font(34, bold=True)
    overlay_text = "SYNTHETIC DEMO"
    bbox = draw.textbbox((0, 0), overlay_text, font=font)
    x = (WIDTH - (bbox[2] - bbox[0])) // 2
    y = HEIGHT // 2 - 50
    draw.text((x, y), overlay_text, fill=(224, 231, 255), font=font)


def render_asset(document_ref: str) -> Image.Image:
    asset = LINKED_ASSETS[document_ref]
    img = Image.new("RGB", (WIDTH, HEIGHT), "#ffffff")
    draw = ImageDraw.Draw(img)

    title_font = _font(34, bold=True)
    label_font = _font(22, bold=True)
    value_font = _font(22)
    small_font = _font(18)
    mono_font = _font(20)

    _draw_watermark(draw)

    draw.rounded_rectangle(
        (MARGIN, 44, WIDTH - MARGIN, HEIGHT - 44),
        radius=16,
        outline="#cbd5e1",
        width=3,
        fill=None,
    )
    draw.rectangle((MARGIN, 44, WIDTH - MARGIN, 128), fill="#eff6ff")
    draw.text((MARGIN + 28, 70), asset.title, fill="#0f172a", font=title_font)
    draw.text((MARGIN + 28, 142), WATERMARK_TEXT, fill="#b91c1c", font=label_font)

    rows = [
        ("Reference", asset.document_ref),
        ("Demo Source", asset.issuer_label),
        ("Synthetic Value", asset.demo_value),
        ("Additional Demo Detail", asset.secondary_value),
        ("Status", asset.status_label),
    ]

    y = 220
    for label, value in rows:
        draw.text((MARGIN + 44, y), f"{label}:", fill="#334155", font=label_font)
        draw.text((MARGIN + 360, y), value, fill="#0f172a", font=mono_font if label == "Reference" else value_font)
        y += 64

    draw.line((MARGIN + 44, HEIGHT - 138, WIDTH - MARGIN - 44, HEIGHT - 138), fill="#cbd5e1", width=2)
    draw.text(
        (MARGIN + 44, HEIGHT - 112),
        "This fixture is for the DocuTrust hackathon demo only. It is not issued by any real authority.",
        fill="#475569",
        font=small_font,
    )
    draw.text(
        (MARGIN + 44, HEIGHT - 82),
        "No official security features, seals, signatures, or real personal identifiers are represented.",
        fill="#475569",
        font=small_font,
    )
    return img


def render_aadhaar_card(aadhaar_ref: str, citizen_ref: str, demo_name: str) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), "#ffffff")
    draw = ImageDraw.Draw(img)

    title_font = _font(34, bold=True)
    label_font = _font(22, bold=True)
    value_font = _font(22)
    small_font = _font(18)
    mono_font = _font(21)

    _draw_watermark(draw)
    draw.rounded_rectangle((MARGIN, 44, WIDTH - MARGIN, HEIGHT - 44), radius=18, outline="#93c5fd", width=3)
    draw.rectangle((MARGIN, 44, WIDTH - MARGIN, 132), fill="#eff6ff")
    draw.text((MARGIN + 28, 70), "DocuTrust Synthetic Aadhaar Demo Card", fill="#0f172a", font=title_font)
    draw.text((MARGIN + 28, 150), WATERMARK_TEXT, fill="#b91c1c", font=label_font)

    rows = [
        ("Demo Marker", AADHAAR_UPLOAD_MARKER),
        ("Aadhaar Demo Reference", aadhaar_ref),
        ("Citizen Demo Reference", citizen_ref),
        ("Demo Name", demo_name),
        ("Masked Display", f"DEMO-XXXX-{aadhaar_ref[-4:]}"),
    ]
    y = 230
    for label, value in rows:
        draw.text((MARGIN + 44, y), f"{label}:", fill="#334155", font=label_font)
        draw.text((MARGIN + 390, y), value, fill="#0f172a", font=mono_font if "Reference" in label or label == "Demo Marker" else value_font)
        y += 64

    draw.line((MARGIN + 44, HEIGHT - 138, WIDTH - MARGIN - 44, HEIGHT - 138), fill="#cbd5e1", width=2)
    draw.text((MARGIN + 44, HEIGHT - 112), "Use this fixture only for the DocuTrust synthetic Aadhaar Link demo.", fill="#475569", font=small_font)
    draw.text((MARGIN + 44, HEIGHT - 82), "This is not issued by UIDAI and contains no real Aadhaar number or security feature.", fill="#475569", font=small_font)
    return img


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for document_ref, asset in LINKED_ASSETS.items():
        img = render_asset(document_ref)
        target = OUTPUT_DIR / asset.asset_filename
        if asset.mime_type == "application/pdf":
            img.save(target, "PDF", resolution=120.0)
        elif asset.mime_type == "image/jpeg":
            img.save(target, "JPEG", quality=92, optimize=True)
        else:
            img.save(target, "PNG", optimize=True)

    aadhaar_samples = [
        ("aadhaar_demo_card_aad_10001.png", "AAD-10001", "CIT-10001", "Aarav Demo"),
        ("aadhaar_demo_card_aad_10002.png", "AAD-10002", "CIT-10002", "Meera Demo"),
    ]
    for filename, aadhaar_ref, citizen_ref, demo_name in aadhaar_samples:
        img = render_aadhaar_card(aadhaar_ref, citizen_ref, demo_name)
        metadata = PngInfo()
        metadata.add_text("DocuTrustDemoMarker", AADHAAR_UPLOAD_MARKER)
        metadata.add_text("AadhaarDemoReference", aadhaar_ref)
        metadata.add_text("CitizenDemoReference", citizen_ref)
        img.save(OUTPUT_DIR / filename, "PNG", pnginfo=metadata, optimize=True)

    print(f"Generated {len(LINKED_ASSETS) + len(aadhaar_samples)} Aadhaar-link sample assets in {OUTPUT_DIR}")
    for asset in LINKED_ASSETS.values():
        print(f"  {asset.asset_filename}")
    for filename, *_ in aadhaar_samples:
        print(f"  {filename}")


if __name__ == "__main__":
    main()
