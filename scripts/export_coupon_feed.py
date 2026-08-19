#!/usr/bin/env python3
"""
Publish docs/data/coupons.json - the feed the local pages read.

Every coupon is tagged with the geography it actually covers, so a page can ask a
single question ("does this coupon reach me?") instead of parsing market strings
in the browser:

    scope        national | state | area | salon | unknown
    state        two-letter state for statewide coupons
    metro_keys   markets an area coupon covers  (e.g. ["IL/glen-ellyn"])
    city_keys    cities it covers               (e.g. ["IL/schaumburg", ...])

Splitting the work this way keeps the ~2,550 city pages static: only this small
JSON changes when coupons change, so the daily scrape does not rewrite (and commit)
every page in the site.

Usage:
    python scripts/export_coupon_feed.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO_ROOT))

import markets  # noqa: E402

# Reuse the homepage's own cleaning so the city pages and the homepage never
# disagree: the blocklist drops dead offers, and normalize_coupons repairs the
# truncated market names the scraper sometimes pulls out of ad copy.
from generate_website import (  # noqa: E402
    is_blocked_coupon,
    normalize_coupons,
)

COUPONS_IN = REPO_ROOT / "data" / "coupons.json"
FEED_OUT = REPO_ROOT / "docs" / "data" / "coupons.json"

# Fields worth shipping to the browser; everything else is build-time noise.
KEEP_FIELDS = (
    "url",
    "coupon_code",
    "price",
    "location_name",
    "city",
    "state",
    "address",
    "area_name",
    "market",
    "expiration",
    "last_verified",
    "participating_location_note",
)


def price_value(coupon: dict) -> float:
    raw = (coupon.get("price") or "").replace("$", "").strip()
    try:
        return float(raw)
    except ValueError:
        return 999.0


def build_feed(cities: dict, metros: dict) -> dict:
    if not COUPONS_IN.exists():
        raise SystemExit(f"{COUPONS_IN} not found")

    with COUPONS_IN.open(encoding="utf-8") as fh:
        source = json.load(fh)

    raw = source.get("coupons", [])
    coupons = normalize_coupons([c for c in raw if not is_blocked_coupon(c)])
    if len(coupons) != len(raw):
        print(f"  filtered {len(raw) - len(coupons)} blocked/junk coupon(s)")

    lookup = markets.build_city_lookup(cities)
    out: list[dict] = []
    scope_counts: dict[str, int] = {}

    for coupon in coupons:
        resolved = markets.coupon_market_keys(coupon, cities, lookup)
        scope = resolved["scope"]
        scope_counts[scope] = scope_counts.get(scope, 0) + 1

        record = {k: coupon.get(k) for k in KEEP_FIELDS if coupon.get(k) is not None}
        record["scope"] = scope
        record["price_value"] = price_value(coupon)

        if scope == "state":
            record["coupon_state"] = resolved.get("state")
            # A market can list several states ("NJ, PA & DE"), so ship them all.
            record["coupon_states"] = resolved.get("states") or [resolved.get("state")]
        if resolved.get("metro_keys"):
            record["metro_keys"] = resolved["metro_keys"]
            record["market_names"] = [
                metros[k]["display_name"]
                for k in resolved["metro_keys"]
                if k in metros
            ]
        if resolved.get("city_keys"):
            record["city_keys"] = resolved["city_keys"]

        out.append(record)

    out.sort(key=lambda c: c["price_value"])

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scraped_at": source.get("scraped_at"),
        "total": len(out),
        "scopes": scope_counts,
        "coupons": out,
    }


def main() -> int:
    cities, metros = markets.build_all()
    feed = build_feed(cities, metros)

    FEED_OUT.parent.mkdir(parents=True, exist_ok=True)
    with FEED_OUT.open("w", encoding="utf-8") as fh:
        json.dump(feed, fh, indent=1, ensure_ascii=False)

    print(f"Wrote {FEED_OUT.relative_to(REPO_ROOT)}  ({len(feed['coupons'])} coupons)")
    for scope, count in sorted(feed["scopes"].items(), key=lambda kv: -kv[1]):
        print(f"  {scope:<9} {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
