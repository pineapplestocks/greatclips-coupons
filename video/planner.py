"""Produce factual scripts. A dollar sign alone is never an offer classification."""
from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

SITE = "https://greatclipsdeal.com"
VERSION = "guide-v2-motion-neural"


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]


def parse_date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(value)[:10], fmt).date()
        except ValueError:
            pass
    return None


def classify_amount(text):
    """Return a single unambiguous (kind, amount), otherwise decline the offer."""
    text = re.sub(r"\s+", " ", text)
    matches = set()
    for pattern in (r"\$(\d+(?:\.\d{1,2})?)\s*(?:off|discount)\b",
                    r"save\s+\$(\d+(?:\.\d{1,2})?)\b"):
        matches.update(("amount_off", Decimal(m)) for m in re.findall(pattern, text, re.I))
    for pattern in (r"\$(\d+(?:\.\d{1,2})?)\s*(?:adult\s+)?haircuts?\b",
                    r"haircuts?\s+(?:for\s+)?(?:only\s+)?\$(\d+(?:\.\d{1,2})?)\b"):
        matches.update(("haircut_price", Decimal(m)) for m in re.findall(pattern, text, re.I))
    if len(matches) != 1:
        return None
    kind, amount = matches.pop()
    if amount <= 0 or amount > 100:
        return None
    return kind, f"{amount:.2f}"


def inspect_offer(coupon, html, today):
    soup = BeautifulSoup(html, "html.parser")
    nodes = [soup.select_one(s) for s in ("#description", "#terms_and_conditions")]
    # Hidden template copies elsewhere can say "offer ended" on valid pages.
    if not all(nodes):
        return None, "official description or terms missing"
    text = " ".join(n.get_text(" ", strip=True) for n in nodes)
    if re.search(r"offer (?:has )?ended|offer (?:has )?expired|no longer available", text, re.I):
        return None, "offer ended"
    classification = classify_amount(text)
    if not classification:
        return None, "discount type is ambiguous or image-only"
    expirations = {parse_date(x) for x in re.findall(r"expires?\s*:?\s*(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})", text, re.I)}
    expirations.discard(None)
    if len(expirations) != 1:
        return None, "explicit expiration missing or ambiguous"
    expires = expirations.pop()
    if (expires - today).days < 3:
        return None, "expired or fewer than three days remain"
    city = (coupon.get("city") or "").strip(" ,")
    area = (coupon.get("area_name") or "").strip()
    area = re.sub(r"^(?:only at )?participating\s+", "", area, flags=re.I)
    location = city or area
    if not location or location.lower() in {"us", "usa", "united states"}:
        return None, "specific geographic coverage required"
    if location.casefold() not in text.casefold():
        return None, "location not confirmed in official terms"
    kind, amount = classification
    return {
        "kind": kind, "amount": amount,
        "label": f"${amount} OFF" if kind == "amount_off" else f"${amount} haircut",
        "location": location,
        "salon": coupon.get("location_name", "Participating salons"),
        "address": coupon.get("address", ""),
        "expiration": expires.isoformat(), "checked_at": today.isoformat(),
        "url": coupon["url"], "terms": text,
    }, None


def verify_offer(coupon, today):
    url = coupon.get("url", "")
    try:
        parsed = urlparse(url)
        allowed = (parsed.scheme == "https" and parsed.hostname == "offers.greatclips.com"
                   and not parsed.username and parsed.port in (None, 443))
    except (ValueError, TypeError):
        allowed = False
    if not allowed:
        return None, "not an official HTTPS offer URL"
    try:
        response = requests.get(url, timeout=(4, 8), allow_redirects=False,
                                headers={"User-Agent": "GreatClipsDeal-Video/1.0"})
        if response.status_code != 200:
            return None, f"official page returned HTTP {response.status_code}"
        return inspect_offer(coupon, response.text, today)
    except requests.RequestException:
        return None, "official page unavailable"


def scene(kind, eyebrow, headline, detail, narration, **extra):
    return dict(kind=kind, eyebrow=eyebrow, headline=headline, detail=detail,
                narration=narration, **extra)


def guide_scenes():
    return [
        scene("intro", "BEFORE YOUR NEXT HAIRCUT", "CHECK FOR\nA COUPON.", "Great Clips coupon guide",
              "Before your next Great Clips haircut, check for a coupon."),
        scene("promise", "HERE'S THE SHORT VERSION", "FIND IT.\nCHECK IT.\nUSE IT.", "Your shortcut to the right offer.",
              "Here's the quick way to find one near you, without guessing which deal works."),
        scene("search", "01 / FIND YOUR AREA", "START\nLOCAL.", "City or state. Then your salon.",
              "Open Great Clips Deal dot com. Search your city, or pick your state to narrow things down."),
        scene("compare", "02 / READ THE AMOUNT", "$5 OFF", "A discount from the regular price.",
              "Watch the wording. Five dollars off means a discount from the regular haircut price."),
        scene("price", "EXAMPLES, NOT LIVE OFFERS", "$5 HAIRCUT", "A fixed price with that offer.",
              "A five dollar haircut means a fixed price with that offer. Big difference. Always check the actual coupon."),
        scene("check", "03 / QUICK CHECK", "RIGHT PLACE.\nRIGHT DATE.", "Participation. Expiration. Terms.",
              "Make sure your salon participates, and check the expiration date. If it's unclear, call the salon before you go."),
        scene("email", "04 / REQUEST THE LINK", "STRAIGHT TO\nYOUR INBOX.", "Coupon requests use email delivery.",
              "Hit Get Coupon, enter your email, and open the official offer from your inbox. That's where you'll find the full terms."),
        scene("redeem", "05 / AT THE SALON", "SHOW IT\nBEFORE\nYOU PAY.", "Follow the instructions on the official offer.",
              "Have the coupon ready on your phone and show it before paying. Follow the instructions on the offer."),
        scene("outro", "WEBSITE LINK BELOW", "CHECK BEFORE\nYOU GO.", "greatclipsdeal.com",
              "The website link is below. Great Clips Deal dot com. Check before you go."),
    ]


