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
import national_offer  # noqa: E402

SITE_URL = "https://greatclipsdeal.com"
REPO_ROOT = Path(__file__).resolve().parent
OUT_DIR = REPO_ROOT / "docs" / "salons"
STATE_STATS_FILE = REPO_ROOT / "data" / "state_history_stats.json"
FEED_FILE = REPO_ROOT / "docs" / "data" / "coupons.json"

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


def state_page_href(state_name: str) -> str | None:
    """Link target for a state page, or None when there isn't one.

    Every state has a page but the District of Columbia does not, so the DC city
    page's breadcrumb and the directory listing were both pointing at a 404.
    """
    slug = state_name.lower().replace(" ", "-")
    return f"/{slug}" if (REPO_ROOT / "docs" / f"{slug}.html").exists() else None


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
    var el = document.createElement('button');
    el.type = 'button';
    el.className = 'block w-full text-left bg-white rounded-xl border border-slate-200 p-5 ' +
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
        'rounded-lg px-4 py-2">Get Coupon</span>' +
      '</div>';
    // Route through the email capture rather than straight out to the offer.
    el.addEventListener('click', function () { gcOpenModal(c, null); });
    return el;
  }

  // Reveal a "Get Coupon" button on each salon, now that we know an offer reaches
  // this city. Each one carries its own street and ZIP into the signup.
  function wireSalonButtons(best) {
    var buttons = document.querySelectorAll('.gc-salon-coupon');
    for (var i = 0; i < buttons.length; i++) {
      (function (btn) {
        if (!best) return;
        btn.textContent = 'Get Coupon' + (best.price ? ' \\u2013 ' + best.price : '');
        btn.hidden = false;
        btn.classList.remove('hidden');
        btn.addEventListener('click', function () {
          gcOpenModal(best, {
            street: btn.getAttribute('data-street') || '',
            zip: btn.getAttribute('data-zip') || ''
          });
        });
      })(buttons[i]);
    }
  }

  // The nationwide section is already in the page's static HTML with its price;
  // all that is missing is the live offer link behind its button.
  function wireNationalButton(coupons) {
    var btn = document.getElementById('gcNationalBtn');
    if (!btn) return;
    var national = null;
    for (var i = 0; i < coupons.length; i++) {
      if (coupons[i].scope === 'national') { national = coupons[i]; break; }
    }
    if (!national) {
      btn.disabled = true;
      btn.textContent = 'Nationwide coupon not available right now';
      btn.className = 'bg-slate-200 text-slate-500 font-semibold py-2.5 px-5 rounded-xl';
      return;
    }
    btn.addEventListener('click', function () { gcOpenModal(national, null); });
  }

  fetch('/data/coupons.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (feed) {
      wireNationalButton(feed.coupons || []);
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
      wireSalonButtons(hits[0]);

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

// --- email capture -------------------------------------------------------
// Same contract as the homepage: POST to the worker, which stores the signup and
// mails the coupon through Brevo. Skipping is still allowed so a reader who does
// not want to hand over an address is not stranded.
var GC_WORKER_URL = 'https://greatclips-email.mehulchaudhari.workers.dev';
var gcPending = null;
var gcPendingSalon = null;
var gcModalReady = false;

// Built on first use so the markup ships once in this file, not on every page.
function gcEnsureModal() {
  if (gcModalReady || document.getElementById('gcEmailModal')) {
    gcModalReady = true;
    return;
  }
  var host = document.createElement('div');
  host.innerHTML = GC_MODAL_HTML;
  document.body.appendChild(host);
  gcModalReady = true;
}

function gcOpenModal(coupon, salon) {
  if (!coupon || !coupon.url) return;
  gcEnsureModal();
  gcPending = coupon;
  gcPendingSalon = salon;

  var page = window.__GC_PAGE__ || {};
  var label = document.getElementById('gcModalSalon');
  if (label) {
    label.textContent = salon && salon.street
      ? coupon.price + ' at Great Clips, ' + salon.street + ', ' + page.cityLabel
      : (coupon.price || '') + ' – ' + (page.cityLabel || '');
  }

  var modal = document.getElementById('gcEmailModal');
  var form = document.getElementById('gcFormView');
  var success = document.getElementById('gcSuccessView');
  if (form) form.classList.remove('hidden');
  if (success) success.classList.add('hidden');
  if (modal) modal.classList.remove('hidden');
  var input = document.getElementById('gcEmailInput');
  if (input) { input.value = ''; input.focus(); }
}

function gcCloseModal() {
  var modal = document.getElementById('gcEmailModal');
  if (modal) modal.classList.add('hidden');
}

function gcOpenCoupon() {
  var url = gcPending && gcPending.url;
  gcCloseModal();
  if (url) window.open(url, '_blank', 'noopener');
}

function gcSkipEmail() {
  gcOpenCoupon();
}

function gcSubmitEmail(event) {
  event.preventDefault();
  var input = document.getElementById('gcEmailInput');
  var btn = document.getElementById('gcSubmitBtn');
  var email = (input && input.value || '').trim();
  if (!email || email.indexOf('@') === -1) return;

  var page = window.__GC_PAGE__ || {};
  var salon = gcPendingSalon || {};
  var payload = {
    email: email,
    coupon_url: gcPending && gcPending.url,
    price: (gcPending && gcPending.price) || '',
    location_name: salon.street || (page.cityLabel || ''),
    city: (page.cityLabel || '').split(',')[0],
    state: page.state || '',
    zip_code: salon.zip || ''
  };

  var original = btn ? btn.innerHTML : '';
  if (btn) { btn.innerHTML = 'Sending... ⏳'; btn.disabled = true; }

  fetch(GC_WORKER_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(function (res) {
      if (res.ok) return res.json().catch(function () { return {}; });
      return res.json().catch(function () { return {}; }).then(function (r) {
        throw new Error(r.error || 'Unable to send your coupon');
      });
    })
    .then(function () {
      var successEmail = document.getElementById('gcSuccessEmail');
      if (successEmail) successEmail.textContent = email;
      var form = document.getElementById('gcFormView');
      var success = document.getElementById('gcSuccessView');
      if (form) form.classList.add('hidden');
      if (success) success.classList.remove('hidden');
    })
    .catch(function (err) {
      alert(err.message || 'Unable to send your coupon. Please try again.');
    })
    .then(function () {
      if (btn) { btn.innerHTML = original; btn.disabled = false; }
    });
}

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') gcCloseModal();
});
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
    # The button starts hidden: whether a coupon reaches this salon is only known
    # once /data/coupons.json loads, so city-coupons.js fills in the price and
    # reveals it. The data- attributes let the email capture record exactly which
    # salon a signup came from, ZIP included.
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
                    <button type="button" hidden
                            class="gc-salon-coupon hidden w-full mb-3 bg-gradient-to-r from-violet-600
                                   to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white
                                   font-semibold py-2.5 px-4 rounded-xl transition-all shadow-md
                                   shadow-purple-200"
                            data-street="{esc(salon['street'])}"
                            data-zip="{esc(salon['zip'])}">Get Coupon</button>
                    <div class="flex flex-wrap gap-3 text-sm">
                        <a href="{maps_url(salon)}" target="_blank" rel="nofollow noopener"
                           class="text-purple-600 hover:underline">Directions</a>
                        <a href="{esc(salon['url'])}" target="_blank" rel="nofollow noopener"
                           class="text-slate-500 hover:text-purple-600">Official salon page &amp; check-in</a>
                    </div>
                </li>
