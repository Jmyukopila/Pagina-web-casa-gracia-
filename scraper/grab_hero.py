"""
Pull the FULL Booking photo gallery for Casa Gracia at high resolution and keep
the wide/landscape shots that work as a website hero. Run with system Python
(has playwright + requests + Pillow).
"""
import re, io, hashlib
from pathlib import Path
import requests
from PIL import Image
from playwright.sync_api import sync_playwright

URL = "https://www.booking.com/hotel/co/casa-gracia.html?lang=en-us"
OUT = Path(__file__).resolve().parent.parent / "web/app/static/img/hero_candidates"
OUT.mkdir(parents=True, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def collect_urls():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(user_agent=UA, locale="en-US",
                        viewport={"width": 1440, "height": 900})
        pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
        for sel in ("#onetrust-accept-btn-handler", "button:has-text('Accept')"):
            try:
                pg.locator(sel).first.click(timeout=2000); break
            except Exception:
                pass
        pg.wait_for_timeout(3500)
        # try to open the gallery so lazy images load
        try:
            pg.locator("[data-testid='gallery-trigger'], .bh-photo-grid-thumb-more").first.click(timeout=3000)
            pg.wait_for_timeout(2500)
            for _ in range(6):
                pg.mouse.wheel(0, 3000); pg.wait_for_timeout(600)
        except Exception:
            pass
        html = pg.content()
        b.close()
    # every Booking listing photo URL on the page
    raw = re.findall(r"https://[a-z0-9-]+\.bstatic\.com/xdata/images/hotel/[^\"'\\ )]+", html)
    by_id = {}
    for u in raw:
        m = re.search(r"/(\d+)\.(jpe?g)", u)
        if not m:
            continue
        # force the largest standard size, keep the signature (?k=...)
        big = re.sub(r"/(max\d+x?\d*|square\d+)/", "/max1920x1080/", u)
        by_id[m.group(1)] = big
    return list(by_id.values())


def main():
    urls = collect_urls()
    print(f"found {len(urls)} unique photos")
    landscape = []
    for u in urls:
        try:
            r = requests.get(u, headers={"User-Agent": UA, "Referer": "https://www.booking.com/"}, timeout=30)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content))
            w, h = im.size
            tag = "LANDSCAPE" if w > h and w >= 1280 else "skip"
            name = f"{w}x{h}_{hashlib.md5(u.encode()).hexdigest()[:6]}.jpg"
            if w > h and w >= 1280:
                (OUT / name).write_bytes(r.content)
                landscape.append((w * h, w, h, name))
            print(f"  {tag:10} {w}x{h}")
        except Exception as e:
            print(f"  ! {e}")
    landscape.sort(reverse=True)
    print(f"\nkept {len(landscape)} landscape candidates in {OUT}")
    for px, w, h, n in landscape[:12]:
        print(f"  {w}x{h}  {n}")


if __name__ == "__main__":
    main()
