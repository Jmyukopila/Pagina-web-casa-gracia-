"""
Merge the raw scrape dumps (data/raw/*.json) into a single consolidated file:
data/casa-gracia-scraped.json -- a clean, deduped view of rooms, prices,
addresses, ratings and image counts pulled from your own listings.

Run:  python merge_to_profile.py
"""
from __future__ import annotations

import json
from collections import defaultdict

import config


def first(d: dict, *keys):
    for k in keys:
        if isinstance(d, dict) and d.get(k):
            return d[k]
    return None


def main():
    merged = {
        "booking": {"rooms": [], "images": 0, "address": None, "geo": None,
                    "rating": None, "title": None},
        "airbnb": [],
        "all_image_counts": defaultdict(int),
    }

    for jf in sorted(config.RAW_DIR.glob("*.json")):
        data = json.loads(jf.read_text(encoding="utf-8"))
        src = data.get("source", "")
        merged["all_image_counts"][src] += len(data.get("image_urls", []) or [])

        if src == "booking.com":
            merged["booking"]["title"] = data.get("title")
            merged["booking"]["rooms"] = data.get("rooms", [])
            merged["booking"]["images"] = len(data.get("image_urls", []) or [])
            for block in data.get("json_ld", []):
                if block.get("@type") in ("Hotel", "LodgingBusiness", "BedAndBreakfast"):
                    merged["booking"]["address"] = block.get("address")
                    merged["booking"]["geo"] = block.get("geo")
                    merged["booking"]["rating"] = block.get("aggregateRating")
        elif src == "airbnb.com":
            merged["airbnb"].append({
                "label": data.get("label"),
                "room_id": data.get("room_id"),
                "title": data.get("title"),
                "price": data.get("price"),
                "images": len(data.get("image_urls", []) or []),
            })

    merged["all_image_counts"] = dict(merged["all_image_counts"])
    out = config.DATA_DIR / "casa-gracia-scraped.json"
    out.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out.relative_to(config.ROOT)}")
    print(json.dumps(merged, indent=2, ensure_ascii=False)[:1200])


if __name__ == "__main__":
    main()
