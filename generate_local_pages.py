#!/usr/bin/env python3
"""
Generate a coupon page for every US city that has a Great Clips salon.

Why this exists
---------------
The site used to have 68 hand-listed metro pages with invented location counts
("200+"), so it only ever competed for "great clips coupons chicago". Nobody
searches that way - they search "great clips coupon schaumburg il" or "cypress
tx". Meanwhile Great Clips issues most of its coupons per *market*
("participating Chicagoland"), and nothing on the site connected a Chicagoland
coupon to the ~72 suburbs it is actually valid in.

This builds the missing layer: one page per city, carrying that city's real
salons (address, phone, hours, coordinates - scraped from the official locator)
plus the coupons that reach it, whether national, statewide, or market-wide.

Output
------
    docs/salons/<st>/<city>.html   one page per city   -> /salons/tx/cypress
    docs/salons/index.html         national directory  -> /salons

Live coupons are injected in the browser from /data/coupons.json so that the
daily coupon refresh does not have to rewrite thousands of static files. The
static half of each page - the salon directory, which is the part that is unique
and worth ranking - is always present in the HTML for crawlers that do not run
JavaScript, including most AI search crawlers.

Usage:
    python generate_local_pages.py                 # everything
    python generate_local_pages.py --state TX      # one state
    python generate_local_pages.py --limit 5       # smoke test
    python generate_local_pages.py --dry-run
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import markets  # noqa: E402

SITE_URL = "https://greatclipsdeal.com"
REPO_ROOT = Path(__file__).resolve().parent
OUT_DIR = REPO_ROOT / "docs" / "salons"
STATE_STATS_FILE = REPO_ROOT / "data" / "state_history_stats.json"

GA_ID = "G-90ZQ7M4EFR"
# Left empty deliberately: AdSense is not in use, so these pages do not pay the
# cost of a third-party ad script on 2,550 URLs. Set the publisher id here to
# switch it on for every generated page.
ADSENSE_CLIENT = ""
LOGO = (
    "https://raw.githubusercontent.com/pineapplestocks/greatclips-coupons/"
    "main/docs/logo.png"
)
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_SHORT = {
    "Monday": "Mon",
    "Tuesday": "Tue",
    "Wednesday": "Wed",
    "Thursday": "Thu",
    "Friday": "Fri",
    "Saturday": "Sat",
    "Sunday": "Sun",
}
SCHEMA_DAY = {
    "Monday": "https://schema.org/Monday",
    "Tuesday": "https://schema.org/Tuesday",
    "Wednesday": "https://schema.org/Wednesday",
    "Thursday": "https://schema.org/Thursday",
    "Friday": "https://schema.org/Friday",
    "Saturday": "https://schema.org/Saturday",
    "Sunday": "https://schema.org/Sunday",
}


def esc(text) -> str:
    return html.escape(str(text or ""), quote=True)


def maps_url(salon: dict) -> str:
    query = urllib.parse.quote_plus(
        f"Great Clips {salon['street']} {salon['city']} {salon['state']} {salon['zip']}"
    )
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def tel_href(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"tel:+1{digits}" if len(digits) == 10 else f"tel:{digits}"


def to_24h(label: str) -> str | None:
    """'8:30 AM' -> '08:30' for schema.org openingHoursSpecification."""
    label = label.strip()
    if not label:
        return None
    suffix = label[-2:].upper()
    if suffix not in ("AM", "PM"):
        return None
    clock = label[:-2].strip()
    hour, _, minute = clock.partition(":")
    try:
        hour_i = int(hour)
    except ValueError:
        return None
    minute_i = int(minute) if minute.isdigit() else 0
    if suffix == "PM" and hour_i != 12:
        hour_i += 12
    if suffix == "AM" and hour_i == 12:
        hour_i = 0
    return f"{hour_i:02d}:{minute_i:02d}"


# ------------------------------------------------------------ static assets --

# Shipped once to docs/assets/city-coupons.js rather than inlined into every page:
# 2,550 copies of this would add ~8 MB to the repo and to what crawlers download.
COUPON_WIDGET_JS = """(function () {
  var PAGE = window.__GC_PAGE__;
  var box = document.getElementById('liveCoupons');
  if (!box || !PAGE) return;

  function couponStates(c) {
    return c.coupon_states || (c.coupon_state ? [c.coupon_state] : []);
  }

  function reaches(c) {
    if (c.scope === 'national') return true;
    if (c.scope === 'state') return couponStates(c).indexOf(PAGE.state) !== -1;
    if (c.city_keys && c.city_keys.indexOf(PAGE.cityKey) !== -1) return true;
    if (c.metro_keys && c.metro_keys.indexOf(PAGE.metroKey) !== -1) return true;
    return false;
  }

  function scopeLabel(c) {
    if (c.scope === 'national') return 'Valid at participating US salons';
    if (c.scope === 'state') {
      var states = couponStates(c);
      return states.length > 1
        ? 'Valid across ' + states.join(', ')
        : 'Valid across ' + PAGE.state;
    }
    if (c.scope === 'salon') return 'Salon-specific offer';
    var names = c.market_names || [];
    return names.length ? 'Valid across the ' + names.join(' & ') + ' market'
                        : 'Regional offer';
  }

  function card(c) {
    var el = document.createElement('a');
    el.href = c.url;
    el.target = '_blank';
    el.rel = 'nofollow noopener';
    el.className = 'block bg-white rounded-xl border border-slate-200 p-5 ' +
                   'hover:border-purple-400 hover:shadow-md transition-all';
    var expiry = c.expiration
      ? '<p class="text-xs text-slate-400 mt-2">Expires ' + c.expiration + '</p>' : '';
    el.innerHTML =
      '<div class="flex items-start justify-between gap-4">' +
        '<div>' +
          '<div class="text-2xl font-extrabold text-purple-600">' + (c.price || '') + '</div>' +
          '<p class="text-sm text-slate-600 mt-1">' + scopeLabel(c) + '</p>' + expiry +
        '</div>' +
        '<span class="shrink-0 bg-purple-600 text-white text-sm font-semibold ' +
        'rounded-lg px-4 py-2">Get coupon</span>' +
      '</div>';
    return el;
  }

  fetch('/data/coupons.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (feed) {
      var hits = (feed.coupons || []).filter(reaches);
      if (!hits.length) {
        box.innerHTML =
          '<p class="text-slate-600">No live coupon is verified for ' + PAGE.cityLabel +
          ' right now. National offers appear here as soon as they are found - ' +
          '<a class="text-purple-600 underline" href="/">check every current coupon</a>.</p>';
        return;
      }
      box.innerHTML = '';
      var grid = document.createElement('div');
      grid.className = 'grid gap-4 sm:grid-cols-2';
      hits.slice(0, 8).forEach(function (c) { grid.appendChild(card(c)); });
      box.appendChild(grid);

      var note = document.createElement('p');
      note.className = 'text-xs text-slate-500 mt-4';
      note.textContent = 'Showing ' + Math.min(hits.length, 8) + ' of ' + hits.length +
        ' offers that reach ' + PAGE.cityLabel + '. Verified ' +
        (feed.scraped_at || '').slice(0, 10) + '.';
      box.appendChild(note);
    })
    .catch(function () {
      box.innerHTML =
        '<p class="text-slate-600"><a class="text-purple-600 underline" href="/">' +
        'View all current Great Clips coupons</a>.</p>';
    });
})();
"""


def nav_html() -> str:
    return f"""    <nav class="bg-white/95 backdrop-blur-sm shadow-sm sticky top-0 z-50 border-b border-slate-100">
        <div class="max-w-6xl mx-auto px-4">
            <div class="flex justify-between items-center h-14">
                <a href="/" class="flex items-center gap-2">
                    <img src="{LOGO}" alt="GreatClipsDeal" class="h-8 w-8 rounded-full object-cover">
                    <span class="font-bold text-lg text-purple-600">GreatClipsDeal</span>
                </a>
                <div class="hidden md:flex items-center gap-6 text-sm">
                    <a href="/salons" class="text-slate-600 hover:text-purple-600 font-medium">Salon Directory</a>
                    <a href="/states" class="text-slate-600 hover:text-purple-600 font-medium">Browse by State</a>
                    <a href="/faq" class="text-slate-600 hover:text-purple-600 font-medium">FAQ</a>
                </div>
            </div>
        </div>
    </nav>
