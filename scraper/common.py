"""
Shared helpers: launch a persistent (logged-in-able) browser context,
extract embedded JSON-LD / state blobs, and save raw output.
"""
from __future__ import annotations
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, Page, BrowserContext

import config


def launch_context(pw) -> BrowserContext:
    """
    Launch a persistent Chromium context. The profile is stored on disk
    (scraper/.pw-profile) so cookies/logins survive between runs -- log into
    YOUR OWN Booking Extranet / Airbnb host account once and it sticks.
    """
    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(config.PROFILE_DIR),
        headless=config.HEADLESS,
        locale=config.LOCALE,
        timezone_id=config.TIMEZONE,
        user_agent=config.USER_AGENT,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    # Light stealth: hide webdriver flag.
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )
    return context


def accept_cookies(page: Page) -> None:
    """Best-effort dismissal of common cookie/consent banners."""
    selectors = [
        "#onetrust-accept-btn-handler",
        "button#onetrust-accept-btn-handler",
        "[aria-label='Accept']",
        "button:has-text('Accept')",
        "button:has-text('Aceptar')",
        "button:has-text('OK')",
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1500):
                el.click(timeout=1500)
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


def extract_json_ld(page: Page) -> list[dict[str, Any]]:
    """Return every <script type='application/ld+json'> block, parsed."""
    blocks: list[dict[str, Any]] = []
    handles = page.locator("script[type='application/ld+json']")
    for i in range(handles.count()):
        try:
            txt = handles.nth(i).inner_text()
            data = json.loads(txt)
            blocks.extend(data if isinstance(data, list) else [data])
        except Exception:
            continue
    return blocks


def extract_json_script(page: Page, element_id: str) -> dict | None:
    """Parse a <script id='...' type='application/json'> blob (Airbnb state)."""
    try:
        txt = page.locator(f"script#{element_id}").first.inner_text()
        return json.loads(txt)
    except Exception:
        return None


# Only keep URLs whose path matches a real listing-photo pattern (drops UI
# icons, flags, avatars, design-assets, etc.).
_PHOTO_PATTERNS = (
    "/xdata/images/hotel/",   # Booking listing photos
    "/im/pictures/",          # Airbnb listing photos
    "/pictures/",             # Airbnb (alt)
    "/images/hotels/",        # Hotels.com / EAN
)
_SKIP = ("design-assets", "images-flags", "/flags/", "/static/", "sprite", "favicon")


def collect_image_urls(page: Page) -> list[str]:
    """Grab plausible high-res photo URLs from <img> tags and srcset."""
    urls = page.eval_on_selector_all(
        "img",
        """els => els.flatMap(e => [e.currentSrc, e.src,
            ...(e.srcset ? e.srcset.split(',').map(s => s.trim().split(' ')[0]) : [])])"""
    )
    keep, seen = [], set()
    for u in urls:
        if not u or not u.startswith("http"):
            continue
        if any(s in u for s in _SKIP):
            continue
        if not any(p in u for p in _PHOTO_PATTERNS):
            continue
        # Upscale Booking thumbnails: .../max300/...  ->  .../max1920x1080/...
        u = re.sub(r"/max\d+(x\d+)?/", "/max1920x1080/", u)
        u = re.sub(r"/square\d+/", "/max1920x1080/", u)
        if u not in seen:
            seen.add(u)
            keep.append(u)
    return keep


def save_raw(name: str, payload: dict) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = config.RAW_DIR / f"{name}_{ts}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  saved -> {path.relative_to(config.ROOT)}")
    return path


def polite_pause():
    time.sleep(config.REQUEST_DELAY)
