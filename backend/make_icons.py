"""Generate PWA / iOS home-screen icons into frontend/public/."""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public"
SIZE = 512


def pentagon(cx, cy, r, rot=-90):
    pts = []
    for k in range(5):
        ang = math.radians(rot + k * 72)
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def render():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # rounded green background with a subtle vertical gradient
    for y in range(SIZE):
        t = y / SIZE
        r = int(0x16 + (0x0b - 0x16) * t)
        g = int(0xC6 + (0x83 - 0xC6) * t)
        b = int(0x4B + (0x2b - 0x4b) * t)
        d.line([(0, y), (SIZE, y)], fill=(r, g, b, 255))
    # mask to rounded square
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE, SIZE], radius=110, fill=255)
    img.putalpha(mask)
    d = ImageDraw.Draw(img)

    # soccer ball
    cx, cy, R = 256, 232, 150
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(255, 255, 255, 255))
    # central black pentagon + 5 surrounding ones (classic look)
    d.polygon(pentagon(cx, cy, 52), fill=(17, 24, 40, 255))
    for k in range(5):
        ang = math.radians(-90 + k * 72)
        px = cx + 104 * math.cos(ang)
        py = cy + 104 * math.sin(ang)
        d.polygon(pentagon(px, py, 30, rot=-90 + k * 72 + 36), fill=(17, 24, 40, 255))

    # "2026"
    font = None
    for path in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
        "/Library/Fonts/Arial.ttf",
    ]:
        try:
            font = ImageFont.truetype(path, 96)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    text = "2026"
    tb = d.textbbox((0, 0), text, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    d.text(((SIZE - tw) / 2 - tb[0], 410 - th / 2 - tb[1]), text,
           font=font, fill=(255, 255, 255, 255))
    return img


def main():
    base = render()
    OUT.mkdir(parents=True, exist_ok=True)
    base.resize((512, 512)).save(OUT / "icon-512.png")
    base.resize((192, 192)).save(OUT / "icon-192.png")
    base.resize((180, 180)).save(OUT / "apple-touch-icon.png")
    # opaque favicon
    fav = Image.new("RGB", (512, 512), (11, 16, 32))
    fav.paste(base, (0, 0), base)
    fav.resize((64, 64)).save(OUT / "favicon.png")
    print("icons written to", OUT)


if __name__ == "__main__":
    main()
