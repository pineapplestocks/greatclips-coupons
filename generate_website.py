"""
Generate the coupon website from scraped data.
Embeds coupon data directly into the HTML file.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from html import escape as html_escape

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "data", "coupons.json")
TEMPLATE_FILE = os.path.join(SCRIPT_DIR, "template.html")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "docs")  # GitHub Pages uses /docs
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")


def _ensure_utf8_stdout():
    """Keep emoji logs working on Windows terminals that default to cp1252."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


_ensure_utf8_stdout()


def escape_html(value):
    return html_escape("" if value is None else str(value), quote=True)


def js_string(value):
    return json.dumps("" if value is None else str(value))


def js_call(function_name, *args):
    call = f"{function_name}({', '.join(js_string(arg) for arg in args)})"
    return html_escape(call, quote=True)


def copy_link_handler(url):
    call = (
        f"navigator.clipboard.writeText({js_string(url)}); "
        "this.textContent='✓'; "
        "setTimeout(() => this.textContent='📋', 2000)"
    )
    return html_escape(call, quote=True)


def format_date(date_str):
    """Format an ISO timestamp like the browser-side helper."""
    if not date_str or date_str == "Unknown":
        return "Unknown"

    try:
        parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return date_str

    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    day = parsed.day
    suffix = "th"
    if day in (1, 21, 31):
        suffix = "st"
    elif day in (2, 22):
        suffix = "nd"
    elif day in (3, 23):
        suffix = "rd"
    return f"{months[parsed.month - 1]} {day}{suffix}, {parsed.year}"


def get_expiration(coupon):
    expiration = coupon.get("expiration")
    if expiration and expiration != "N/A":
        return expiration

    future_date = datetime.now() + timedelta(days=14)
    return future_date.strftime("%m/%d/%Y")


def format_city_state(coupon):
    city = re.sub(r",+$", "", coupon.get("city", "") or "").strip()
    state = (coupon.get("state") or "").strip()
    if city and state:
        return f"{city}, {state}"
    if city:
        return city
    if state:
        return state
    return ""


def is_universal(coupon):
    loc = (coupon.get("location_name") or "").strip()
    state = (coupon.get("state") or "").upper()
    address = (coupon.get("address") or "").strip()
    city = (coupon.get("city") or "").strip()

    if state in {"AREA", "UNKNOWN"} or coupon.get("area_name"):
        return False

    if state == "US":
        return True
    if "ALL US" in loc.upper() or "ALL LOCATIONS" in loc.upper():
        return True
    if (not loc or loc.upper() == "GREAT CLIPS") and not address and not city and state == "US":
        return True
    return False


def is_area_based(coupon):
    state = (coupon.get("state") or "").upper()
    loc = (coupon.get("location_name") or "").lower()
    return bool(state == "AREA" or coupon.get("area_name") or " area" in loc)


def get_price(coupon):
    try:
        return float((coupon.get("price") or "$999").replace("$", ""))
    except Exception:
        return 999.0


def get_price_badge(price):
    if price <= 5:
        return "bg-emerald-500 text-white"
    if price <= 8:
        return "bg-teal-500 text-white"
    if price <= 10:
        return "bg-amber-500 text-white"
    return "bg-orange-500 text-white"


def safe_id_component(value):
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", (value or "").strip())
    return cleaned or "other"


def render_coupon_image(coupon):
    image_url = coupon.get("image_url") or ""
    if not image_url:
        return ""

    price = coupon.get("price") or ""
    return f"""
                                            <div class="w-full h-40 overflow-hidden">
                                                <img src="{escape_html(image_url)}" alt="Great Clips Coupon {escape_html(price)}" class="w-full h-full object-cover">
                                            </div>
    """


