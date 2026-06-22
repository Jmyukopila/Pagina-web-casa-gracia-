"""
Grab the Casa Gracia logo (the brand profile image) from its official social
profiles, using the local browser so it loads from YOUR own IP.

Strategy: open each public profile and read the <meta property="og:image">
(the profile picture) plus any high-res "profile_pic_url_hd" embedded in the
page JSON. Download all candidates into assets/logo/raw/ for you to pick from.

Run:  python grab_logo.py
Then: python make_logo.py   (cleans + exports usable formats)
"""
from __future__ import annotations

import json
import re
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

import config
from common import launch_context, accept_cookies

TARGETS = [
    ("instagram", "https://www.instagram.com/casagracia.ctg/"),
    ("facebook", "https://www.facebook.com/61570407230142"),
    ("facebook_pfbid", "https://www.facebook.com/casagracia.ctg/"),
]

OUT = config.ASSETS_DIR / "logo" / "raw"
OUT.mkdir(parents=True, exist_ok=True)


def clean(url: str) -> str:
    return unquote(url.replace("\\u0026", "&").replace("\\/", "/")).strip()


def candidates_from_page(page) -> list[str]:
    urls: list[str] = []
    # 1) Open Graph image (usually the profile picture)
    try:
        og = page.locator("meta[property='og:image']").first
        if og.count():
            c = og.get_attribute("content")
            if c:
                urls.append(c)
    except Exception:
        pass
    # 2) High-res profile pic embedded in page JSON
    html = page.content()
    for pat in (r'"profile_pic_url_hd":"(.*?)"',
                r'"profile_pic_url":"(.*?)"',
                r'"image":"(https:[^"]+?)"'):
        urls += re.findall(pat, html)
    # dedupe, clean
    out, seen = [], set()
    for u in urls:
        u = clean(u)
        if u.startswith("http") and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def main():
    found: dict[str, list[str]] = {}
    with sync_playwright() as pw:
        ctx = launch_context(pw)
        for name, url in TARGETS:
            print(f"[{name}] {url}")
            try:
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                accept_cookies(page)
                page.wait_for_timeout(3000)
                cands = candidates_from_page(page)
                found[name] = cands
                print(f"  candidates: {len(cands)}")
                for i, u in enumerate(cands):
                    try:
                        resp = ctx.request.get(u, timeout=30000)
                        if resp.ok and "image" in resp.headers.get("content-type", ""):
                            ext = resp.headers["content-type"].split("/")[-1].split(";")[0]
                            dest = OUT / f"{name}_{i}.{ext}"
                            dest.write_bytes(resp.body())
                            print(f"    + {dest.name} ({len(resp.body())//1024} KB)")
                    except Exception as e:
                        print(f"    ! download failed: {e}")
                page.close()
            except Exception as e:
                print(f"  ! {name} failed: {e}")
        ctx.close()
    (OUT.parent / "candidates.json").write_text(
        json.dumps(found, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved raw logo candidates -> {OUT.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