def offer_scenes(offers, today):
    scenes = [scene("intro", f"DEAL BRIEF / {today.strftime('%b %d, %Y').upper()}",
                    "Fresh finds.\nLocal savings.", "A closer look at selected local offers.",
                    f"Here are {len(offers)} local Great Clips offers, checked on {today.strftime('%B %d')}. Start with your location.")]
    for i, offer in enumerate(offers, 1):
        phrase = f"{offer['amount']} dollars off the regular haircut price" if offer['kind'] == "amount_off" else f"a haircut priced at {offer['amount']} dollars"
        end = date.fromisoformat(offer["expiration"]).strftime("%B %d, %Y")
        place = f"{offer['address']}, {offer['location']}" if offer['address'] else f"participating salons in {offer['location']}"
        scenes.append(scene("offer", f"LOCAL OFFER / {i:02}", offer["label"], offer["location"],
                            f"At {place}: {phrase}. Expires {end}. Check the official terms before visiting.", offer=offer))
    scenes.extend([guide_scenes()[5], guide_scenes()[6], guide_scenes()[-1]])
    return scenes


def build_plan(feed, ledger, mode="auto", today=None, verifier=verify_offer):
    today = today or datetime.now(timezone.utc).date()
    history = ledger.get("videos", [])
    guide_id = fingerprint(VERSION)
    guide_done = any(v["id"] == guide_id for v in history)
    if mode == "guide" or (mode == "auto" and not guide_done):
        if guide_done:
            return {"status": "skipped", "reason": "Evergreen tutorial already created."}
        return {"status": "ready", "id": guide_id, "type": "guide", "date": today.isoformat(),
                "title": "How to Find Great Clips Coupons Near You (And Use Them)",
                "scenes": guide_scenes(), "offers": [], "rejected": []}
    recent = [parse_date(v.get("date")) for v in history if v.get("type") == "deals"]
    if any(d and (today - d).days < 7 for d in recent):
        return {"status": "skipped", "reason": "Weekly deal-video limit; no new video needed."}
    rows = feed.get("coupons", [])[:40]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda c: verifier(c, today), rows))
    rejected = [{"url": c.get("url"), "reason": reason} for c, (o, reason) in zip(rows, results) if not o]
    offers, seen = [], set()
    previous = {key for v in history for key in v.get("offer_keys", [])}
    for offer, _ in results:
        if not offer:
            continue
        key = fingerprint({k: offer[k] for k in ("kind", "amount", "location", "expiration", "address")})
        if key in seen or key in previous:
            continue
        offer["key"] = key
        seen.add(key)
        offers.append(offer)
    offers = sorted(offers, key=lambda o: (o["location"], o["amount"]))
    if mode == "local":
        recent_locations = {v.get("location") for v in history
                            if v.get("type") == "local" and parse_date(v.get("date"))
                            and (today - parse_date(v["date"])).days < 7}
        offers = [o for o in offers if o["location"] not in recent_locations]
        if not offers:
            return {"status":"skipped", "reason":"No new verified local offers outside the weekly location limit.", "rejected":rejected}
        location = offers[0]["location"]
        offers = [o for o in offers if o["location"] == location][:3]
        scenes = offer_scenes(offers, today)
        scenes[0] = scene("intro", "GREAT CLIPS / LOCAL COUPONS", f"{location.upper()}\nHAIRCUT DEALS.",
                          f"Checked {today.isoformat()}",
                          f"Looking for a Great Clips coupon in {location}? Here's what we found. These offers apply only to the listed participating locations.")
        labels = {o["label"] for o in offers}
        label = next(iter(labels)) if len(labels) == 1 else "Local offers"
        return {"status":"ready", "id":fingerprint(sorted(o["key"] for o in offers)),
                "type":"local", "location":location, "date":today.isoformat(),
                "title":f"Great Clips {location} Coupons: {label} | {today.strftime('%B %Y')}",
                "scenes":scenes, "offers":offers, "rejected":rejected}
    offers = offers[:3]
    if len(offers) < 2:
        return {"status": "skipped", "reason": "Fewer than two new, unambiguous, live-checked offers.", "rejected": rejected}
    identity = fingerprint(sorted(o["key"] for o in offers))
    return {"status": "ready", "id": identity, "type": "deals", "date": today.isoformat(),
            "title": f"Great Clips Coupons: {today.strftime('%B %Y')} Local Offers & How to Use Them",
            "scenes": offer_scenes(offers, today), "offers": offers, "rejected": rejected}