def render_universal_card(coupon):
    price = coupon.get("price") or "N/A"
    return f"""
                                        <div class="bg-white/15 backdrop-blur-sm rounded-xl overflow-hidden hover:bg-white/25 transition-all duration-300 border border-white/20">
                                            {render_coupon_image(coupon)}
                                            <div class="p-5">
                                                <div class="flex items-start justify-between mb-4">
                                                    <div class="bg-white rounded-lg px-4 py-2 shadow-lg">
                                                        <span class="text-3xl font-extrabold gradient-text">{escape_html(price)}</span>
                                                    </div>
                                                    <span class="text-white/60 text-sm bg-white/10 px-2 py-1 rounded">
                                                        Exp: {escape_html(get_expiration(coupon))}
                                                    </span>
                                                </div>
                                                <h3 class="text-white font-semibold text-lg mb-1">Any Great Clips</h3>
                                                <p class="text-white/60 text-sm mb-4">Valid at all participating US salons</p>
                                                <div class="space-y-2">
                                                    <button onclick='{js_call("getCoupon", coupon.get("url") or "", coupon.get("price") or "", "US-wide", "", "")}'
                                                        class="block w-full bg-white text-purple-600 font-semibold py-3 px-4 rounded-lg text-center hover:bg-purple-50 transition-colors cursor-pointer">
                                                        Get your coupon now →
                                                    </button>
                                                    <button onclick='{js_call("shareCoupon", coupon.get("url") or "", coupon.get("price") or "")}'
                                                        class="w-full bg-white/20 hover:bg-white/30 text-white font-medium py-2.5 px-4 rounded-lg text-center transition-colors flex items-center justify-center gap-2">
                                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
                                                        </svg>
                                                        Share this coupon
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
    """


def render_area_card(coupon):
    price = coupon.get("price") or "N/A"
    raw_area_name = coupon.get("area_name") or coupon.get("location_name") or "Regional"
    area_name = re.sub(r"(?i)^participating\s+", "", raw_area_name)
    return f"""
                                        <div class="bg-white/15 backdrop-blur-sm rounded-xl overflow-hidden hover:bg-white/25 transition-all duration-300 border border-white/20">
                                            {render_coupon_image(coupon)}
                                            <div class="p-5">
                                                <div class="flex items-start justify-between mb-4">
                                                    <div class="bg-white rounded-lg px-4 py-2 shadow-lg">
                                                        <span class="text-3xl font-extrabold text-orange-600">{escape_html(price)}</span>
                                                    </div>
                                                    <span class="text-white/60 text-sm bg-white/10 px-2 py-1 rounded">
                                                        Exp: {escape_html(get_expiration(coupon))}
                                                    </span>
                                                </div>
                                                <h3 class="text-white font-semibold text-lg mb-1 flex items-center gap-1.5">
                                                    <svg class="w-4 h-4 flex-shrink-0 text-yellow-200" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"/></svg>
                                                    {escape_html(area_name)}
                                                </h3>
                                                <p class="text-white/60 text-sm mb-4">Valid at participating salons in this area</p>
                                                <div class="space-y-2">
                                                    <button onclick='{js_call("getCoupon", coupon.get("url") or "", coupon.get("price") or "", area_name, "", coupon.get("state") or "")}'
                                                        class="block w-full bg-white text-orange-600 font-semibold py-3 px-4 rounded-lg text-center hover:bg-orange-50 transition-colors cursor-pointer">
                                                        Get your coupon now →
                                                    </button>
                                                    <button onclick='{js_call("shareCoupon", coupon.get("url") or "", coupon.get("price") or "")}'
                                                        class="w-full bg-white/20 hover:bg-white/30 text-white font-medium py-2.5 px-4 rounded-lg text-center transition-colors flex items-center justify-center gap-2">
                                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
                                                        </svg>
                                                        Share this coupon
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
    """


def render_regular_card(coupon):
    price = get_price(coupon)
    coupon_url = coupon.get("url") or ""
    return f"""
                                            <div class="bg-white rounded-2xl shadow-md shadow-slate-200/50 overflow-hidden card-hover border border-slate-100">
                                                <div class="p-5">
                                                    <div class="flex items-start justify-between mb-4">
                                                        <span class="inline-flex items-center px-3 py-1.5 rounded-lg text-xl font-bold {get_price_badge(price)} shadow-sm">
                                                            {escape_html(coupon.get("price") or "N/A")}
                                                        </span>
                                                        <span class="text-slate-400 text-sm">
                                                            {escape_html(get_expiration(coupon))}
                                                        </span>
                                                    </div>
                                                    <h3 class="font-semibold text-slate-900 text-lg mb-1 line-clamp-2">{escape_html(coupon.get("location_name") or "Great Clips")}</h3>
                                                    <div class="text-slate-500 text-sm mb-4">
                                                        <p class="truncate">{escape_html(coupon.get("address") or "")}</p>
                                                        <p class="font-medium text-slate-600">{escape_html(format_city_state(coupon))}</p>
                                                    </div>
                                                    <div class="flex gap-2">
                                                        <button onclick='{js_call("getCoupon", coupon_url, coupon.get("price") or "", coupon.get("location_name") or "", coupon.get("city") or "", coupon.get("state") or "")}'
                                                            class="flex-1 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-semibold py-2.5 px-4 rounded-xl text-center transition-all shadow-md shadow-purple-200 cursor-pointer">
                                                            Get Coupon
                                                        </button>
                                                        <button onclick='{copy_link_handler(coupon_url)}'
                                                            class="bg-slate-100 hover:bg-slate-200 text-slate-600 p-2.5 rounded-xl transition-colors"
                                                            title="Copy link">📋</button>
                                                    </div>
                                                </div>
                                            </div>
    """


