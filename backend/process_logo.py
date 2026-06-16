"""Turn the official WC26 logo photo into square app icons."""
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "trophy-photo.jpg"
OUT = ROOT / "frontend" / "public"
BG = (255, 255, 255)


def trim_to_content(im):
    """Crop away the white margins around the logo."""
    rgb = im.convert("RGB")
    bg = Image.new("RGB", rgb.size, BG)
    diff = ImageChops.difference(rgb, bg).convert("L").point(lambda p: 255 if p > 18 else 0)
    box = diff.getbbox()
    return rgb.crop(box) if box else rgb


def remove_fifa(im):
    """Paint out the white 'FIFA' wordmark (it sits in black, so fill it black)."""
    import numpy as np

    arr = np.array(im)
    h, w, _ = arr.shape
    # This band (below the gold base, central column) is solid black except the
    # white "FIFA" wordmark — so fill it black entirely to erase it cleanly.
    y0, y1 = int(h * 0.785), int(h * 0.935)
    x0, x1 = int(w * 0.17), int(w * 0.83)
    arr[y0:y1, x0:x1] = (0, 0, 0)
    return Image.fromarray(arr)


def square_pad(im, pad_ratio=0.1):
    side = max(im.size)
    pad = int(side * pad_ratio)
    canvas = Image.new("RGB", (side + 2 * pad, side + 2 * pad), BG)
    canvas.paste(im, ((canvas.width - im.width) // 2, (canvas.height - im.height) // 2))
    return canvas


def main():
    logo = square_pad(remove_fifa(trim_to_content(Image.open(SRC))))
    OUT.mkdir(parents=True, exist_ok=True)
    for size, name in {512: "icon-512.png", 192: "icon-192.png",
                       180: "apple-touch-icon.png", 64: "favicon.png"}.items():
        logo.resize((size, size), Image.LANCZOS).save(OUT / name)
    print(f"icons written from {SRC.name} (content {logo.size})")


if __name__ == "__main__":
    main()