"""


def footer_html() -> str:
    return """    <footer class="bg-slate-900 text-slate-400 py-10 mt-12">
        <div class="max-w-6xl mx-auto px-4 text-center">
            <p class="mb-3">Salon addresses, phone numbers and hours come from the official Great Clips
               salon locator. Coupon availability is set by Great Clips and can change without notice.</p>
            <p class="mb-4 text-sm">GreatClipsDeal is an independent coupon directory and is not
               affiliated with, endorsed by, or sponsored by Great Clips, Inc.</p>
            <a href="/" class="text-purple-400 hover:text-purple-300 font-medium">GreatClipsDeal.com</a>
        </div>
    </footer>
"""


def adsense_html() -> str:
    """AdSense tags, or nothing at all when ADSENSE_CLIENT is empty."""
    if not ADSENSE_CLIENT:
        return ""
    return (
        "\n    <!-- Google AdSense -->\n"
        f'    <script async src="https://pagead2.googlesyndication.com/pagead/js/'
        f'adsbygoogle.js?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>\n'
        f'    <meta name="google-adsense-account" content="{ADSENSE_CLIENT}">\n'
    )


def head_html(title: str, description: str, canonical: str, extra: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{GA_ID}');
    </script>
{adsense_html()}
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}">
    <link rel="canonical" href="{canonical}">
    <meta property="og:title" content="{esc(title)}">
    <meta property="og:description" content="{esc(description)}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:type" content="website">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}</style>
{extra}</head>
"""


