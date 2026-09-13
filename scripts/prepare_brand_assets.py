"""Prepare brand banner + title arts for mockup theme."""
from pathlib import Path

from PIL import Image

ROOT = Path(r"C:\Users\clove\CursorProjects\DSR EventLab Codes Page")
BRAND = ROOT / "assets" / "brand"
CURSOR_ASSETS = Path(
    r"C:\Users\clove\.cursor\projects\c-Users-clove-CursorProjects-DSR-EventLab-Codes-Page\assets"
)


def crop_banner_top(src: Path, dest: Path, keep_ratio: float = 0.58) -> None:
    """Keep top portion (wizard / build / logo); drop spare-parts table."""
    im = Image.open(src).convert("RGB")
    w, h = im.size
    cut = max(1, int(h * keep_ratio))
    out = im.crop((0, 0, w, cut))
    out.save(dest, quality=92, optimize=True)
    print(f"banner {im.size} -> {out.size} ({dest.name})")


def black_to_alpha(src: Path, dest: Path, threshold: int = 28, soft: int = 18) -> None:
    """Turn near-black into transparency so titles blend on void background."""
    im = Image.open(src).convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            lum = (r + g + b) // 3
            if lum <= threshold:
                px[x, y] = (r, g, b, 0)
            elif lum < threshold + soft:
                # soft edge
                alpha = int(255 * (lum - threshold) / soft)
                px[x, y] = (r, g, b, alpha)
    # trim transparent padding
    bbox = im.getbbox()
    if bbox:
        pad = 12
        x0, y0, x1, y1 = bbox
        x0 = max(0, x0 - pad)
        y0 = max(0, y0 - pad)
        x1 = min(w, x1 + pad)
        y1 = min(h, y1 + pad)
        im = im.crop((x0, y0, x1, y1))
    im.save(dest, optimize=True)
    print(f"alpha {src.name} -> {im.size} ({dest.name})")


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    banner_src = BRAND / "banner.jpg"
    crop_banner_top(banner_src, BRAND / "banner-hero.jpg", keep_ratio=0.56)

    for name in ("title-eventlab-track-codes.png", "title-time-attack.png"):
        src = BRAND / name
        if not src.exists() and (CURSOR_ASSETS / name).exists():
            src = CURSOR_ASSETS / name
        black_to_alpha(src, BRAND / name.replace(".png", "-blend.png"))


if __name__ == "__main__":
    main()
