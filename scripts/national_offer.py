#!/usr/bin/env python3
"""The nationwide coupon, shared by every generator that renders a location page.

A coupon valid at participating salons anywhere in the US is valid on every
location page the site has - all 2,550 city pages, all 68 metro pages and all 50
state pages - so each of those pages should say so in its own HTML rather than
leaving it to the client-side coupon list, which most AI crawlers never run.

generate_local_pages.py had its own private copy of this loader and was the only
generator that called it. That is why the state and metro pages spent months
advertising a hardcoded "$6.99" in their Offer schema while a $5.00 nationwide
coupon was live and valid in every one of those states.

The volatile parts of the offer are left out on purpose: the offer code changes
every time Great Clips reissues it, and baking it in would rewrite thousands of
static files on every scrape. Price is stable, so price is what gets baked; the
live link is still wired up client-side from /data/coupons.json.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FEED_FILE = REPO_ROOT / "docs" / "data" / "coupons.json"


def load_feed(path: Path | None = None) -> dict:
    """The exported coupon feed, or an empty feed if it is missing or unreadable.

    Returning an empty feed rather than raising keeps a scrape failure from
    taking the page build down with it: pages then simply omit the offer.
    """
    feed_path = path or FEED_FILE
    if not feed_path.exists():
        return {}
    try:
        with feed_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _price_value(coupon: dict) -> float:
    """Numeric price, falling back to parsing the display string."""
    value = coupon.get("price_value")
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(coupon.get("price") or "").replace("$", "").strip())
    except ValueError:
        return 999.0


def national_offer(feed: dict | None = None) -> dict | None:
    """The cheapest coupon valid at participating salons anywhere in the US.

    None when no nationwide coupon is running, in which case callers must omit
    the nationwide section entirely rather than fall back to a guess.
    """
    data = load_feed() if feed is None else feed
    national = [c for c in data.get("coupons", []) if c.get("scope") == "national"]
    if not national:
        return None
    return min(national, key=_price_value)


def floor_price(feed: dict | None = None) -> str | None:
    """Cheapest price anywhere in the feed, nationwide or local, as "$5.00".

    This is the only figure a page may honestly quote as "as little as X". The
    old templates hardcoded "$5.99-$8.99", a range that no coupon in the feed has
    matched for months.
    """
    data = load_feed() if feed is None else feed
    coupons = data.get("coupons") or []
    if not coupons:
        return None
    cheapest = min(coupons, key=_price_value)
    price = (cheapest.get("price") or "").strip()
    return price or None


def price_text(offer: dict | None) -> str:
    """Display price of an offer, e.g. "$5.00"."""
    if not offer:
        return ""
    return (offer.get("price") or "").strip()


def schema_price(offer: dict | None) -> str | None:
    """Offer price formatted for schema.org, e.g. "5.00"."""
    raw = price_text(offer).replace("$", "").strip()
    if not raw:
        return None
    try:
        return f"{float(raw):.2f}"
    except ValueError:
        return None
