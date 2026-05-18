"""
Build MakeAGIF.ico (multi-resolution) from the AI-generated PNG.

Run:
    python _make_icon.py

Produces:
    MakeAGIF.ico  -- contains 256/128/64/48/32/16 PNG-encoded layers.
    icon_512.png  -- preview / source for the .ico (square crop).
"""
import os
from PIL import Image, ImageDraw

SRC = r"C:\Users\matias.szteinberg\.cursor\projects\f-PERSONAL-TOOLS\assets\makeagif_icon.png"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PNG = os.path.join(HERE, "icon_512.png")
OUT_ICO = os.path.join(HERE, "MakeAGIF.ico")

# 1. Open and crop to a centered square (the AI canvas is 16:9-ish; the
#    icon rounded-square sits in the middle).
im = Image.open(SRC).convert("RGBA")
w, h = im.size
side = min(w, h)
left = (w - side) // 2
top = (h - side) // 2
im_sq = im.crop((left, top, left + side, top + side))

# 2. Round the corners with an alpha mask so the icon reads as a
#    proper Windows app icon (no dark bezel around the rounded square).
def round_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask

# Resize to a clean 1024 base, apply rounded mask (~22% radius matches
# Windows 11 / macOS Big Sur style superellipse-ish corners well enough).
base = im_sq.resize((1024, 1024), Image.LANCZOS)
mask = round_mask(1024, 224)
base.putalpha(mask)

# 3. Save 512px PNG preview.
base.resize((512, 512), Image.LANCZOS).save(OUT_PNG, "PNG")

# 4. Build multi-resolution .ico. Windows uses 16/32/48/256 most often;
#    we include 64 and 128 for crisp scaling on hi-DPI taskbars.
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
base.save(OUT_ICO, format="ICO", sizes=sizes)

print(f"OK: {OUT_ICO}")
print(f"OK: {OUT_PNG}")
