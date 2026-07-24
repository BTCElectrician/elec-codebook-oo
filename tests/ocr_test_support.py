"""Synthetic image-only PDF fixtures generated at test time."""

import io
from pathlib import Path


def create_image_only_pdf(path: Path) -> None:
    """Create one scanned-looking page with no embedded text layer."""

    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1700, 2200), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=42)
    lines = [
        "Synthetic Scanned Manual",
        "Article 7. Training Clearances",
        "7.1 Invented Clearance",
        "The invented scan clearance is forty-two training units.",
    ]
    for index, line in enumerate(lines):
        draw.text((160, 240 + index * 150), line, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PDF", resolution=220)
    path.write_bytes(buffer.getvalue())
    image.close()
