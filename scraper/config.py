"""
Central configuration for the Casa Gracia scraping toolkit.

Edit the dates and (if needed) the listing URLs here. Everything else
(scrape_booking.py, scrape_airbnb.py, download_images.py) reads from this file.
"""
from __future__ import annotations
import os
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent           # project root
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"                               # raw JSON dumps per run
ASSETS_DIR = ROOT / "assets"                             # downloaded images
PROFILE_DIR = Path(__file__).resolve().parent / ".pw-profile"  # persistent browser profile

for _d in (DATA_DIR, RAW_DIR, ASSETS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Search dates (Booking needs dates to render live room prices)
# ---------------------------------------------------------------------------
CHECKIN = (date.today() + timedelta(days=30)).isoformat()   # 30 days out
CHECKOUT = (date.today() + timedelta(days=32)).isoformat()  # 2-night stay
ADULTS = 2
CURRENCY = "USD"

# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------
BOOKING_URL = "https://www.booking.com/hotel/co/casa-gracia.html"

AIRBNB_ROOMS = [
    {"id": "1197228721608888257", "label": "Queen Room 101"},
    {"id": "1214331311532778558", "label": "Double Room 201"},
    {"id": "1218986625525817678", "label": "King Room 202"},
    {"id": "1265108254884566985", "label": "Queen Room 301"},
]

# ---------------------------------------------------------------------------
# Browser behaviour
# ---------------------------------------------------------------------------
# HEADLESS=False is strongly recommended: a visible browser is far less likely
# to be blocked, and lets you log into YOUR OWN accounts / solve a CAPTCHA once.
# Override per-run with env var, e.g.  $env:HEADLESS="1"; py scrape_booking.py
HEADLESS = os.environ.get("HEADLESS", "0") == "1"
# Polite pacing between page loads (seconds). Do not lower this.
REQUEST_DELAY = 4.0
LOCALE = "es-CO"
TIMEZONE = "America/Bogota"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
