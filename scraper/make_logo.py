"""
Turn the raw Casa Gracia brand images into a clean, web-ready logo kit.

Inputs:
  - assets/logo/raw/facebook_0.jpeg   (720x720 isotype: white arch on caramel)
  - assets/logo/src/wordmark.png       (the full "CASA GRACIA" lockup)

Outputs (assets/logo/):
  svg/   vector logos (icon + wordmark, brand-color and white)
  png/   transparent high-res PNGs
  webp/  same, WebP
  favicon/ favicon.ico + apple-touch + PWA icons
  brand.md  brand color reference

Run:  python make_logo.py
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image
import vtracer

import config

LOGO = config.ASSETS_DIR / "logo"
SRC = LOGO / "src"
SVG = LOGO / "svg"
PNG = LOGO / "png"
WEBP = LOGO / "webp"
FAV = LOGO / "favicon"
for d in (SRC, SVG, PNG, WEBP, FAV):
    d.mkdir(parents=True, exist_ok=True)

# Brand palette (sampled from the official assets)
BRAND = "#B88850"          # caramel / ocre  (rgb 184,136,80)
BRAND_RGB = (184, 136, 80)
WHITE = "#FFFFFF"

ICON_SRC = LOGO / "raw" / "facebook_0.jpeg"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def smoothstep(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def autocrop_content(src: Image.Image, pad: int = 6) -> Image.Image:
    """Crop to the wordmark's real bounding box, dropping thin stray border
    lines (e.g. a 1px divider at the edge) that aren't part of the logo."""
    rgb = np.asarray(src.convert("RGB")).astype(float)
    lum = rgb.mean(axis=2)
    ink = lum < 205

    def keep_span(profile):
        # contiguous ink runs; drop runs <=2px wide (stray lines)
        runs, inrun, start = [], False, 0
        for i, c in enumerate(profile):
            if c > 0 and not inrun:
                start, inrun = i, True
            elif c == 0 and inrun:
                runs.append((start, i - 1)); inrun = False
        if inrun:
            runs.append((start, len(profile) - 1))
        runs = [(s, e) for s, e in runs if (e - s + 1) > 2]
        if not runs:
            return 0, len(profile) - 1
        return runs[0][0], runs[-1][1]

    x0, x1 = keep_span(ink.sum(axis=0))
    y0, y1 = keep_span(ink.sum(axis=1))
    x0 = max(0, x0 - pad); y0 = max(0, y0 - pad)
    x1 = min(src.width - 1, x1 + pad); y1 = min(src.height - 1, y1 + pad)
    return src.crop((x0, y0, x1 + 1, y1 + 1))


def save_png(arr_rgba: np.ndarray, path: Path):
    Image.fromarray(arr_rgba, "RGBA").save(path)
    print(f"  png  -> {path.relative_to(config.ROOT)}")


def recolor_mark(src: Image.Image, color, mark_is_bright: bool) -> np.ndarray:
    """Return RGBA where the 'mark' is `color` on a transparent background.
    mark_is_bright=True  -> mark is the bright/white pixels (icon badge)
    mark_is_bright=False -> mark is the dark/caramel pixels (wordmark on white)
    """
    rgb = np.asarray(src.convert("RGB")).astype(float)
    lum = rgb.mean(axis=2)
    if mark_is_bright:
        alpha = smoothstep(lum, 165, 235)          # bg(133) -> 0, white(255) -> 1
    else:
        alpha = smoothstep(255 - lum, 30, 120)     # white -> 0, caramel -> 1
    h, w = lum.shape
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = color
    out[..., 3] = (alpha * 255).astype(np.uint8)
    return out


def binarize(src: Image.Image, mark_is_bright: bool, upscale: int = 1) -> Path:
    """Write a clean black-on-white PNG for vectorization. Returns its path."""
    if upscale > 1:
        src = src.resize((src.width * upscale, src.height * upscale), Image.LANCZOS)
    rgb = np.asarray(src.convert("RGB")).astype(float)
    lum = rgb.mean(axis=2)
    mark = lum > 190 if mark_is_bright else lum < 205
    out = np.where(mark[..., None], 0, 255).astype(np.uint8)
    out = np.repeat(out, 3, axis=2)
    tmp = SRC / ("_bin_bright.png" if mark_is_bright else "_bin_dark.png")
    Image.fromarray(out, "RGB").save(tmp)
    return tmp