"""


def email_modal_html() -> str:
    """Email-capture modal, mirroring the homepage's so the flow feels identical.

    Injected by city-coupons.js rather than written into all 2,550 pages: it is
    identical everywhere and only matters once someone clicks, so shipping it
    statically cost ~10 MB of duplicated markup for no crawler benefit.
    """
    return """    <div id="gcEmailModal" class="hidden fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" onclick="gcCloseModal()"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl max-w-md w-full p-8">
            <button onclick="gcCloseModal()" aria-label="Close"
                    class="absolute top-4 right-4 text-slate-400 hover:text-slate-600 text-2xl">&times;</button>

            <div id="gcFormView">
                <div class="text-center mb-6">
                    <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-violet-500 to-purple-500 rounded-full mb-4">
                        <span class="text-3xl">&#9986;</span>
                    </div>
                    <h3 class="text-2xl font-bold text-slate-900">Get Your Coupon!</h3>
                    <p class="text-slate-600 mt-2">Enter your email and we&rsquo;ll send the coupon link instantly.</p>
                    <p id="gcModalSalon" class="text-sm font-medium text-purple-600 mt-3"></p>
                </div>
                <form onsubmit="gcSubmitEmail(event)" class="space-y-4">
                    <input type="email" id="gcEmailInput" placeholder="Enter your email" required
                           class="w-full px-4 py-3 border-2 border-slate-200 rounded-xl focus:border-purple-500 focus:outline-none transition-colors">
                    <button type="submit" id="gcSubmitBtn"
                            class="w-full bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-bold py-3 px-6 rounded-xl transition-all shadow-lg shadow-purple-200">
                        Send Me the Coupon &#128231;
                    </button>
                </form>
                <button onclick="gcSkipEmail()"
                        class="w-full mt-3 text-slate-500 hover:text-slate-700 text-sm py-2 transition-colors">
                    No thanks, just show me the coupon
                </button>
                <p class="text-center text-xs text-slate-400 mt-4">
                    &#128274; No spam, unsubscribe anytime. We respect your privacy.
                </p>
            </div>

            <div id="gcSuccessView" class="hidden text-center">
                <div class="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-5">
                    <span class="text-4xl">&#10003;</span>
                </div>
                <h3 class="text-2xl font-bold text-slate-900 mb-2">Coupon ready!</h3>
                <p class="text-slate-600 mb-1">A copy was also sent to:</p>
                <p class="font-semibold text-purple-600 mb-5" id="gcSuccessEmail"></p>
                <button onclick="gcOpenCoupon()"
                        class="w-full bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-bold py-3 px-6 rounded-xl transition-all">
                    Open my coupon &rarr;
                </button>
            </div>
        </div>
    </div>
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