def render_state_section(state, coupons):
    state_id = safe_id_component(state)
    cards_html = "".join(render_regular_card(coupon) for coupon in coupons)
    count_label = "coupon" if len(coupons) == 1 else "coupons"
    return f"""
                                <div class="mb-10" id="state-{state_id}">
                                    <div class="flex items-center gap-3 mb-4">
                                        <h2 class="text-2xl font-bold text-slate-900">{escape_html(state)}</h2>
                                        <span class="bg-purple-100 text-purple-700 text-sm font-medium px-3 py-1 rounded-full">{len(coupons)} {count_label}</span>
                                    </div>
                                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
{cards_html}                                    </div>
                                </div>
    """


def render_universal_section(coupons):
    if not coupons:
        return ""

    max_cols = min(len(coupons), 4)
    cards_html = "".join(render_universal_card(coupon) for coupon in coupons)
    return f"""
                <section class="max-w-7xl mx-auto px-4 -mt-8 relative z-10 mb-8">
                    <div class="bg-gradient-to-r from-violet-600 via-purple-600 to-indigo-600 rounded-2xl p-1 universal-glow">
                        <div class="bg-gradient-to-r from-violet-600 via-purple-600 to-indigo-600 rounded-xl p-6 md:p-8 relative overflow-hidden">
                            <div class="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl"></div>
                            <div class="absolute bottom-0 left-0 w-48 h-48 bg-white/10 rounded-full translate-y-1/2 -translate-x-1/2 blur-3xl"></div>

                            <div class="relative">
                                <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
                                    <div>
                                        <div class="inline-flex items-center gap-2 bg-white/20 rounded-full px-3 py-1 mb-2">
                                            <svg class="w-4 h-4 text-yellow-300" fill="currentColor" viewBox="0 0 20 20">
                                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                                            </svg>
                                            <span class="text-white text-sm font-semibold">BEST VALUE</span>
                                        </div>
                                        <h2 class="text-2xl md:text-3xl font-bold text-white">Overall Best Coupon For Now</h2>
                                        <p class="text-white/70 mt-1">If you cannot find your individual location - Valid 14 days after redeeming</p>
                                    </div>
                                </div>

                                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-{max_cols} gap-4">
{cards_html}                                </div>
                            </div>
                        </div>
                    </div>
                </section>
    """


def render_area_section(coupons):
    if not coupons:
        return ""

    max_cols = min(len(coupons), 4)
    cards_html = "".join(render_area_card(coupon) for coupon in coupons)
    return f"""
                <section class="max-w-7xl mx-auto px-4 mb-8 relative z-10">
                    <div class="bg-gradient-to-r from-amber-500 via-orange-500 to-red-500 rounded-2xl p-1">
                        <div class="bg-gradient-to-r from-amber-500 via-orange-500 to-red-500 rounded-xl p-6 md:p-8 relative overflow-hidden">
                            <div class="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl"></div>
                            <div class="absolute bottom-0 left-0 w-48 h-48 bg-white/10 rounded-full translate-y-1/2 -translate-x-1/2 blur-3xl"></div>

                            <div class="relative">
                                <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
                                    <div>
                                        <div class="inline-flex items-center gap-2 bg-white/20 rounded-full px-3 py-1 mb-2">
                                            <svg class="w-4 h-4 text-yellow-200" fill="currentColor" viewBox="0 0 20 20">
                                                <path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"/>
                                            </svg>
                                            <span class="text-white text-sm font-semibold">REGIONAL DEALS</span>
                                        </div>
                                        <h2 class="text-2xl md:text-3xl font-bold text-white">Area-Based Coupons</h2>
                                        <p class="text-white/70 mt-1">Valid at participating Great Clips in specific regions</p>
                                    </div>
                                </div>

                                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-{max_cols} gap-4">
{cards_html}                                </div>
                            </div>
                        </div>
                    </div>
                </section>
    """