# ----------------------------------------------------------- content pieces --

def hours_summary(salon: dict) -> str:
    """Collapse a week of hours into as few lines as possible."""
    hours = salon.get("hours") or {}
    if not hours:
        return ""
    runs: list[tuple[list[str], str]] = []
    for day in DAYS:
        value = hours.get(day, "Closed")
        if runs and runs[-1][1] == value:
            runs[-1][0].append(day)
        else:
            runs.append(([day], value))

    parts = []
    for days, value in runs:
        label = (
            DAY_SHORT[days[0]]
            if len(days) == 1
            else f"{DAY_SHORT[days[0]]}-{DAY_SHORT[days[-1]]}"
        )
        parts.append(f"{label} {value}")
    return " · ".join(parts)


def salon_card(salon: dict, index: int) -> str:
    hours = hours_summary(salon)
    phone = salon.get("phone") or ""
    phone_html = (
        f'<a href="{tel_href(phone)}" class="text-purple-600 hover:underline font-medium">{esc(phone)}</a>'
        if phone
        else '<span class="text-slate-400">Phone not listed</span>'
    )
    return f"""                <li class="p-5 border border-slate-200 rounded-xl bg-white">
                    <div class="flex flex-wrap items-baseline justify-between gap-2 mb-2">
                        <h3 class="font-semibold text-slate-900">
                            {index}. Great Clips &ndash; {esc(salon['street'])}
                        </h3>
                        <span class="text-xs text-slate-500">{esc(salon['zip'])}</span>
                    </div>
                    <p class="text-slate-600 text-sm mb-2">
                        {esc(salon['street'])}, {esc(salon['city'])}, {esc(salon['state'])} {esc(salon['zip'])}
                    </p>
                    <p class="text-sm mb-2">{phone_html}</p>
                    <p class="text-xs text-slate-500 mb-3">{esc(hours)}</p>
                    <div class="flex flex-wrap gap-3 text-sm">
                        <a href="{maps_url(salon)}" target="_blank" rel="nofollow noopener"
                           class="text-purple-600 hover:underline">Directions</a>
                        <a href="{esc(salon['url'])}" target="_blank" rel="nofollow noopener"
                           class="text-slate-500 hover:text-purple-600">Official salon page &amp; check-in</a>
                    </div>
                </li>
"""


