"""
Download every image URL collected by the scrapers into /assets.

Reads all data/raw/*.json files, gathers their "image_urls" arrays, dedupes,
and downloads into assets/<source>/. Skips files already on disk.

Run:  python download_images.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import requests

import config

HEADERS = {"User-Agent": config.USER_AGENT, "Referer": "https://www.google.com/"}


def gather() -> dict[str, set[str]]:
    """Map source name -> set of image URLs, from every raw dump."""
    by_source: dict[str, set[str]] = {}
    for jf in config.RAW_DIR.glob("*.json"):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        src = data.get("source", "misc").split(".")[0]
        bucket = by_source.setdefault(src, set())
        for u in data.get("image_urls", []) or []:
            bucket.add(u)
    return by_source


def fname_for(url: str) -> str:
    base = Path(urlparse(url).path).name or "img"
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    if "." not in base:
        base += ".jpg"
    stem, ext = base.rsplit(".", 1)
    return f"{stem[:40]}_{h}.{ext}"


def main():
    by_source = gather()
    if not by_source:
        print("No raw scrape files found. Run scrape_booking.py / scrape_airbnb.py first.")
        return
    total = 0
    for src, urls in by_source.items():
        out = config.ASSETS_DIR / src
        out.mkdir(parents=True, exist_ok=True)
        print(f"[{src}] {len(urls)} unique image URLs -> {out.relative_to(config.ROOT)}")
        for u in sorted(urls):
            dest = out / fname_for(u)
            if dest.exists():
                continue
            try:
                r = requests.get(u, headers=HEADERS, timeout=30)
                r.raise_for_status()
                dest.write_bytes(r.content)
                total += 1
                print(f"  + {dest.name}  ({len(r.content)//1024} KB)")
            except Exception as e:
                print(f"  ! {u[:70]}... -> {e}")
    print(f"\nDone. {total} new images downloaded into {config.ASSETS_DIR.relative_to(config.ROOT)}/")


if __name__ == "__main__":
    main()