def vectorize(bin_png: Path, out_svg: Path, fill: str):
    vtracer.convert_image_to_svg_py(
        str(bin_png), str(out_svg),
        colormode="binary", mode="spline",
        filter_speckle=4, corner_threshold=60, path_precision=8,
    )
    svg = out_svg.read_text(encoding="utf-8")
    # vtracer fills traced shapes black; recolor to the requested fill.
    svg = re.sub(r'fill="#0+"', f'fill="{fill}"', svg, flags=re.I)
    svg = re.sub(r'fill="black"', f'fill="{fill}"', svg, flags=re.I)
    # Add a viewBox so the logo scales responsively (vtracer omits it).
    m = re.search(r'<svg[^>]*\bwidth="(\d+)"[^>]*\bheight="(\d+)"', svg)
    if m and "viewBox" not in svg:
        w, h = m.group(1), m.group(2)
        svg = svg.replace("<svg ", f'<svg viewBox="0 0 {w} {h}" ', 1)
    out_svg.write_text(svg, encoding="utf-8")
    print(f"  svg  -> {out_svg.relative_to(config.ROOT)}  (fill {fill})")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    icon = Image.open(ICON_SRC)
    wordmark_path = SRC / "wordmark.png"
    if not wordmark_path.exists():
        print(f"! Missing {wordmark_path}. Copy the full 'CASA GRACIA' logo there "
              f"and re-run.")
        wordmark = None
    else:
        wordmark = autocrop_content(Image.open(wordmark_path))

    # ---- transparent PNGs (pixel-perfect, antialiased) -------------------
    print("[png] transparent rasters")
    icon_brand = recolor_mark(icon, BRAND_RGB, mark_is_bright=True)
    icon_white = recolor_mark(icon, (255, 255, 255), mark_is_bright=True)
    save_png(icon_brand, PNG / "icon-brand-720.png")
    save_png(icon_white, PNG / "icon-white-720.png")
    # the original filled badge (caramel bg + white mark), squared
    icon.convert("RGB").save(PNG / "icon-badge-720.png")
    print(f"  png  -> {(PNG/'icon-badge-720.png').relative_to(config.ROOT)}")

    if wordmark is not None:
        wm_trans = recolor_mark(wordmark, BRAND_RGB, mark_is_bright=False)
        save_png(wm_trans, PNG / "wordmark-brand.png")

    # ---- SVG (vector) ----------------------------------------------------
    print("[svg] vectorizing")
    icon_bin = binarize(icon, mark_is_bright=True)
    vectorize(icon_bin, SVG / "icon-brand.svg", BRAND)
    vectorize(icon_bin, SVG / "icon-white.svg", WHITE)
    if wordmark is not None:
        wm_bin = binarize(wordmark, mark_is_bright=False, upscale=4)
        vectorize(wm_bin, SVG / "logo-wordmark.svg", BRAND)

    # ---- WebP ------------------------------------------------------------
    print("[webp]")
    for p in PNG.glob("*.png"):
        Image.open(p).save(WEBP / (p.stem + ".webp"), "WEBP", quality=92, method=6)
    print(f"  -> {WEBP.relative_to(config.ROOT)}/*.webp")

    # ---- favicons / app icons (from the filled badge) --------------------
    print("[favicon]")
    badge = icon.convert("RGB")
    badge.resize((180, 180), Image.LANCZOS).save(FAV / "apple-touch-icon.png")
    badge.resize((192, 192), Image.LANCZOS).save(FAV / "icon-192.png")
    badge.resize((512, 512), Image.LANCZOS).save(FAV / "icon-512.png")
    badge.resize((32, 32), Image.LANCZOS).save(FAV / "favicon-32.png")
    badge.resize((16, 16), Image.LANCZOS).save(FAV / "favicon-16.png")
    badge.save(FAV / "favicon.ico",
               sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"  -> {FAV.relative_to(config.ROOT)}/ (ico, apple-touch, 192, 512, 32, 16)")

    # ---- brand reference -------------------------------------------------
    (LOGO / "brand.md").write_text(f"""# Casa Gracia — Brand assets

**Primary color (caramel / ocre):** `{BRAND}`  ·  rgb{BRAND_RGB}
**On dark backgrounds:** use the white logo variants.

## Files
- `svg/icon-brand.svg` / `icon-white.svg` — isotype (the arch monogram), vector
- `svg/logo-wordmark.svg` — full "CASA GRACIA" lockup, vector
- `png/*.png` — transparent, high-res rasters
- `webp/*.webp` — smaller modern format for the web
- `favicon/` — `favicon.ico`, `apple-touch-icon.png` (180), PWA `icon-192/512.png`

## Web usage
```html
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon/favicon-32.png">
<link rel="apple-touch-icon" href="/favicon/apple-touch-icon.png">
<!-- header logo -->
<img src="/svg/logo-wordmark.svg" alt="Casa Gracia Hotel Boutique" height="40">
```
Prefer the **SVG** for the site header (crisp at any size). Use PNG/WebP only
where SVG isn't supported.
""", encoding="utf-8")
    print(f"  brand.md -> {(LOGO/'brand.md').relative_to(config.ROOT)}")

    # cleanup temp binaries
    for t in SRC.glob("_bin_*.png"):
        t.unlink()
    print("\nDone. Logo kit in assets/logo/")


if __name__ == "__main__":
    main()