def salon_schema(salon: dict, city: dict) -> dict:
    node = {
        "@type": "HairSalon",
        "name": f"Great Clips - {salon['street']}",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": salon["street"],
            "addressLocality": salon["city"],
            "addressRegion": salon["state"],
            "postalCode": salon["zip"],
            "addressCountry": "US",
        },
        "url": salon["url"],
        "priceRange": "$",
    }
    if salon.get("phone"):
        node["telephone"] = salon["phone"]
    if salon.get("lat") is not None:
        node["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": salon["lat"],
            "longitude": salon["lng"],
        }
    spec = []
    for day, value in (salon.get("hours") or {}).items():
        if "-" not in value:
            continue
        opens, _, closes = value.partition("-")
        o, c = to_24h(opens), to_24h(closes)
        if o and c and day in SCHEMA_DAY:
            spec.append(
                {
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": SCHEMA_DAY[day],
                    "opens": o,
                    "closes": c,
                }
            )
    if spec:
        node["openingHoursSpecification"] = spec
    return node


def price_line(state: str, stats: dict) -> tuple[str, str]:
    """Human sentence plus a short badge value for a state's recent prices."""
    entry = (stats.get("states") or {}).get(state)
    if not entry:
        return ("", "Varies")
    low = entry.get("lowest_price")
    median = entry.get("median_price")
    bits = []
    if low is not None:
        bits.append(f"as low as ${low:.2f}")
    if median is not None:
        bits.append(f"a median of ${median:.2f}")
    if not bits:
        return ("", "Varies")
    sentence = (
        f"Over the last six months, verified {state} Great Clips coupons ran "
        + " with ".join(bits)
        + "."
    )
    return (sentence, f"${low:.2f}" if low is not None else f"${median:.2f}")


def coverage_paragraph(city: dict, metro: dict, salon_count: int) -> str:
    """Explain, in plain language, which coupons reach this city."""
    same = metro["name"].split("-")[0].lower() == city["city"].lower()
    if same:
        return (
            f"Great Clips issues most of its offers by market rather than by single "
            f"salon. {esc(city['city'])} is the centre of the "
            f"<strong>{esc(metro['name'])} coupon market</strong>, which covers "
            f"{metro['salon_count']} salons across {metro['city_count']} nearby "
            f"communities - so a coupon advertised for this market is generally "
            f"honoured at all {salon_count} {esc(city['city'])} locations."
        )
    return (
        f"Great Clips issues most of its offers by market rather than by single "
        f"salon, which is why a coupon may be advertised for a nearby big city and "
        f"still work here. {esc(city['city'])} sits inside the "
        f"<strong>{esc(metro['name'])} coupon market</strong> "
        f"({metro['salon_count']} salons across {metro['city_count']} communities), "
        f"so {esc(metro['name'])}-area offers are generally valid at the "
        f"{salon_count} Great Clips in {esc(city['city'])}."
    )


