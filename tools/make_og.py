#!/usr/bin/env python3
"""
Build the social preview card (Open Graph image) from the site's hero.

    python tools/make_og.py

Writes assets/og-cover.jpg at 1200x470. Re-run it if the wordmark changes.
"""

from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "og-cover.jpg"

# 1200x470 rather than the usual 1200x630: the wordmark is a long, short
# shape, so a 1.91:1 canvas leaves dead bands above and below it. Wide
# enough that every platform still renders a large preview.
W, H = 1200, 470
PAPER = (242, 244, 247)          # --paper
INK = (20, 23, 28)               # --ink
MARGIN = 76

WORDMARK = ROOT / "assets" / "fonts" / "Rubik80sFade-Regular.ttf"
ORB = ROOT / "assets" / "images" / "expl6.webp"


def fit_width(font_path, text, target, start=200):
    """Largest font size whose rendered text still fits `target` px wide."""
    size = start
    while size > 10:
        f = ImageFont.truetype(str(font_path), size)
        if f.getbbox(text)[2] - f.getbbox(text)[0] <= target:
            return f
        size -= 2
    return ImageFont.truetype(str(font_path), 10)


card = Image.new("RGB", (W, H), PAPER)

# the drifting orb, bleeding off the right edge as it does on the page
orb = Image.open(ORB).convert("RGB").resize((640, 640), Image.LANCZOS)
layer = Image.new("RGB", (W, H), (255, 255, 255))
layer.paste(orb, (W - 300, (H - 640) // 2))
# multiply then blend: the same "multiply at 34%" the stylesheet uses
card = Image.blend(card, ImageChops.multiply(card, layer), 0.30)

draw = ImageDraw.Draw(card)

mark_font = fit_width(WORDMARK, "ELLIOT LEE", W - MARGIN * 2)
mark_box = mark_font.getbbox("ELLIOT LEE")
mark_w = mark_box[2] - mark_box[0]
mark_h = mark_box[3] - mark_box[1]

# the wordmark is the whole card now, so centre it: horizontally on the canvas,
# and a touch above true centre, which reads as centred to the eye
x = (W - mark_w) // 2 - mark_box[0]
y = (H - mark_h) // 2 - mark_box[1] - 12
draw.text((x, y), "ELLIOT LEE", font=mark_font, fill=INK)

# no meta row: the card carries the wordmark and the line, nothing else. The
# platform already prints the domain under the preview, and the title tag
# repeats the name, so anything more here is said twice.

card.save(OUT, "JPEG", quality=88, optimize=True, progressive=True)
print(f"wrote {OUT.relative_to(ROOT)}  {W}x{H}  {OUT.stat().st_size // 1024} KB")
