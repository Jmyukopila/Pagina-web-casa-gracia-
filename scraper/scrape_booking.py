"""
Scrape the Casa Gracia Booking.com page from YOUR OWN browser/IP.

What it pulls:
  - All JSON-LD (name, address, geo, aggregateRating, images)
  - The live room table for the dates in config.py (room name, occupancy, price)
  - Photo gallery image URLs

Run:  python scrape_booking.py
First run: a real Chromium window opens. If Booking shows a CAPTCHA/consent,
solve it once -- the persistent profile remembers it for next time.

NOTE: Booking's ToS restricts automated access. Use this on YOUR OWN property
listing, gently (the built-in delay is intentional). For bulk/production data,
prefer the Booking.com Connectivity/Content API via your Extranet.
"""
from __future__ import annotations

from playwright.sync_api import sync_playwright

import config
from common import (launch_context, accept_cookies, extract_json_ld,
                    collect_image_urls, save_raw, polite_pause)


def build_url() -> str:
    return (f"{config.BOOKING_URL}"
            f"?checkin={config.CHECKIN}&checkout={config.CHECKOUT}"
            f"&group_adults={config.ADULTS}&no_rooms=1"
            f"&selected_currency={config.CURRENCY}&lang=en-us")


def parse_rooms(page) -> list[dict]:
    """Read the #hprt-table room/price grid. Selectors are best-effort with
    fallbacks because Booking changes class names periodically."""
    rooms: list[dict] = []
    rows = page.locator("#hprt-table tr.js-rt-block-row, #hprt-table tbody tr")
    last_room_name = None
    for i in range(rows.count()):
        row = rows.nth(i)
        try:
            name_el = row.locator(".hprt-roomtype-icon-link, a.hprt-roomtype-link").first
            name = name_el.inner_text().strip() if name_el.count() else None
        except Exception:
            name = None
        if name:
            last_room_name = name
        # occupancy
        occ = None
        try:
            occ_el = row.locator(".hprt-occupancy-occupancy-info, .bui-u-sr-only").first
            if occ_el.count():
                occ = occ_el.inner_text().strip()
        except Exception:
            pass
        # price
        price = None
        for psel in (".prco-valign-middle-helper", ".bui-price-display__value",
                     "[data-testid='price-and-discounted-price']", ".hprt-price-price"):
            try:
                pe = row.locator(psel).first
                if pe.count() and pe.inner_text().strip():
                    price = pe.inner_text().strip()
                    break
            except Exception:
                continue
        if price or name:
            rooms.append({"room": last_room_name, "occupancy": occ, "price": price})
    return rooms


def main():
    url = build_url()
    print(f"[booking] {url}")
    with sync_playwright() as pw:
        ctx = launch_context(pw)
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        accept_cookies(page)
        page.wait_for_timeout(3000)
        try:
            page.wait_for_selector("#hprt-table, #hp_hotel_name, h2.pp-header__title",
                                   timeout=20000)
        except Exception:
            print("  ! room table not found (CAPTCHA? not logged in?) -- still "
                  "dumping what loaded.")

        json_ld = extract_json_ld(page)
        rooms = parse_rooms(page)
        images = collect_image_urls(page)

        try:
            title = page.locator("#hp_hotel_name, h2.pp-header__title").first.inner_text().strip()
        except Exception:
            title = None

        payload = {
            "source": "booking.com",
            "url": url,
            "checkin": config.CHECKIN,
            "checkout": config.CHECKOUT,
            "title": title,
            "rooms": rooms,
            "json_ld": json_ld,
            "image_urls": images,
        }
        save_raw("booking", payload)
        print(f"  rooms parsed: {len(rooms)} | images: {len(images)} | "
              f"json-ld blocks: {len(json_ld)}")
        polite_pause()
        ctx.close()


if __name__ == "__main__":
    main()