def faq_entries(city: dict, metro: dict, stats: dict) -> list[tuple[str, str]]:
    name, state = city["city"], city["state"]
    count = city["salon_count"]
    zips = sorted({s["zip"] for s in city["salons"] if s["zip"]})
    zip_text = ", ".join(zips[:6]) + (" and others" if len(zips) > 6 else "")
    entry = (stats.get("states") or {}).get(state) or {}
    low = entry.get("lowest_price")
    cheapest = f"${low:.2f}" if low is not None else "under $10"

    plural = "salon" if count == 1 else "salons"
    faqs = [
        (
            f"How many Great Clips locations are in {name}, {state}?",
            f"There {'is' if count == 1 else 'are'} {count} Great Clips {plural} in "
            f"{name}, {state}"
            + (f", serving ZIP {zip_text}." if zips else ".")
            + f" Every address, phone number and set of hours on this page comes from "
            f"the official Great Clips salon locator.",
        ),
        (
            f"Do Great Clips coupons work in {name}?",
            f"Yes. Three kinds of coupon reach {name}: national offers valid at "
            f"participating US salons, statewide {state} offers, and "
            f"{metro['name']}-market offers, since {name} is part of the "
            f"{metro['name']} coupon market. Because participation is set by each "
            f"franchisee, confirm the offer at the salon before your cut.",
        ),
        (
            f"What is the cheapest Great Clips haircut in {name}?",
            f"Recent verified coupons in {state} have gone {cheapest} against a "
            f"regular adult haircut of roughly $17-$23, so a coupon typically saves "
            f"$5-$10. Current offers for {name} are listed at the top of this page.",
        ),
        (
            f"Do I need an appointment at Great Clips in {name}?",
            f"No. All {count} {name} {plural} take walk-ins. You can also use Online "
            f"Check-In from the salon's official page to join the waitlist before you "
            f"leave home, which usually cuts the wait to a few minutes.",
        ),
    ]
    return faqs


# ------------------------------------------------------------- page builder --