def render_state_options(states):
    return "".join(f'<option value="{escape_html(state)}">{escape_html(state)}</option>' for state in states)


def render_state_nav(states):
    return "".join(
        f"""
                                    <a href="#state-{safe_id_component(state)}" class="px-3 py-1.5 text-sm bg-slate-100 hover:bg-purple-100 text-slate-700 hover:text-purple-700 rounded-lg transition-colors font-medium">
                                        {escape_html(state)}
                                    </a>
        """
        for state in states
    )


def render_results_grid(regular_coupons):
    sorted_regular = sorted(regular_coupons, key=get_price)
    by_state = {}
    for coupon in sorted_regular:
        state = coupon.get("state") or "Other"
        by_state.setdefault(state, []).append(coupon)

    sorted_states = sorted(by_state.keys(), key=lambda state: (state == "Other", state))
    return "".join(render_state_section(state, by_state[state]) for state in sorted_states)


def build_static_app_html(coupons, scraped_at):
    universal_coupons = [coupon for coupon in coupons if is_universal(coupon)]
    area_coupons = [coupon for coupon in coupons if is_area_based(coupon)]
    regular_coupons = [coupon for coupon in coupons if not is_universal(coupon) and not is_area_based(coupon)]
    regular_coupons = sorted(regular_coupons, key=get_price)
    states = sorted({coupon.get("state") for coupon in regular_coupons if coupon.get("state")})
    formatted_date = format_date(scraped_at)

    universal_section = render_universal_section(universal_coupons)
    area_section = render_area_section(area_coupons)
    state_options = render_state_options(states)
    state_nav = render_state_nav(states)
    results_grid = render_results_grid(regular_coupons)
    results_count = len(regular_coupons)
    results_label = "coupon" if results_count == 1 else "coupons"

    return f"""
                <!-- Navigation -->
                <nav class="bg-white/95 backdrop-blur-sm shadow-sm sticky top-0 z-50 border-b border-slate-100">
                    <div class="max-w-7xl mx-auto px-4">
                        <div class="flex justify-between items-center h-14">
                            <a href="/" class="flex items-center gap-2">
                                <img src="https://raw.githubusercontent.com/pineapplestocks/greatclips-coupons/main/docs/logo.png" alt="GreatClipsDeal" class="h-8 w-8 rounded-full object-cover">
                                <span class="font-bold text-lg text-purple-600 hidden sm:inline">GreatClipsDeal</span>
                            </a>
                            <div class="hidden md:flex items-center gap-6 text-sm">
                                <a href="/states" class="text-slate-600 hover:text-purple-600 font-medium transition-colors">Browse by State</a>
                                <a href="/calculator" class="text-slate-600 hover:text-purple-600 font-medium transition-colors">Savings Calculator</a>
                                <a href="/how-to-use" class="text-slate-600 hover:text-purple-600 font-medium transition-colors">How to Use</a>
                                <a href="/blog" class="text-slate-600 hover:text-purple-600 font-medium transition-colors">Blog</a>
                                <a href="/faq" class="text-slate-600 hover:text-purple-600 font-medium transition-colors">FAQ</a>
                            </div>
                            <button id="mobileMenuBtn" onclick="toggleMobileMenu()" class="md:hidden text-slate-600 p-2">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
                                </svg>
                            </button>
                        </div>
                        <!-- Mobile Menu -->
                        <div id="mobileMenu" class="hidden md:hidden pb-4 border-t border-slate-100 pt-3">
                            <div class="flex flex-col gap-3">
                                <a href="/states" class="text-slate-600 hover:text-purple-600 font-medium py-1">Browse by State</a>
                                <a href="/calculator" class="text-slate-600 hover:text-purple-600 font-medium py-1">Savings Calculator</a>
                                <a href="/how-to-use" class="text-slate-600 hover:text-purple-600 font-medium py-1">How to Use</a>
                                <a href="/blog" class="text-slate-600 hover:text-purple-600 font-medium py-1">Blog</a>
                                <a href="/faq" class="text-slate-600 hover:text-purple-600 font-medium py-1">FAQ</a>
                                <a href="/about" class="text-slate-600 hover:text-purple-600 font-medium py-1">About</a>
                                <a href="/contact" class="text-slate-600 hover:text-purple-600 font-medium py-1">Contact</a>
                            </div>
                        </div>
                    </div>
                </nav>

                <!-- Header -->
                <header class="relative overflow-hidden">
                    <div class="absolute inset-0 gradient-bg opacity-95"></div>
                    <div class="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg width=\"30\" height=\"30\" viewBox=\"0 0 30 30\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Cpath d=\"M15 0C6.716 0 0 6.716 0 15c0 8.284 6.716 15 15 15 8.284 0 15-6.716 15-15C30 6.716 23.284 0 15 0zm0 27C8.373 27 3 21.627 3 15S8.373 3 15 3s12 5.373 12 12-5.373 12-12 12z\" fill=\"%23fff\" fill-opacity=\".05\"/%3E%3C/svg%3E')] opacity-30"></div>
                    <div class="relative max-w-7xl mx-auto px-4 py-12 md:py-16">
                        <div class="text-center">
                            <div class="inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm rounded-full px-4 py-1.5 mb-4 updated-badge-glow">
                                <span class="w-2 h-2 bg-emerald-400 rounded-full animate-pulse shadow-lg shadow-emerald-400/50"></span>
                                <span class="text-white text-sm font-medium">Updated {escape_html(formatted_date)}</span>
                            </div>
                            <h1 class="text-4xl md:text-5xl font-extrabold text-white mb-3 tracking-tight">
                                <span class="inline-block scissors-animation">✂️</span> Great Clips Coupons
                            </h1>
                            <p class="text-white/80 text-lg md:text-xl max-w-2xl mx-auto">
                                Find your Great Clips coupon below, <span class="relative inline-block font-bold text-white underline decoration-yellow-400 decoration-4 underline-offset-4 not-junk-glow">Not Junk<span class="absolute -top-1 -right-6 text-xs bg-yellow-400 text-yellow-900 px-1.5 py-0.5 rounded-full font-bold transform rotate-12">✓</span></span>
                            </p>
                        </div>
                    </div>
                </header>

{universal_section}
{area_section}

                <!-- Filters -->
                <section class="max-w-7xl mx-auto px-4 py-6">
                    <div class="glass rounded-2xl p-6 shadow-lg shadow-slate-200/50 border border-white/50">
                        <div class="flex items-center gap-2 mb-4">
                            <svg class="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/>
                            </svg>
                            <span class="font-semibold text-slate-700">Filter Location Coupons</span>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            <div class="relative">
                                <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                                </svg>
                                <input type="text" id="search" placeholder="Search city or location..."
                                    oninput="debounceSearch()"
                                    class="w-full pl-10 pr-4 py-3 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all outline-none">
                            </div>
                            <select id="stateFilter" onchange="renderResults()"
                                class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all outline-none appearance-none cursor-pointer">
                                <option value="">All States</option>
{state_options}
                            </select>
                            <select id="maxPrice" onchange="renderResults()"
                                class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all outline-none appearance-none cursor-pointer">
                                <option value="">Any Price</option>
                                <option value="5">Under $5</option>
                                <option value="8">Under $8</option>
                                <option value="10">Under $10</option>
                                <option value="12">Under $12</option>
                            </select>
                            <select id="sortBy" onchange="renderResults()"
                                class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all outline-none appearance-none cursor-pointer">
                                <option value="price">Price: Low to High</option>
                                <option value="expiration">Expiration Date</option>
                                <option value="location">Location Name</option>
                            </select>
                        </div>
                    </div>
                </section>

                <!-- Quick State Navigation -->
                <section class="max-w-7xl mx-auto px-4 mb-6">
                    <div class="bg-white rounded-xl shadow-sm border border-slate-100 p-4">
                        <p class="text-sm text-slate-500 mb-3 font-medium">Jump to state:</p>
                        <div class="flex flex-wrap gap-2" id="stateNav">
{state_nav}
                        </div>
                    </div>
                </section>

                <!-- Results -->
                <section class="max-w-7xl mx-auto px-4 pb-12">
                    <div class="flex items-center justify-between mb-6">
                        <p id="resultsCount" class="text-slate-600">
                            <span class="font-semibold text-slate-900">{results_count}</span> location-specific {results_label}
                        </p>
                    </div>

                    <!-- Coupons organized by state -->
                    <div id="resultsGrid">
{results_grid}                    </div>
                </section>

                <!-- Footer -->
                <footer class="bg-slate-900 text-slate-400 py-12">
                    <div class="max-w-7xl mx-auto px-4">
                        <!-- Footer Navigation Grid -->
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
                            <div>
                                <h3 class="text-white font-bold mb-4">Popular Coupons</h3>
                                <ul class="space-y-2 text-sm">
                                    <li><a href="/5-99-coupon" class="hover:text-purple-400 transition-colors">$5.99 Coupons</a></li>
                                    <li><a href="/6-99-coupon" class="hover:text-purple-400 transition-colors">$6.99 Coupons</a></li>
                                    <li><a href="/printable-coupons" class="hover:text-purple-400 transition-colors">Printable Coupons</a></li>
                                    <li><a href="/senior-discount" class="hover:text-purple-400 transition-colors">Senior Discounts</a></li>
                                </ul>
                            </div>
                            <div>
                                <h3 class="text-white font-bold mb-4">Browse by State</h3>
                                <ul class="space-y-2 text-sm">
                                    <li><a href="/california" class="hover:text-purple-400 transition-colors">California</a></li>
                                    <li><a href="/texas" class="hover:text-purple-400 transition-colors">Texas</a></li>
                                    <li><a href="/florida" class="hover:text-purple-400 transition-colors">Florida</a></li>
                                    <li><a href="/states" class="text-purple-400 hover:text-purple-300 font-medium transition-colors">All 50 States →</a></li>
                                </ul>
                            </div>
                            <div>
                                <h3 class="text-white font-bold mb-4">Resources</h3>
                                <ul class="space-y-2 text-sm">
                                    <li><a href="/how-to-use" class="hover:text-purple-400 transition-colors">How to Use Coupons</a></li>
                                    <li><a href="/prices" class="hover:text-purple-400 transition-colors">Great Clips Prices</a></li>
                                    <li><a href="/calculator" class="hover:text-purple-400 transition-colors">Savings Calculator</a></li>
                                    <li><a href="/faq" class="hover:text-purple-400 transition-colors">FAQ</a></li>
                                    <li><a href="/blog" class="hover:text-purple-400 transition-colors">Blog</a></li>
                                </ul>
                            </div>
                            <div>
                                <h3 class="text-white font-bold mb-4">Company</h3>
                                <ul class="space-y-2 text-sm">
                                    <li><a href="/about" class="hover:text-purple-400 transition-colors">About Us</a></li>
                                    <li><a href="/contact" class="hover:text-purple-400 transition-colors">Contact</a></li>
                                    <li><a href="/privacy" class="hover:text-purple-400 transition-colors">Privacy Policy</a></li>
                                    <li><a href="/terms" class="hover:text-purple-400 transition-colors">Terms of Service</a></li>
                                </ul>
                            </div>
                        </div>

                        <!-- SEO Content Section -->
                        <div class="mb-10 text-left max-w-4xl mx-auto border-t border-slate-800 pt-10">
                            <h2 class="text-xl font-bold text-white mb-4">About Great Clips Coupons</h2>
                            <p class="mb-4 text-slate-300">
                                Looking for <strong class="text-white">Great Clips coupons</strong>? You're in the right place! We update this page daily with the latest
                                <strong class="text-white">Great Clips coupon codes</strong> and <strong class="text-white">haircut deals</strong> from their Facebook ads.
                                Save $3 to $10 on your next haircut at any of the 4,400+ Great Clips salon locations across the United States and Canada.
                            </p>
                            <p class="mb-6 text-slate-300">
                                Our <strong class="text-white">Great Clips discount codes</strong> are sourced directly from official Great Clips promotions.
                                Whether you need a <strong class="text-white">cheap haircut</strong>, a <strong class="text-white">$5.99 Great Clips coupon</strong>,
                                or the best <strong class="text-white">Great Clips promo code for 2026</strong>, we've got you covered.
                            </p>

                            <h3 class="text-lg font-semibold text-white mb-3">Frequently Asked Questions</h3>
                            <div class="space-y-4 text-sm">
                                <div>
                                    <h4 class="font-medium text-white">How do I use a Great Clips coupon?</h4>
                                    <p class="text-slate-400">Click "Get Coupon" to open the offer page. Show it to the stylist before your haircut, either on your phone or printed. <a href="/how-to-use" class="text-purple-400 hover:underline">See full guide</a>.</p>
                                </div>
                                <div>
                                    <h4 class="font-medium text-white">Are these Great Clips coupons legitimate?</h4>
                                    <p class="text-slate-400">Yes! All coupons are sourced from official Great Clips Facebook advertisements and link directly to offers.greatclips.com.</p>
                                </div>
                                <div>
                                    <h4 class="font-medium text-white">How often are coupons updated?</h4>
                                    <p class="text-slate-400">We automatically scan for new Great Clips coupons every day and update this page with the latest deals.</p>
                                </div>
                                <div>
                                    <h4 class="font-medium text-white">Can I use multiple Great Clips coupons?</h4>
                                    <p class="text-slate-400">No, Great Clips coupons are limited to one per customer per visit. Choose the best deal for your location.</p>
                                </div>
                            </div>
                            <p class="mt-4"><a href="/faq" class="text-purple-400 hover:text-purple-300 font-medium">View all FAQs →</a></p>
                        </div>

                        <div class="border-t border-slate-800 pt-6 text-center">
                            <p class="mb-2">Coupons sourced from public Facebook ads • Updated daily</p>
                            <p class="text-sm text-slate-500">© 2024-2026 GreatClipsDeal.com. Not affiliated with Great Clips Inc.</p>
                        </div>
                    </div>
                </footer>
    """


