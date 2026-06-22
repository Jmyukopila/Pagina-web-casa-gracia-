"""
Grab photos from the Casa Gracia Facebook page using the local browser
(persistent profile, so if you're logged into FB it sees more). Downloads
the good-quality landscape shots into web/app/static/img/fb_candidates/.

Run with system Python:  python grab_fb_photos.py
"""
import re, io, hashlib
from pathlib import Path
from urllib.parse import unquote

import requests
from PIL import Image
from playwright.sync_api import sync_playwright

PHOTOS_URL = "https://www.facebook.com/profile.php?id=61570407230142&sk=photos"
PROFILE = Path(__file__).resolve().parent / ".pw-profile"
OUT = Path(__file__).resolve().parent.parent / "web/app/static/img/fb_candidates"
OUT.mkdir(parents=True, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def collect():
    urls = set()
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE), headless=True, user_agent=UA,
            locale="es-CO", viewport={"width": 1366, "height": 900})
        pg = ctx.new_page()
        pg.goto(PHOTOS_URL, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(3000)
        # dismiss the login / cookie dialogs if present
        for sel in ("[aria-label='Cerrar']", "[aria-label='Close']",
                    "div[role='button']:has-text('Permitir todas')",
                    "div[role='button']:has-text('Allow all')"):
            try:
                pg.locator(sel).first.click(timeout=1500)
            except Exception:
                pass
        # scroll to lazy-load the photo grid
        for _ in range(12):
            pg.mouse.wheel(0, 4000)
            pg.wait_for_timeout(900)
        # 1) <img> tags
        for u in pg.eval_on_selector_all(
                "img", "els => els.map(e => e.currentSrc || e.src)"):
            if u and "fbcdn" in u:
                urls.add(u)
        # 2) URLs embedded in page JSON (escaped)
        html = pg.content()
        for u in re.findall(r"https://[a-z0-9.\-]*fbcdn\.net/[^\"'\\ )]+", html):
            urls.add(unquote(u.replace("\\u0026", "&").replace("\\/", "/")))
        ctx.close()
    return urls


def main():
    urls = collect()
    print(f"found {len(urls)} fbcdn urls")
    kept = []
    for u in urls:
        if any(x in u for x in ("static.xx", "/emoji", "/rsrc.php", "safe_image")):
            continue
        try:
            r = requests.get(u, headers={"User-Agent": UA, "Referer": "https://www.facebook.com/"}, timeout=30)
            if not r.ok or "image" not in r.headers.get("content-type", ""):
                continue
            im = Image.open(io.BytesIO(r.content)); w, h = im.size
            if w < 600 or h < 400:           # drop icons/thumbnails
                continue
            name = f"{w}x{h}_{hashlib.md5(u.encode()).hexdigest()[:6]}.jpg"
            (OUT / name).write_bytes(r.content)
            kept.append((w * h, w, h, name))
            print(f"  kept {w}x{h}  {name}")
        except Exception:
            continue
    kept.sort(reverse=True)
    print(f"\n{len(kept)} usable photos in {OUT}")
    for _, w, h, n in kept[:20]:
        print(f"  {w}x{h}  {n}")


if __name__ == "__main__":
    main()