def build_city_page(
    city: dict,
    metro: dict,
    cities: dict,
    stats: dict,
    generated: str,
) -> str:
    name, state = city["city"], city["state"]
    state_name = city["state_name"]
    count = city["salon_count"]
    slug = city["slug"]
    canonical = f"{SITE_URL}/salons/{state.lower()}/{slug}"
    state_slug = state_name.lower().replace(" ", "-")
    label = f"{name}, {state}"
    plural = "salon" if count == 1 else "salons"

    price_sentence, price_badge = price_line(state, stats)
    nearby = markets.nearest_cities(city, cities, limit=10, max_mi=40.0)
    streets = [s["street"] for s in city["salons"]]

    title = (
        f"Great Clips Coupons {name} {state} - {count} Salon"
        f"{'' if count == 1 else 's'} & Haircut Deals ({generated[:4]})"
    )
    description = (
        f"Great Clips coupons for {label}: all {count} {plural} with addresses, "
        f"phone numbers and hours, plus the national, {state} and "
        f"{metro['name']}-area offers that are valid here."
    )

    intro_streets = ""
    if streets:
        shown = streets[:3]
        intro_streets = " Locations include " + ", ".join(esc(s) for s in shown)
        intro_streets += f" and {len(streets) - len(shown)} more." if len(streets) > len(shown) else "."

    # ---- JSON-LD ---------------------------------------------------------
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL},
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Salon Directory",
                "item": f"{SITE_URL}/salons",
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": state_name,
                "item": f"{SITE_URL}/{state_slug}",
            },
            {"@type": "ListItem", "position": 4, "name": label, "item": canonical},
        ],
    }
    item_list = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"Great Clips salons in {label}",
        "numberOfItems": count,
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "item": salon_schema(salon, city),
            }
            for i, salon in enumerate(city["salons"], 1)
        ],
    }
    faqs = faq_entries(city, metro, stats)
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in faqs
        ],
    }

    page_state = {
        "state": state,
        "cityKey": city["key"],
        "metroKey": city["metro_key"],
        "cityLabel": label,
    }

    extra_head = (
        '    <script type="application/ld+json">\n'
        + json.dumps(breadcrumb, separators=(",", ":"))
        + "\n    </script>\n"
        '    <script type="application/ld+json">\n'
        + json.dumps(item_list, separators=(",", ":"))
        + "\n    </script>\n"
        '    <script type="application/ld+json">\n'
        + json.dumps(faq_schema, separators=(",", ":"))
        + "\n    </script>\n"
    )

    # ---- nearby + FAQ markup --------------------------------------------
    nearby_html = "".join(
        f"""                <a href="/salons/{r['city']['state'].lower()}/{r['city']['slug']}"
                   class="flex items-center justify-between gap-2 bg-slate-50 hover:bg-purple-50 rounded-lg px-4 py-3">
                    <span class="font-medium text-slate-700">{esc(r['city']['city'])}, {esc(r['city']['state'])}</span>
                    <span class="text-xs text-slate-500">{r['city']['salon_count']} &middot; {r['distance_mi']:.0f} mi</span>
                </a>
"""
        for r in nearby
        if r["distance_mi"] is not None
    )

    faq_html = "".join(
        f"""                <div>
                    <h3 class="font-semibold text-slate-900 mb-2">{esc(q)}</h3>
                    <p class="text-slate-600">{esc(a)}</p>
                </div>
"""
        for q, a in faqs
    )

    salons_html = "".join(
        salon_card(salon, i) for i, salon in enumerate(city["salons"], 1)
    )

    body = f"""<body class="bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen">
{nav_html()}
    <div class="max-w-6xl mx-auto px-4 py-3">
        <nav class="text-sm text-slate-500" aria-label="Breadcrumb">
            <a href="/" class="hover:text-purple-600">Home</a>
            <span class="mx-2">&rsaquo;</span>
            <a href="/salons" class="hover:text-purple-600">Salons</a>
            <span class="mx-2">&rsaquo;</span>
            <a href="/{state_slug}" class="hover:text-purple-600">{esc(state_name)}</a>
            <span class="mx-2">&rsaquo;</span>
            <span class="text-slate-900">{esc(name)}</span>
        </nav>
    </div>

    <header class="bg-gradient-to-r from-violet-600 to-purple-600 text-white py-12">
        <div class="max-w-6xl mx-auto px-4">
            <div class="inline-flex items-center gap-2 bg-white/20 rounded-full px-4 py-1.5 mb-4">
                <span class="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></span>
                <span class="text-sm font-medium">Coupons checked daily</span>
            </div>
            <h1 class="text-3xl md:text-5xl font-extrabold mb-4">Great Clips Coupons in {esc(name)}, {esc(state)}</h1>
            <p class="text-lg text-white/85 max-w-3xl">
                {count} Great Clips {plural} in {esc(name)}, part of the {esc(metro['name'])} coupon market.
                Real addresses, phone numbers and hours below - plus every offer that reaches this city.
            </p>
        </div>
    </header>

    <main class="max-w-6xl mx-auto px-4 py-10">
        <section class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
            <div class="bg-white rounded-xl p-5 text-center shadow-sm">
                <div class="text-3xl font-bold text-purple-600">{count}</div>
                <div class="text-slate-600 text-sm mt-1">{esc(name)} {plural}</div>
            </div>
            <div class="bg-white rounded-xl p-5 text-center shadow-sm">
                <div class="text-3xl font-bold text-purple-600">{price_badge}</div>
                <div class="text-slate-600 text-sm mt-1">Recent {esc(state)} low</div>
            </div>
            <div class="bg-white rounded-xl p-5 text-center shadow-sm">
                <div class="text-3xl font-bold text-purple-600">{metro['salon_count']}</div>
                <div class="text-slate-600 text-sm mt-1">Salons in market</div>
            </div>
            <div class="bg-white rounded-xl p-5 text-center shadow-sm">
                <div class="text-3xl font-bold text-purple-600">{metro['city_count']}</div>
                <div class="text-slate-600 text-sm mt-1">Cities in market</div>
            </div>
        </section>

        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-4">Coupons available in {esc(name)} right now</h2>
            <div id="liveCoupons">
                <p class="text-slate-600">
                    Loading verified offers for {esc(label)}&hellip;
                    <a class="text-purple-600 underline" href="/">browse every current coupon</a>.
                </p>
            </div>
        </section>

        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-4">Which coupons are valid in {esc(name)}?</h2>
            <div class="text-slate-600 space-y-4">
                <p>{coverage_paragraph(city, metro, count)}</p>
                <p>{esc(price_sentence)}</p>
            </div>
        </section>

        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-2">
                All {count} Great Clips {plural} in {esc(name)}, {esc(state)}
            </h2>
            <p class="text-slate-500 text-sm mb-6">
                Source: official Great Clips salon locator.{intro_streets}
            </p>
            <ul class="grid gap-4 md:grid-cols-2 list-none p-0 m-0">
{salons_html}            </ul>
        </section>

        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">Great Clips near {esc(name)}</h2>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
{nearby_html}            </div>
            <p class="mt-6">
                <a href="/{state_slug}" class="text-purple-600 font-medium hover:underline">
                    See every {esc(state_name)} city with a Great Clips &rarr;
                </a>
            </p>
        </section>

        <section class="bg-white rounded-2xl shadow-sm p-8">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">{esc(name)} Great Clips FAQ</h2>
            <div class="space-y-6">
{faq_html}            </div>
        </section>
    </main>
{footer_html()}
    <script>window.__GC_PAGE__ = {json.dumps(page_state, separators=(",", ":"))};</script>
    <script src="/assets/city-coupons.js" defer></script>
</body>
</html>
"""

    return head_html(title, description, canonical, extra_head) + body