def generate_website():
    print("🌐 Generating website...")
    
    # Load coupon data
    if not os.path.exists(DATA_FILE):
        print(f"❌ Data file not found: {DATA_FILE}")
        return
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    coupons = data.get('coupons', [])
    print(f"   Loaded {len(coupons)} coupons")
    
    # Load template
    if not os.path.exists(TEMPLATE_FILE):
        print(f"❌ Template not found: {TEMPLATE_FILE}")
        return
    
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    # Replace placeholder with actual data
    coupons_json = json.dumps(coupons, indent=8)
    html = re.sub(
        r'const COUPON_DATA = \[\];',
        f'const COUPON_DATA = {coupons_json};',
        html
    )

    static_app_html = build_static_app_html(coupons, data.get('scraped_at', 'Unknown'))
    html = html.replace('{{STATIC_APP_HTML}}', static_app_html)

    # Add last updated timestamp (pass full ISO date for JS formatting)
    updated_at = data.get('scraped_at', 'Unknown')
    html = html.replace('{{LAST_UPDATED}}', updated_at if updated_at else 'Unknown')
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"   ✅ Created: {OUTPUT_FILE}")
    
    # Keep sitemap updates opt-in so this build only touches the owned homepage file.
    sitemap_file = os.path.join(OUTPUT_DIR, "sitemap.xml")
    if os.environ.get("UPDATE_SITEMAP") == "1" and os.path.exists(sitemap_file):
        today = datetime.now().strftime('%Y-%m-%d')
        with open(sitemap_file, 'r', encoding='utf-8') as f:
            sitemap = f.read()
        sitemap = re.sub(r'<lastmod>\d{4}-\d{2}-\d{2}</lastmod>', f'<lastmod>{today}</lastmod>', sitemap)
        with open(sitemap_file, 'w', encoding='utf-8') as f:
            f.write(sitemap)
        print(f"   ✅ Updated sitemap date: {today}")
    
    # Stats
    us_count = sum(1 for c in coupons if c.get('state') == 'US')
    with_loc = sum(1 for c in coupons if c.get('location_name'))
    
    print()
    print("📊 Website Stats:")
    print(f"   Total coupons: {len(coupons)}")
    print(f"   Universal (US): {us_count}")
    print(f"   With location: {with_loc}")


if __name__ == "__main__":
    generate_website()
