# Canal Directo — Casa Gracia Hotel Boutique

Toolkit + dataset to gather Casa Gracia's listing content (info, photos, prices)
and build a **direct-booking channel** (your own site/booking engine) so you
keep more revenue instead of paying OTA commissions.

## En producción

| | Enlace |
|---|---|
| **Sitio web** | https://casa-gracia.vercel.app |
| **Panel de administración** | https://casa-gracia.vercel.app/admin |

> El panel pide el `ADMIN_TOKEN` (configurado en Vercel) para entrar. No lo
> compartas ni lo subas al repositorio.

```
Canal directo casa gracia/
├── README.md                     <- you are here
├── PLAN.md                       <- strategy & roadmap for the direct channel
├── data/
│   ├── casa-gracia-profile.json  <- structured master data (public sources)
│   ├── casa-gracia-profile.md    <- same, human-readable
│   └── raw/                       <- raw JSON dumps written by the scrapers
├── assets/                        <- downloaded photos (by source)
└── scraper/
    ├── config.py                  <- EDIT: dates, listing URLs, behaviour
    ├── common.py                  <- shared browser + parsing helpers
    ├── scrape_booking.py          <- pull your Booking.com page
    ├── scrape_airbnb.py           <- pull your 4 Airbnb room listings
    ├── download_images.py         <- download every collected photo into assets/
    ├── merge_to_profile.py        <- consolidate raw dumps into one clean file
    └── requirements.txt
```

## ⚠️ Read first — the legitimate way to do this

Booking.com and Airbnb **block automated scraping** (you'll see `403`/CAPTCHAs)
and their **Terms of Service prohibit it**. This toolkit is built for the one
case where gathering this data is clearly legitimate: **you operate Casa Gracia
and you're collecting your own listing content from your own accounts.**

Two paths, best first:

1. **Official / API (recommended for anything ongoing).**
   - **Booking.com**: log into the **Extranet → Property → Photos / Description**
     and export your own content; for live rates/availability use the
     **Connectivity (Content) API** (via your channel manager / Connectivity partner).
   - **Airbnb**: professional hosts / channel managers get the **Airbnb API**.
   - A **Channel Manager** (Cloudbeds, SiteMinder, Little Hotelier, Hostaway,
     Lobby PMS, Zeevou…) already holds all this data and syncs it for you.

2. **Local browser pull (this toolkit).** Runs a real Chromium **from your own
   computer and IP**, optionally logged into your own accounts. Polite pacing is
   built in. Use it for a one-time content/photo grab, not bulk harvesting.

## Setup (Windows / PowerShell)

```powershell
cd "C:\Canal directo casa gracia\scraper"
py -m pip install -r requirements.txt
py -m playwright install chromium
```

## Run

```powershell
# 1) Pull Booking page (opens a real browser; solve any CAPTCHA once)
py scrape_booking.py

# 2) Pull the 4 Airbnb room listings
py scrape_airbnb.py

# 3) Download every photo the scrapers found, into ../assets/
py download_images.py

# 4) Consolidate everything into data/casa-gracia-scraped.json
py merge_to_profile.py
```

Edit **`scraper/config.py`** to change the search dates (Booking needs dates to
show live prices), currency, or to set `HEADLESS = True` once it's working.

The first run opens a visible Chromium with a **persistent profile**
(`scraper/.pw-profile`) — log into your Booking Extranet / Airbnb host account
there once and it's remembered on later runs.

## What you get
- `data/raw/*.json` — full JSON-LD, room/price tables, embedded state, photo URLs
- `assets/booking/`, `assets/airbnb/` — downloaded images
- `data/casa-gracia-scraped.json` — one consolidated, deduped view

If a site blocks the automated browser, fall back to path #1 (Extranet export /
API / channel manager) — same data, no friction. See **PLAN.md** for the full
roadmap to a live direct-booking site.