def faq_entries(
    city: dict, metro: dict, stats: dict, national: dict | None = None
) -> list[tuple[str, str]]:
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

    # Asked first, because it is the one answer that holds for every city: a
    # nationwide coupon does not depend on where the reader is.
    if national and national.get("price"):
        faqs.insert(
            0,
            (
                f"Is there a nationwide Great Clips coupon that works in {name}?",
                f"Yes. A {national['price']} Great Clips haircut coupon is currently "
                f"running nationwide and is valid at participating Great Clips salons "
                f"anywhere in the United States, including all {count} {plural} in "
                f"{name}, {state}. It is not tied to a city or market, so it applies "
                f"here regardless of which local offers are running.",
            ),
        )
    return faqs


# ------------------------------------------------------------- page builder --

def national_section_html(offer: dict | None, city: dict) -> str:
    """Static, crawlable statement of the nationwide offer for this city."""
    if not offer:
        return ""
    count = city["salon_count"]
    price = offer.get("price") or ""
    plural = "salon" if count == 1 else "salons"
    return f"""        <section class="bg-emerald-50 border border-emerald-200 rounded-2xl p-8 mb-10">
            <div class="flex items-start gap-4">
                <span class="text-3xl leading-none">&#127758;</span>
                <div>
                    <h2 class="text-2xl font-bold text-slate-900 mb-3">
                        Nationwide Great Clips coupon &ndash; valid in {esc(city['city'])}
                    </h2>
                    <p class="text-slate-700 mb-4">
                        A <strong>{esc(price)} Great Clips haircut coupon</strong> is currently running
                        nationwide, valid at participating Great Clips salons anywhere in the United
                        States &ndash; including all {count} {plural} in
                        {esc(city['city'])}, {esc(city['state'])} listed below. Unlike the
                        market-specific offers, this one does not depend on your city.
                    </p>
                    <button type="button" id="gcNationalBtn"
                            class="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700
                                   hover:to-teal-700 text-white font-semibold py-2.5 px-5 rounded-xl
                                   transition-all shadow-md">
                        Get the {esc(price)} nationwide coupon
                    </button>
                    <p class="text-xs text-slate-500 mt-3">
                        Participation is set by each franchise owner, so confirm at the salon.
                    </p>
                </div>
            </div>
        </section>

"""


