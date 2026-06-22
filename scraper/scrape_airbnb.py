"""
Scrape each Casa Gracia Airbnb room listing from YOUR OWN browser/IP.

What it pulls per listing:
  - Title (h1)
  - Visible price
  - The embedded JSON state blob (#data-deferred-state-0) -- contains the full
    description, amenities, photos, house rules, review summary
  - JSON-LD
  - Photo URLs (muscache.com)

Run:  python scrape_airbnb.py
A real Chromium window opens. Log into YOUR host account once if you want the
host-side data; the persistent profile remembers it.

NOTE: Airbnb's ToS restricts automated access. Use on YOUR OWN listings, gently.
For production data prefer the Airbnb API available to professional hosts /
channel managers.
"""
from __future__ import annotations

from playwright.sync_api import sync_playwright

import config
from common import (launch_context, accept_cookies, extract_json_ld,
                    extract_json_script, collect_image_urls, save_raw, polite_pause)


def scrape_one(ctx, room: dict) -> dict:
    url = f"https://www.airbnb.com/rooms/{room['id']}?currency={config.CURRENCY}"
    print(f"[airbnb] {room['label']} -> {url}")
    page = ctx.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    accept_cookies(page)
    page.wait_for_timeout(3500)

    try:
        title = page.locator("h1").first.inner_text().strip()
    except Exception:
        title = None

    price = None
    for sel in ("[data-testid='price-availability-row']",
                "span:has-text('per night')", "div._1jo4hgw", "span._tyxjp1"):
        try:
            el = page.locator(sel).first
            if el.count() and el.inner_text().strip():
                price = el.inner_text().strip()
                break
        except Exception:
            continue

    payload = {
        "source": "airbnb.com",
        "room_id": room["id"],
        "label": room["label"],
        "url": url,
        "title": title,
        "price": price,
        "json_ld": extract_json_ld(page),
        "deferred_state": extract_json_script(page, "data-deferred-state-0"),
        "image_urls": collect_image_urls(page),
    }
    page.close()
    return payload


def main():
    with sync_playwright() as pw:
        ctx = launch_context(pw)
        for room in config.AIRBNB_ROOMS:
            try:
                data = scrape_one(ctx, room)
                save_raw(f"airbnb_{room['id']}", data)
                print(f"  images: {len(data['image_urls'])} | "
                      f"state blob: {'yes' if data['deferred_state'] else 'no'}")
            except Exception as e:
                print(f"  ! failed {room['label']}: {e}")
            polite_pause()
        ctx.close()


if __name__ == "__main__":
    main()
