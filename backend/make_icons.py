"""Generate PWA / iOS home-screen icons into frontend/public/.

A golden World Cup trophy on a green gradient, with a neatly centered "2026".
Tries to render the 🏆 emoji (Apple Color Emoji); falls back to a drawn cup.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public"
SIZE = 512
GOLD = (245, 200, 66)
GOLD_DARK = (197, 150, 30)


def _bg():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(SIZE):
        t = y / SIZE
        r = int(0x16 + (0x0b - 0x16) * t)
        g = int(0xC6 + (0x83 - 0xC6) * t)
        b = int(0x4B + (0x2b - 0x4b) * t)
        d.line([(0, y), (SIZE, y)], fill=(r, g, b, 255))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE, SIZE], radius=112, fill=255)
    img.putalpha(mask)
    return img


def _emoji_trophy(img):
    """Try Apple Color Emoji; return True on success."""
    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Apple Color Emoji.ttc", 160
        )
        layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text(
            (256, 205), "🏆", font=font, anchor="mm", embedded_color=True
        )
        img.alpha_composite(layer)
        return True
    except Exception:
        return False


def _drawn_trophy(img):
    """Fallback: a clean golden cup drawn with primitives."""
    d = ImageDraw.Draw(img)
    cx = 256
    # handles
    for sx in (-1, 1):
        d.ellipse([cx + sx * 150 - 34, 120, cx + sx * 150 + 34, 210],
                  outline=GOLD, width=18)
    # cup bowl
    d.polygon([(160, 110), (352, 110), (322, 210), (256, 250), (190, 210)], fill=GOLD)
    d.ellipse([160, 92, 352, 132], fill=GOLD)
    d.ellipse([182, 100, 330, 124], fill=GOLD_DARK)
    # stem + base
    d.rectangle([244, 248, 268, 300], fill=GOLD)
    d.polygon([(206, 300), (306, 300), (322, 340), (190, 340)], fill=GOLD)
    d.rounded_rectangle([196, 338, 316, 360], radius=8, fill=GOLD_DARK)


def render():
    img = _bg()
    if not _emoji_trophy(img):
        _drawn_trophy(img)

    # "2026" — centered with anchor for perfect alignment
    d = ImageDraw.Draw(img)
    font = None
    for path in ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"]:
        try:
            font = ImageFont.truetype(path, 92)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    d.text((256, 405), "2026", font=font, anchor="mm",
           fill=(255, 255, 255, 255))
    return img


def main():
    base = render()
    OUT.mkdir(parents=True, exist_ok=True)
    base.resize((512, 512)).save(OUT / "icon-512.png")
    base.resize((192, 192)).save(OUT / "icon-192.png")
    base.resize((180, 180)).save(OUT / "apple-touch-icon.png")
    fav = Image.new("RGB", (512, 512), (11, 16, 32))
    fav.paste(base, (0, 0), base)
    fav.resize((64, 64)).save(OUT / "favicon.png")
    print("icons written to", OUT)


if __name__ == "__main__":
    main()