def coupons_for_city(feed_coupons: list[dict], city: dict) -> list[dict]:
    """The coupons valid in this city - Python twin of reaches() in the widget JS.

    Kept deliberately in step with COUPON_WIDGET_JS above: if the two disagree, a
    crawler and a reader see different coupons on the same page.
    """
    state = city["state"]
    city_key = city["key"]
    metro_key = city["metro_key"]
    hits = []
    for c in feed_coupons:
        scope = c.get("scope")
        if scope == "national":
            hits.append(c)
        elif scope == "state":
            states = c.get("coupon_states") or (
                [c["coupon_state"]] if c.get("coupon_state") else []
            )
            if state in states:
                hits.append(c)
        elif city_key in (c.get("city_keys") or []):
            hits.append(c)
        elif metro_key in (c.get("metro_keys") or []):
            hits.append(c)
    return sorted(hits, key=lambda c: c.get("price_value", 999))


def coupon_scope_label(coupon: dict, state: str) -> str:
    """Where one coupon is valid, in words. Twin of scopeLabel() in the widget JS."""
    scope = coupon.get("scope")
    if scope == "national":
        return "Valid at participating US salons"
    if scope == "state":
        states = coupon.get("coupon_states") or (
            [coupon["coupon_state"]] if coupon.get("coupon_state") else []
        )
        if len(states) > 1:
            return f"Valid across {', '.join(states)}"
        return f"Valid across {states[0] if states else state}"
    if scope == "salon":
        return "Salon-specific offer"
    names = coupon.get("market_names") or []
    if names:
        return f"Valid across the {' & '.join(names)} market"
    return "Regional offer"


def live_coupons_html(hits: list[dict], city: dict, label: str, scraped_at: str) -> str:
    """Static, crawlable list of the coupons that reach this city.

    The widget replaces this wholesale once /data/coupons.json loads, so it exists
    for whoever never runs the script - most AI crawlers among them. Before this,
    the served HTML followed the heading "Coupons available in Cypress right now"
    with nothing but "Loading verified offers for Cypress, TX...", which is a thin
    result on the exact query the page is built to win.

    No links to offers.greatclips.com here on purpose: the interactive cards
    already handle redemption, and 2,550 pages each sprouting a handful of
    outbound offer links is not a trade worth making for a fallback.
    """
    if not hits:
        return f"""                <p class="text-slate-600">
                    No live coupon is verified for {esc(label)} right now. National offers appear
                    here as soon as they are found &ndash;
                    <a class="text-purple-600 underline" href="/">check every current coupon</a>.
                </p>
"""

    state = city["state"]
    cards = []
    for coupon in hits[:8]:
        price = esc(coupon.get("price") or "")
        scope_text = esc(coupon_scope_label(coupon, state))
        expires = coupon.get("expiration")
        expires_html = (
            f'\n                        <p class="text-xs text-slate-500 mt-2">Expires {esc(expires)}</p>'
            if expires
            else ""
        )
        cards.append(
            f"""                    <div class="bg-white rounded-xl border border-slate-200 p-5">
                        <p class="text-2xl font-bold text-purple-600">{price}</p>
                        <p class="text-slate-700 mt-1">{scope_text}</p>{expires_html}
                    </div>
"""
        )

    shown = min(len(hits), 8)
    verified = esc((scraped_at or "")[:10])
    reach = "offer that reaches" if len(hits) == 1 else "offers that reach"
    note = f"Showing {shown} of {len(hits)} {reach} {esc(label)}."
    if verified:
        note += f" Verified {verified}."
    return f"""                <div class="grid gap-4 sm:grid-cols-2">
{''.join(cards)}                </div>
                <p class="text-xs text-slate-500 mt-4">{note}</p>
"""


def national_offer_schema(offer: dict | None, city: dict, canonical: str) -> dict | None:
    """schema.org Offer for the nationwide coupon.

    Carries the price so Google can show it as a rich result and so an LLM reading
    the page has a machine-readable figure rather than only prose. The offer code is
    deliberately absent - see load_national_offer().
    """
    if not offer:
        return None
    raw = (offer.get("price") or "").replace("$", "").strip()
    try:
        price = f"{float(raw):.2f}"
    except ValueError:
        return None

    node = {
        "@context": "https://schema.org",
        "@type": "Offer",
        "name": f"Great Clips ${price} haircut coupon (nationwide)",
        "description": (
            f"Nationwide Great Clips coupon for a ${price} haircut, valid at "
            f"participating Great Clips salons across the United States, including "
            f"{city['salon_count']} in {city['city']}, {city['state']}."
        ),
        "price": price,
        "priceCurrency": "USD",
        "availability": "https://schema.org/InStock",
        "url": canonical,
        "areaServed": {"@type": "Country", "name": "United States"},
        "itemOffered": {
            "@type": "Service",
            "name": "Haircut",
            "provider": {"@type": "Organization", "name": "Great Clips"},
        },
    }
    if offer.get("expiration"):
        node["validThrough"] = offer["expiration"]
    return node


