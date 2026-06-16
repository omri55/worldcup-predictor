"""Render trophy.svg into the PWA / iOS icons (needs `rsvg-convert`: brew install librsvg)."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SVG = HERE / "trophy.svg"
OUT = HERE.parent / "frontend" / "public"
BG = "#06070e"  # fill the rounded corners so icons are opaque squares

SIZES = {512: "icon-512.png", 192: "icon-192.png", 180: "apple-touch-icon.png", 64: "favicon.png"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for size, name in SIZES.items():
        subprocess.run(
            ["rsvg-convert", "-w", str(size), "-h", str(size), "-b", BG,
             str(SVG), "-o", str(OUT / name)],
            check=True,
        )
    print("icons written to", OUT)


if __name__ == "__main__":
    main()