def build_directory_page(cities: dict, metros: dict, generated: str) -> str:
    """The /salons hub: every state, its salon count and its biggest markets."""
    canonical = f"{SITE_URL}/salons"
    by_state: dict[str, list[dict]] = {}
    for city in cities.values():
        by_state.setdefault(city["state"], []).append(city)

    total_salons = sum(c["salon_count"] for c in cities.values())
    rows = []
    for state in sorted(by_state):
        members = by_state[state]
        salons = sum(c["salon_count"] for c in members)
        state_name = members[0]["state_name"]
        state_slug = state_name.lower().replace(" ", "-")
        top = sorted(members, key=lambda c: -c["salon_count"])[:6]
        links = " · ".join(
            f'<a href="/salons/{c["state"].lower()}/{c["slug"]}" '
            f'class="text-purple-600 hover:underline">{esc(c["city"])}</a>'
            for c in top
        )
        rows.append(
            f"""                <div class="p-5 border border-slate-200 rounded-xl bg-white">
                    <div class="flex items-baseline justify-between gap-3 mb-2">
                        <h3 class="font-semibold text-slate-900">
                            <a href="/{state_slug}" class="hover:text-purple-600">{esc(state_name)}</a>
                        </h3>
                        <span class="text-xs text-slate-500">{salons} salons &middot; {len(members)} cities</span>
                    </div>
                    <p class="text-sm text-slate-600">{links}</p>
                </div>
"""
        )

    title = (
        f"Great Clips Salon Directory - {total_salons:,} Locations in "
        f"{len(by_state)} States"
    )
    description = (
        f"Browse Great Clips coupons by city. {total_salons:,} salons across "
        f"{len(cities):,} US cities, with addresses, phone numbers, hours and the "
        f"coupons valid at each one."
    )

    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL},
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Salon Directory",
                "item": canonical,
            },
        ],
    }
    extra = (
        '    <script type="application/ld+json">\n'
        + json.dumps(breadcrumb, separators=(",", ":"))
        + "\n    </script>\n"
    )

    big_markets = sorted(metros.values(), key=lambda m: -m["salon_count"])[:24]
    market_html = "".join(
        f"""                <li class="flex items-center justify-between gap-3 bg-slate-50 rounded-lg px-4 py-3">
                    <span class="font-medium text-slate-700">{esc(m['display_name'])}</span>
                    <span class="text-xs text-slate-500">{m['salon_count']} salons &middot; {m['city_count']} cities</span>
                </li>
"""
        for m in big_markets
    )

    body = f"""<body class="bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen">
{nav_html()}
    <header class="bg-gradient-to-r from-violet-600 to-purple-600 text-white py-12">
        <div class="max-w-6xl mx-auto px-4">
            <h1 class="text-3xl md:text-5xl font-extrabold mb-4">Great Clips Salon Directory</h1>
            <p class="text-lg text-white/85 max-w-3xl">
                {total_salons:,} Great Clips salons across {len(cities):,} US cities in
                {len(by_state)} states. Pick your city for its salon list and the coupons valid there.
            </p>
        </div>
    </header>

    <main class="max-w-6xl mx-auto px-4 py-10">
        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-4">How Great Clips coupons are scoped</h2>
            <div class="text-slate-600 space-y-3">
                <p>Great Clips runs three kinds of offer: <strong>national</strong> coupons valid at
                   participating US salons, <strong>statewide</strong> coupons, and
                   <strong>market</strong> coupons tied to a metro area such as Chicagoland or Greater
                   Houston. A market coupon covers every suburb in that market, not just the city named
                   on it - which is why a Chicagoland offer works in Schaumburg or Naperville.</p>
                <p>We map all {len(metros):,} Great Clips markets to the cities inside them, so each city
                   page shows the offers that genuinely reach it. Participation is ultimately set by each
                   franchise owner, so confirm at the salon.</p>
            </div>
        </section>

        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">Largest Great Clips markets</h2>
            <ul class="grid gap-3 md:grid-cols-2 list-none p-0 m-0">
{market_html}            </ul>
        </section>

        <section>
            <h2 class="text-2xl font-bold text-slate-900 mb-6">Browse salons by state</h2>
            <div class="grid gap-4 md:grid-cols-2">
{''.join(rows)}            </div>
        </section>
    </main>
{footer_html()}</body>
</html>
"""
    return head_html(title, description, canonical, extra) + body


