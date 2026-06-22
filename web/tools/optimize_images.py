"""Generate optimized WebP (and mobile-sized) variants of the site images.

Run after adding/replacing photos:

    .venv/Scripts/python tools/optimize_images.py

What it does (idempotent — skips up-to-date outputs):
- Every `static/img/{hero,rooms,fb_hd}/*.jpg` gets a sibling `.webp` (~quality
  80). WebP is typically 25-45% smaller than JPEG at the same quality and is
  supported by all current browsers; the original JPG stays as a fallback.
- Hero photos (used as full-bleed backgrounds) additionally get a `-mobile`
  variant capped at 768px wide, in both WebP and JPG, so phones download a
  small image instead of the full desktop one.

Templates/CSS reference the WebP via <picture> and CSS image-set(), always with
a JPG fallback, so nothing breaks on older clients.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

IMG_ROOT = Path(__file__).resolve().parent.parent / "app" / "static" / "img"
DIRS = ["hero", "rooms", "fb_hd"]

WEBP_QUALITY = 80
MAX_DESKTOP_W = 1920      # cap oversized originals
MOBILE_W = 768            # phone hero width


def _newer(src: Path, dst: Path) -> bool:
    """True if dst is missing or older than src (so we (re)generate it)."""
    return not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime


def _save_webp(im: Image.Image, dst: Path) -> None:
    im.save(dst, "WEBP", quality=WEBP_QUALITY, method=6)


def _downscaled(im: Image.Image, max_w: int) -> Image.Image:
    if im.width <= max_w:
        return im
    h = round(im.height * max_w / im.width)
    return im.resize((max_w, h), Image.LANCZOS)


def process(jpg: Path, is_hero: bool) -> list[str]:
    out: list[str] = []
    with Image.open(jpg) as im:
        im = im.convert("RGB")

        webp = jpg.with_suffix(".webp")
        if _newer(jpg, webp):
            _save_webp(_downscaled(im, MAX_DESKTOP_W), webp)
            out.append(webp.name)

        if is_hero:
            small = _downscaled(im, MOBILE_W)
            m_webp = jpg.with_name(f"{jpg.stem}-mobile.webp")
            m_jpg = jpg.with_name(f"{jpg.stem}-mobile.jpg")
            if _newer(jpg, m_webp):
                _save_webp(small, m_webp)
                out.append(m_webp.name)
            if _newer(jpg, m_jpg):
                small.save(m_jpg, "JPEG", quality=82, optimize=True, progressive=True)
                out.append(m_jpg.name)
    return out


def main() -> None:
    total_src = 0
    total_made = 0
    for d in DIRS:
        folder = IMG_ROOT / d
        if not folder.is_dir():
            continue
        for jpg in sorted(folder.glob("*.jpg")):
            if jpg.stem.endswith("-mobile"):
                continue  # don't re-process generated variants
            total_src += 1
            made = process(jpg, is_hero=(d == "hero"))
            total_made += len(made)
            if made:
                print(f"  {d}/{jpg.name} -> {', '.join(made)}")
    print(f"Done. Processed {total_src} source images, wrote {total_made} files.")


if __name__ == "__main__":
    main()
