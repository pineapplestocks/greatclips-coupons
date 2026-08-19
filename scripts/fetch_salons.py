#!/usr/bin/env python3
"""
Build the salon location database from the public Great Clips salon locator.

Source of truth: https://salons.greatclips.com/sitemap.xml
  - depth-3 paths  (us/il/schaumburg)                  -> city directory pages
  - depth-4 paths  (us/il/schaumburg/1109-s-roselle-rd) -> salon detail pages

Each salon detail page carries JSON-LD (HealthAndBeautyBusiness) with the full
street address, city, state, ZIP, phone and opening hours, plus a Yext
"certified fact" block with lat/lng. We keep only those facts.

Writes data/salons.json. Resumable: extracted records are appended to a JSONL
cache, so re-running after an interruption only fetches what is missing.

Usage:
    python scripts/fetch_salons.py                # full refresh (uses cache)
    python scripts/fetch_salons.py --limit 50     # smoke test
    python scripts/fetch_salons.py --no-cache     # ignore cache, refetch all
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests

SITEMAP_INDEX = "https://salons.greatclips.com/sitemap.xml"
BASE = "https://salons.greatclips.com/"

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = REPO_ROOT / "data" / "salons.json"
CACHE_DIR = Path(
    os.environ.get("GC_CACHE_DIR", REPO_ROOT / ".cache" / "salons")
)
CACHE_FILE = CACHE_DIR / "salons.jsonl"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
WORKERS = int(os.environ.get("GC_WORKERS", "12"))
TIMEOUT = 30
RETRIES = 3

DAY_ORDER = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
DAY_FULL = {
    "Mo": "Monday",
    "Tu": "Tuesday",
    "We": "Wednesday",
    "Th": "Thursday",
    "Fr": "Friday",
    "Sa": "Saturday",
    "Su": "Sunday",
}

_print_lock = threading.Lock()
_cache_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    return s


def get(session: requests.Session, url: str) -> str | None:
    """GET with retries and linear backoff. Returns text or None."""
    for attempt in range(RETRIES):
        try:
            r = session.get(url, timeout=TIMEOUT)
            if r.status_code == 200:
                return r.text
            if r.status_code in (404, 410):
                return None
            # 429/5xx -> back off
        except requests.RequestException:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None


# ---------------------------------------------------------------- sitemap ----

def fetch_sitemap_paths(session: requests.Session) -> list[str]:
    """Return every site-relative path from the locator's sitemap index."""
    index = get(session, SITEMAP_INDEX)
    if not index:
        raise SystemExit("Could not fetch the Great Clips locator sitemap index")

    children = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", index)
    paths: list[str] = []
    for child in children:
        body = get(session, child)
        if not body:
            log(f"  ! could not fetch {child}")
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
        for loc in locs:
            paths.append(loc.replace(BASE, "").strip("/"))
        log(f"  {child.rsplit('/', 1)[-1]}: {len(locs):,} urls")
    return paths


def split_paths(paths: list[str]) -> tuple[list[str], list[str]]:
    """Split locator paths into (salon detail paths, city directory paths).

    Salon pages are us/<st>/<city>/<street>. Street slugs can themselves contain
    slashes ("2506-1/2-n-clark-st", "422-us-hwy-202/206-n"), which show up as
    extra path segments; those variants always also appear with a trailing
    /salon-services. So: treat "<...>/salon-services" as the canonical marker of
    a salon page and derive the detail path by stripping that suffix.
    """
    salons: set[str] = set()
    cities: set[str] = set()

    for p in paths:
        if not p or "." in p.split("/")[-1]:
            continue
        parts = p.split("/")
        if parts[-1] == "salon-services":
            salons.add("/".join(parts[:-1]))
        elif len(parts) == 3:
            cities.add(p)
        elif len(parts) >= 4:
            salons.add(p)

    return sorted(salons), sorted(cities)


# ------------------------------------------------------------- extraction ----

def _json_blocks(html: str) -> list[dict]:
    out = []
    for raw in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    ):
        try:
            parsed = json.loads(raw.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict) and "@graph" in parsed:
            for node in parsed["@graph"]:
                if isinstance(node, dict):
                    out.append(node)
        elif isinstance(parsed, dict):
            out.append(parsed)
    return out


def _normalize_hours(opening_hours) -> dict[str, str]:
    """'Mo,Tu,We,Th,Fr 09:00-20:00' -> {'Monday': '9:00 AM - 8:00 PM', ...}"""
    hours: dict[str, str] = {}
    if not isinstance(opening_hours, list):
        return hours

    for spec in opening_hours:
        if not isinstance(spec, str) or " " not in spec:
            continue
        days_part, _, time_part = spec.partition(" ")
        times = time_part.strip()
        for token in days_part.split(","):
            token = token.strip()[:2]
            if token in DAY_FULL:
                hours[DAY_FULL[token]] = times
    return hours


def _pretty_time(hhmm: str) -> str:
    try:
        h, m = (int(x) for x in hhmm.split(":")[:2])
    except (ValueError, IndexError):
        return hhmm
    suffix = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {suffix}" if m else f"{h12} {suffix}"


def _pretty_range(rng: str) -> str:
    if "-" not in rng:
        return rng
    open_t, _, close_t = rng.partition("-")
    return f"{_pretty_time(open_t)} - {_pretty_time(close_t)}"