# -------------------------------------------------------------------- main ---

def load_stats() -> dict:
    if STATE_STATS_FILE.exists():
        with STATE_STATS_FILE.open(encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state", help="only build this state (e.g. TX)")
    ap.add_argument("--limit", type=int, default=0, help="cap pages, for smoke tests")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--clean",
        action="store_true",
        help="remove docs/salons first (drops pages for closed salons)",
    )
    args = ap.parse_args()

    cities, metros = markets.build_all()
    markets.save_metros(cities, metros)
    stats = load_stats()
    generated = datetime.now().strftime("%Y-%m-%d")

    targets = sorted(cities.values(), key=lambda c: (c["state"], c["slug"]))
    if args.state:
        targets = [c for c in targets if c["state"] == args.state.upper()]
    if args.limit:
        targets = targets[: args.limit]

    if args.clean and OUT_DIR.exists() and not args.dry_run:
        shutil.rmtree(OUT_DIR)

    print(f"Building {len(targets):,} city pages -> {OUT_DIR.relative_to(REPO_ROOT)}")
    if args.dry_run:
        for city in targets[:20]:
            print(f"  /salons/{city['state'].lower()}/{city['slug']}  ({city['salon_count']} salons)")
        print("  (dry run, nothing written)")
        return 0

    written = 0
    total_bytes = 0
    for city in targets:
        metro = metros[city["metro_key"]]
        page = build_city_page(city, metro, cities, stats, generated)
        path = OUT_DIR / city["state"].lower() / f"{city['slug']}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            fh.write(page)
        written += 1
        total_bytes += len(page.encode("utf-8"))
        if written % 500 == 0:
            print(f"  {written:,}/{len(targets):,}")

    index = build_directory_page(cities, metros, generated)
    index_path = OUT_DIR / "index.html"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as fh:
        fh.write(index)

    asset_path = REPO_ROOT / "docs" / "assets" / "city-coupons.js"
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    with asset_path.open("w", encoding="utf-8") as fh:
        fh.write(COUPON_WIDGET_JS)

    print()
    print(f"  city pages : {written:,}")
    print(f"  directory  : /salons")
    print(f"  total size : {total_bytes / 1_048_576:.1f} MB")
    print(f"  avg page   : {total_bytes / max(written, 1) / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