def build_city_page(
    city: dict,
    metro: dict,
    cities: dict,
    stats: dict,
    generated: str,
    national: dict | None = None,
    feed_coupons: list[dict] | None = None,
    scraped_at: str = "",
) -> str:
    name, state = city["city"], city["state"]
    state_name = city["state_name"]
    count = city["salon_count"]
    slug = city["slug"]
    canonical = f"{SITE_URL}/salons/{state.lower()}/{slug}"
    state_slug = state_name.lower().replace(" ", "-")
    label = f"{name}, {state}"
    plural = "salon" if count == 1 else "salons"

    live_coupons = live_coupons_html(
        coupons_for_city(feed_coupons or [], city), city, label, scraped_at
    )

    price_sentence, price_badge = price_line(state, stats)
    state_href = state_page_href(state_name)
    state_crumb = (
        f'<a href="{state_href}" class="hover:text-purple-600">{esc(state_name)}</a>'
        if state_href
        else f'<span>{esc(state_name)}</span>'
    )
    state_all_link = (
        f'<a href="{state_href}" class="text-purple-600 font-medium hover:underline">'
        f'See every {esc(state_name)} city with a Great Clips &rarr;</a>'
        if state_href
        else '<a href="/salons" class="text-purple-600 font-medium hover:underline">'
             'Browse every state in the salon directory &rarr;</a>'
    )
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
    faqs = faq_entries(city, metro, stats, national)
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

    schema_nodes = [breadcrumb, item_list, faq_schema]
    offer_schema = national_offer_schema(national, city, canonical)
    if offer_schema:
        schema_nodes.insert(1, offer_schema)

    extra_head = "".join(
        '    <script type="application/ld+json">\n'
        + json.dumps(node, separators=(",", ":"))
        + "\n    </script>\n"
        for node in schema_nodes
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
            {state_crumb}
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

{national_section_html(national, city)}        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-4">Coupons available in {esc(name)} right now</h2>
            <div id="liveCoupons">
{live_coupons}            </div>
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
                {state_all_link}
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
        href = state_page_href(state_name)
        state_label = (
            f'<a href="{href}" class="hover:text-purple-600">{esc(state_name)}</a>'
            if href
            else esc(state_name)
        )
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
                            {state_label}
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

def build_llms_txt(cities: dict, metros: dict, national: dict | None) -> str:
    """docs/llms.txt - a plain-language index for AI assistants.

    Emerging convention (llmstxt.org): a short markdown brief at /llms.txt that
    tells a model what a site covers and where to look, instead of making it infer
    that from 2,550 pages. Generated rather than hand-written so the counts and the
    current nationwide price cannot drift.
    """
    total_salons = sum(c["salon_count"] for c in cities.values())
    states = sorted({c["state"] for c in cities.values()})
    biggest = sorted(metros.values(), key=lambda m: -m["salon_count"])[:10]
    # Biggest cities, not the alphabetical first - sorting by name gave eight
    # A-state examples, which tells a reader nothing about the site's coverage.
    examples = sorted(
        cities.values(), key=lambda c: (-c["salon_count"], c["state"], c["city"])
    )[:8]

    national_line = (
        f"- A **{national['price']}** coupon is currently running nationwide, valid "
        f"at participating Great Clips salons anywhere in the US.\n"
        if national and national.get("price")
        else "- No nationwide coupon is running at the moment.\n"
    )

    lines = [
        "# GreatClipsDeal",
        "",
        "> Independent directory of verified Great Clips haircut coupons, refreshed "
        "every six hours. Covers "
        f"{total_salons:,} salons across {len(cities):,} US cities in "
        f"{len(states)} states, with each salon's address, phone number and hours "
        "taken from the official Great Clips salon locator.",
        "",
        "Not affiliated with, endorsed by, or sponsored by Great Clips, Inc.",
        "",
        "## How Great Clips coupons are scoped",
        "",
        "This is the thing most sources get wrong. Great Clips issues coupons at "
        "four different scopes, and the scope decides where a coupon works:",
        "",
        "- **Nationwide** - valid at participating salons anywhere in the US.",
        "- **Statewide** - one or more whole states, e.g. \"NJ, PA & DE\".",
        "- **Market** - a metro area, e.g. \"participating Chicagoland\". A market "
        "coupon is valid across every suburb in that market, not only the city "
        "named on it, which is why a Chicagoland coupon works in Schaumburg or "
        "Naperville.",
        "- **Single salon** - one street address.",
        "",
        f"We map all {len(metros):,} Great Clips markets to the cities inside them, so "
        "each city page lists the coupons that genuinely reach it. Participation is "
        "ultimately set by each franchise owner, so a coupon should be confirmed at "
        "the salon.",
        "",
        "## Current offers",
        "",
        national_line.rstrip(),
        "- Live coupon data: https://greatclipsdeal.com/data/coupons.json "
        "(JSON; each coupon is tagged with the cities and markets it reaches)",
        "",
        "## Key pages",
        "",
        "- [Homepage](https://greatclipsdeal.com/): every current coupon, filterable "
        "by city, state and price.",
        "- [Salon directory](https://greatclipsdeal.com/salons): all "
        f"{len(cities):,} cities that have a Great Clips, grouped by state.",
        "- [How we verify coupons](https://greatclipsdeal.com/how-we-verify-coupons)",
        "- [FAQ](https://greatclipsdeal.com/faq)",
        "- [Sitemap](https://greatclipsdeal.com/sitemap.xml)",
        "",
        "## City pages",
        "",
        "One page per city at `/salons/{state}/{city}`, each listing that city's "
        "salons with address, phone, hours and the coupons valid there. Examples:",
        "",
    ]
    for city in examples:
        lines.append(
            f"- [{city['city']}, {city['state']}]"
            f"(https://greatclipsdeal.com/salons/{city['state'].lower()}/{city['slug']})"
            f" - {city['salon_count']} salons"
        )

    lines += ["", "## Largest markets", ""]
    for metro in biggest:
        lines.append(
            f"- {metro['display_name']} - {metro['salon_count']} salons across "
            f"{metro['city_count']} cities"
        )

    lines += [
        "",
        "## Data provenance",
        "",
        "- Salon addresses, phone numbers, hours and coordinates: the official "
        "Great Clips salon locator (salons.greatclips.com).",
        "- Coupon offers: Great Clips advertising, re-checked every six hours.",
        "- Location counts on this site are actual counts from the locator, not "
        "estimates.",
        "",
    ]
    return "\n".join(lines)


def load_stats() -> dict:
    if STATE_STATS_FILE.exists():
        with STATE_STATS_FILE.open(encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def load_national_offer() -> dict | None:
    """The cheapest coupon valid at participating salons anywhere in the US.

    Thin wrapper over scripts/national_offer.py, which is now shared with the
    state and metro page builders. This loader used to live here privately, and
    being the only caller is why /alabama and /cities/dallas spent months with no
    mention of a nationwide coupon that was valid at every salon they list.
    """
    return national_offer.national_offer()


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
    feed = national_offer.load_feed()
    feed_coupons = feed.get("coupons") or []
    scraped_at = feed.get("scraped_at") or ""
    national = load_national_offer()
    if feed_coupons:
        print(f"Feed: {len(feed_coupons)} coupons - rendering each city's into its HTML")
    else:
        print("Feed empty or missing; the coupon list falls back to the widget only")
    if national:
        print(f"Nationwide offer in feed: {national.get('price')} - baking into pages")
    else:
        print("No nationwide offer in the feed; pages omit that section")
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
        page = build_city_page(
            city, metro, cities, stats, generated, national, feed_coupons, scraped_at
        )
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
    modal_literal = "var GC_MODAL_HTML = " + json.dumps(email_modal_html()) + ";\n\n"
    with asset_path.open("w", encoding="utf-8") as fh:
        fh.write(modal_literal + COUPON_WIDGET_JS)

    llms_path = REPO_ROOT / "docs" / "llms.txt"
    with llms_path.open("w", encoding="utf-8") as fh:
        fh.write(build_llms_txt(cities, metros, national))
    print("  llms.txt   : /llms.txt")

    print()
    print(f"  city pages : {written:,}")
    print(f"  directory  : /salons")
    print(f"  total size : {total_bytes / 1_048_576:.1f} MB")
    print(f"  avg page   : {total_bytes / max(written, 1) / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