def parse_salon(path: str, html: str) -> dict | None:
    """Pull the facts we need out of a salon detail page."""
    blocks = _json_blocks(html)

    business = next(
        (
            b
            for b in blocks
            if isinstance(b.get("address"), dict)
            and b.get("@type")
            in ("HealthAndBeautyBusiness", "HairSalon", "LocalBusiness")
        ),
        None,
    )

    # Yext certified-fact block carries geo coordinates.
    subject = next(
        (
            b.get("credentialSubject")
            for b in blocks
            if isinstance(b.get("credentialSubject"), dict)
            and isinstance(b["credentialSubject"].get("address"), dict)
        ),
        None,
    )

    address = (business or {}).get("address") or (subject or {}).get("address")
    if not address:
        return None

    city = (address.get("addressLocality") or "").strip()
    state = (address.get("addressRegion") or "").strip().upper()
    street = (address.get("streetAddress") or "").strip()
    if not (city and state and street):
        return None

    lat = lng = None
    geo = (subject or {}).get("geo") or {}
    if isinstance(geo, dict):
        try:
            lat = round(float(geo["latitude"]), 6)
            lng = round(float(geo["longitude"]), 6)
        except (KeyError, TypeError, ValueError):
            lat = lng = None
    if lat is None:
        m = re.search(
            r'"yextDisplayCoordinate":\{"latitude":([-\d.]+),"longitude":([-\d.]+)\}',
            html,
        )
        if m:
            lat, lng = round(float(m.group(1)), 6), round(float(m.group(2)), 6)

    phone = (business or {}).get("telephone") or ""
    if not phone and subject:
        raw = subject.get("telephone", "")
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) == 10:
            phone = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    phone = phone.strip()

    hours = {
        day: _pretty_range(rng)
        for day, rng in _normalize_hours((business or {}).get("openingHours")).items()
    }

    parts = path.split("/")
    return {
        "path": path,
        "url": BASE + path,
        "country": parts[0].upper() if parts else "US",
        "street": street,
        "city": city,
        "state": state,
        "zip": (address.get("postalCode") or "").strip(),
        "phone": phone,
        "lat": lat,
        "lng": lng,
        "hours": hours,
    }


def fetch_one(session: requests.Session, path: str) -> dict | None:
    html = get(session, BASE + path)
    if not html:
        return None
    try:
        return parse_salon(path, html)
    except Exception as exc:  # noqa: BLE001 - one bad page must not kill the run
        log(f"  ! parse failed for {path}: {exc}")
        return None


# ------------------------------------------------------------------ cache ----

def load_cache() -> dict[str, dict]:
    if not CACHE_FILE.exists():
        return {}
    records: dict[str, dict] = {}
    with CACHE_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("path"):
                records[rec["path"]] = rec
    return records


def append_cache(rec: dict) -> None:
    with _cache_lock:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with CACHE_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------- main ----

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="only fetch N salons")
    ap.add_argument("--no-cache", action="store_true", help="refetch everything")
    ap.add_argument(
        "--us-only",
        action="store_true",
        default=True,
        help="keep US salons only (default)",
    )
    ap.add_argument("--include-canada", dest="us_only", action="store_false")
    args = ap.parse_args()

    session = make_session()

    print("Fetching locator sitemap...")
    paths = fetch_sitemap_paths(session)
    salon_paths, city_paths = split_paths(paths)
    print(f"  -> {len(salon_paths):,} salon pages, {len(city_paths):,} city pages")

    if args.us_only:
        salon_paths = [p for p in salon_paths if p.startswith("us/")]
        print(f"  -> {len(salon_paths):,} US salon pages")

    if args.limit:
        salon_paths = salon_paths[: args.limit]

    cache = {} if args.no_cache else load_cache()
    if cache:
        print(f"  -> {len(cache):,} salons already cached")

    todo = [p for p in salon_paths if p not in cache]
    print(f"Fetching {len(todo):,} salon pages with {WORKERS} workers...")

    done = failed = 0
    if todo:
        sessions = [make_session() for _ in range(WORKERS)]
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {
                pool.submit(fetch_one, sessions[i % WORKERS], p): p
                for i, p in enumerate(todo)
            }
            for fut in as_completed(futures):
                path = futures[fut]
                try:
                    rec = fut.result()
                except Exception as exc:  # noqa: BLE001
                    rec = None
                    log(f"  ! {path}: {exc}")
                if rec:
                    cache[path] = rec
                    append_cache(rec)
                    done += 1
                else:
                    failed += 1
                total = done + failed
                if total % 250 == 0:
                    log(f"  {total:,}/{len(todo):,} ({failed} failed)")

    salons = [cache[p] for p in salon_paths if p in cache]
    salons.sort(key=lambda s: (s["state"], s["city"], s["street"]))

    if not salons:
        print("No salons parsed - refusing to write an empty database.")
        return 1

    with_geo = sum(1 for s in salons if s.get("lat") is not None)
    cities = {(s["state"], s["city"]) for s in salons}

    payload = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": BASE,
        "total_salons": len(salons),
        "total_cities": len(cities),
        "salons": salons,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)

    print()
    print(f"Wrote {OUT_FILE.relative_to(REPO_ROOT)}")
    print(f"  salons        : {len(salons):,}")
    print(f"  cities        : {len(cities):,}")
    print(f"  states        : {len({s['state'] for s in salons})}")
    print(f"  with lat/lng  : {with_geo:,}")
    print(f"  with phone    : {sum(1 for s in salons if s['phone']):,}")
    print(f"  with hours    : {sum(1 for s in salons if s['hours']):,}")
    if failed:
        print(f"  failed pages  : {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
