"""
Log into Facebook (you do it once in the visible window) and pull the Casa
Gracia photo album in HIGH RESOLUTION.

How it works:
  1. Opens a real Chromium window at facebook.com (persistent profile).
  2. Waits until you log in -- detected via the `c_user` cookie (up to 8 min).
  3. Opens the page's photos, scrolls to load every thumbnail, then opens each
     photo in the theater viewer and grabs the FULL-SIZE image (not the thumb).
  4. Downloads them, keeps the HD ones, writes a contact sheet.

Run with system Python:  python fb_hd.py
"""
import re, io, time, hashlib
from pathlib import Path
import requests
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

PROFILE = Path(__file__).resolve().parent / ".pw-profile"
PAGE_ID = "61570407230142"
PHOTOS = f"https://www.facebook.com/profile.php?id={PAGE_ID}&sk=photos"
OUT = Path(__file__).resolve().parent.parent / "web/app/static/img/fb_hd"
OUT.mkdir(parents=True, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
LOGIN_TIMEOUT = 900       # seconds to wait for you to log in (15 min)
MAX_PHOTOS = 60


def logged_in(ctx) -> bool:
    try:
        return any(c["name"] == "c_user" for c in ctx.cookies())
    except Exception:
        return False


def context_alive(ctx) -> bool:
    """True while the browser window is still open."""
    try:
        _ = ctx.cookies()      # raises if the context/browser was closed
        return True
    except Exception:
        return False


def main():
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE), headless=False, user_agent=UA,
            locale="es-CO", viewport={"width": 1366, "height": 900},
            args=["--disable-blink-features=AutomationControlled"])
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto("https://www.facebook.com/login", wait_until="domcontentloaded", timeout=60000)

        if not logged_in(ctx):
            print(">>> INICIA SESION en la ventana de Facebook que se abrio...", flush=True)
            print(f">>> Tienes hasta {LOGIN_TIMEOUT//60} minutos. NO cierres la ventana; "
                  f"yo la cierro al terminar.", flush=True)
            waited = 0
            while waited < LOGIN_TIMEOUT:
                time.sleep(5); waited += 5
                if not context_alive(ctx):
                    print("!! La ventana se cerro antes de iniciar sesion. "
                          "Vuelve a ejecutar y dejala abierta.", flush=True)
                    return
                if logged_in(ctx):
                    break
                if waited % 30 == 0:
                    print(f"   ...esperando login ({waited}s)", flush=True)
            if not logged_in(ctx):
                print("!! No detecte inicio de sesion en el tiempo dado. Saliendo.", flush=True)
                try: ctx.close()
                except Exception: pass
                return
        print(">>> Sesion detectada. Cargando el album de fotos...", flush=True)

        # Collect photo permalinks (fbids) from the photos grid.
        pg.goto(PHOTOS, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(3500)
        fbids, stale = [], 0
        while len(fbids) < MAX_PHOTOS and stale < 4:
            hrefs = pg.eval_on_selector_all(
                "a[href*='fbid=']", "els => els.map(e => e.href)")
            before = len(fbids)
            for h in hrefs:
                m = re.search(r"fbid=(\d+)", h)
                if m and m.group(1) not in fbids:
                    fbids.append(m.group(1))
            stale = stale + 1 if len(fbids) == before else 0
            pg.mouse.wheel(0, 4000); pg.wait_for_timeout(1100)
        print(f">>> {len(fbids)} fotos encontradas. Abriendo en alta resolucion...", flush=True)

        photos = []
        for i, fbid in enumerate(fbids[:MAX_PHOTOS], 1):
            try:
                pg.goto(f"https://www.facebook.com/photo/?fbid={fbid}",
                        wait_until="domcontentloaded", timeout=40000)
                pg.wait_for_timeout(1600)
                src = pg.eval_on_selector(
                    "img[data-visualcompletion='media-vc-image'], "
                    "img[referrerpolicy='origin-when-cross-origin']",
                    "e => e ? e.src : null")
                if src and "fbcdn" in src:
                    photos.append(src)
                    print(f"  [{i}/{len(fbids)}] ok", flush=True)
            except Exception:
                print(f"  [{i}] skip", flush=True)
        ctx.close()

    # Download + keep HD
    seen, kept = set(), []
    for u in photos:
        key = re.search(r"/(\d+)_", u)
        key = key.group(1) if key else u
        if key in seen:
            continue
        seen.add(key)
        try:
            r = requests.get(u, headers={"User-Agent": UA, "Referer": "https://www.facebook.com/"}, timeout=30)
            if not r.ok:
                continue
            im = Image.open(io.BytesIO(r.content)); w, h = im.size
            if max(w, h) < 1000:        # not HD enough
                continue
            n = f"{w}x{h}_{hashlib.md5(u.encode()).hexdigest()[:6]}.jpg"
            (OUT / n).write_bytes(r.content)
            kept.append((w * h, w, h, n))
        except Exception:
            pass
    kept.sort(reverse=True)
    print(f"\n>>> {len(kept)} fotos HD guardadas en {OUT}", flush=True)
    for _, w, h, n in kept:
        print(f"   {w}x{h}  {n}", flush=True)

    # contact sheet
    if kept:
        files = [OUT / n for _, _, _, n in kept]
        cols, tw, th = 4, 360, 270
        rows = (len(files) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * th), (245, 240, 233))
        d = ImageDraw.Draw(sheet)
        for i, f in enumerate(files):
            t = Image.open(f); t.thumbnail((tw - 12, th - 26))
            x = (i % cols) * tw; y = (i // cols) * th
            sheet.paste(t, (x + 6, y + 6))
            d.rectangle([x + 2, y + 2, x + tw - 2, y + th - 2], outline=(184, 136, 80), width=2)
            d.text((x + 8, y + th - 20), f"#{i+1} {f.name}", fill=(46, 42, 38))
        sheet.save(OUT.parent / "_fbhd_sheet.png")
        print(">>> hoja de contacto: _fbhd_sheet.png", flush=True)


if __name__ == "__main__":
    main()
