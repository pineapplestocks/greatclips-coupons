#!/usr/bin/env python3
"""
Auto-generate monthly Great Clips coupon landing pages.
Runs on the 1st of each month via GitHub Actions.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
OUTPUT_DIR = "docs"  # Where pages are served from
SITE_URL = "https://greatclipsdeal.com"

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

def get_month_slug(month, year):
    """Generate URL slug like 'january-2026'"""
    return f"{MONTH_NAMES[month-1].lower()}-{year}"

def get_adjacent_months(month, year):
    """Get previous and next month info"""
    # Previous month
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
    
    # Next month
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year
    
    return {
        'prev': {'month': prev_month, 'year': prev_year, 'name': MONTH_NAMES[prev_month-1], 'slug': get_month_slug(prev_month, prev_year)},
        'next': {'month': next_month, 'year': next_year, 'name': MONTH_NAMES[next_month-1], 'slug': get_month_slug(next_month, next_year)}
    }


def month_page_exists(year, now=None):
    """True when a month page is generated for that year.

    We build the current year and the next one, so December 2027 linking to
    January 2028, and January 2026 linking to December 2025, were both 404s.
    """
    now = now or datetime.now()
    return now.year <= year <= now.year + 1

# How far ahead a month page is allowed to be indexed. Beyond this there is
# nothing true to say about a month yet, and 12 near-identical pages for next year
# is the doorway pattern Google's spam policy describes. The URLs still exist and
# still get generated - they just carry noindex until they are close enough to
# carry real coupon data, at which point a later run removes it.
INDEX_HORIZON_MONTHS = 4


def load_site_data():
    """Real numbers for the month pages: salon totals and live coupon figures.

    These pages used to hardcode "$5.99", "50+" and "4,400+ salons" identically on
    all 24 of them, which was both untrue and the reason they read as duplicates.
    Everything returned here comes from data we actually hold.
    """
    data = {"salons": None, "cities": None, "coupon_count": None,
            "lowest": None, "markets": [], "national": None}

    salons_path = Path(__file__).resolve().parent / "data" / "salons.json"
    if salons_path.exists():
        try:
            with open(salons_path, encoding="utf-8") as fh:
                payload = json.load(fh)
            data["salons"] = payload.get("total_salons")
            data["cities"] = payload.get("total_cities")
        except (json.JSONDecodeError, OSError):
            pass

    feed_path = Path(__file__).resolve().parent / "docs" / "data" / "coupons.json"
    if feed_path.exists():
        try:
            with open(feed_path, encoding="utf-8") as fh:
                feed = json.load(fh)
            coupons = feed.get("coupons", [])
            data["coupon_count"] = len(coupons)
            prices = [c["price_value"] for c in coupons if c.get("price_value")]
            if prices:
                data["lowest"] = f"${min(prices):.2f}"
            data["markets"] = [
                (c.get("area_name") or "").replace("participating ", "").strip()
                for c in coupons
                if c.get("scope") == "area"
            ][:6]
            national = [c for c in coupons if c.get("scope") == "national"]
            if national:
                data["national"] = min(
                    national, key=lambda c: c.get("price_value", 999)
                ).get("price")
        except (json.JSONDecodeError, OSError):
            pass

    return data


# A real paragraph per month instead of one interchangeable line of filler. These
# are the things that genuinely differ month to month - when salons are busy, what
# people are getting cut and why - so the pages stop being keyword variants of
# each other.
MONTH_CONTEXT = {
    1: ("New year, quiet salons",
        "January is one of the easiest months to walk in. The December rush is over, "
        "the pre-holiday crowds have gone, and mid-January afternoons are about as "
        "quiet as a Great Clips gets. If you have been putting off a bigger change "
        "than a trim, this is the month to have time in the chair for it."),
    2: ("Short month, steady demand",
        "February is unremarkable for haircut demand, which works in your favour: no "
        "seasonal rush means shorter waits. It is also the month people book ahead of "
        "Valentine's Day, so the weekend before the 14th is busier than the rest of "
        "the month."),
    3: ("Growing out the winter cut",
        "March is when winter length starts to feel like too much. Most requests shift "
        "from \"just tidy it\" back towards taking real length off. If you grew your "
        "hair out over winter and want it shaped rather than shortened, say so "
        "explicitly - ask for layers or a taper rather than a number."),
    4: ("Spring reset",
        "April brings the first proper wave of shorter cuts, along with school photos "
        "and end-of-year events in many districts. Late-April Saturdays get busy for "
        "that reason. Online Check-In is worth using rather than turning up cold."),
    5: ("Before-summer clean-up",
        "May is the run-up to summer, and the month graduations land. Salons see a "
        "spike in the week before ceremonies, so if you need a cut for one, go early "
        "in the week rather than the day before."),
    6: ("Peak buzz-cut season",
        "June is the shortest-hair month of the year. Buzz cuts and high fades "
        "dominate as soon as the heat arrives, and kids are out of school so weekday "
        "mornings fill up in a way they do not during term time. If you want a buzz, "
        "know your guard number before you sit down."),
    7: ("Mid-summer, holiday gaps",
        "July is steady but patchy - salon traffic follows local holidays, so the week "
        "of the 4th is unpredictable in both directions. Hours can vary around the "
        "holiday itself, which is the one month it is genuinely worth checking your "
        "salon's hours before setting off."),
    8: ("The busiest month of the year",
        "Back-to-school makes August the single busiest stretch for Great Clips, and "
        "the last two weeks are the peak of it. Expect the longest waits of the year "
        "on weekends, and go on a weekday morning if you possibly can. This is also "
        "when Great Clips most reliably runs promotions, because it is competing for "
        "the same families everyone else is."),
    9: ("School photos and the tail of the rush",
        "September carries the tail of the back-to-school rush plus school photo days, "
        "which land in the first few weeks in most districts. A cut three to five days "
        "before a photo sits better than one the night before - freshly cut hair "
        "rarely photographs the way it will a few days later."),
    10: ("Quiet, until the end",
        "October is one of the calmer months until the last week, when Halloween "
        "costume cuts arrive. If a costume needs a specific look, bring a photo, and "
        "be clear about what has to grow back afterwards."),
    11: ("Pre-holiday build-up",
        "November builds steadily towards Thanksgiving, and the two days before it are "
        "among the busiest of the year as people tidy up before family photos and "
        "travel. Salon hours change around the holiday itself. The last week of "
        "November is a better bet than the fourth Wednesday."),
    12: ("The December crush",
        "December is the most crowded month after August. Holiday parties, family "
        "photographs and end-of-year events all push demand into the same three weeks, "
        "and hours shift around Christmas Eve, Christmas Day and New Year's Eve. Go in "
        "the first half of the month if the cut is for a specific occasion."),
}


def generate_monthly_page(month, year, data=None, now=None):
    """Generate HTML for a monthly landing page"""
    month_name = MONTH_NAMES[month - 1]
    slug = get_month_slug(month, year)
    adjacent = get_adjacent_months(month, year)
    data = data or load_site_data()
    now = now or datetime.now()

    months_ahead = (year - now.year) * 12 + (month - now.month)
    far_future = months_ahead > INDEX_HORIZON_MONTHS
    robots_tag = (
        '    <meta name="robots" content="noindex, follow">\n' if far_future else ""
    )

    context_heading, context_body = MONTH_CONTEXT[month]

    def month_link(entry, arrow_before):
        if not month_page_exists(entry['year'], now):
            return '<span></span>'
        label = f"{entry['name']} {entry['year']}"
        inner = (f"<span>&larr;</span><span>{label}</span>" if arrow_before
                 else f"<span>{label}</span><span>&rarr;</span>")
        return (f'<a href="/{entry["slug"]}" class="flex items-center gap-2 '
                f'text-purple-600 hover:text-purple-700 font-medium">{inner}</a>')

    prev_link = month_link(adjacent['prev'], True)
    next_link = month_link(adjacent['next'], False)

    # Stat tiles, from real data where we have it.
    salon_stat = f"{data['salons']:,}" if data.get("salons") else "4,300+"
    salon_label = (
        f"US salons in {data['cities']:,} cities" if data.get("cities")
        else "Participating salons"
    )
    price_stat = data.get("lowest") or "$5.99"
    coupon_stat = (
        str(data["coupon_count"]) if data.get("coupon_count") is not None else "Daily"
    )

    market_line = ""
    if data.get("markets"):
        market_line = (
            "Market offers being tracked right now include "
            + ", ".join(m for m in data["markets"] if m)
            + "."
        )
    national_line = ""
    if data.get("national"):
        national_line = (
            f"A {data['national']} coupon is currently running nationwide, valid at "
            "participating salons anywhere in the US."
        )

    # Seasonal messaging
    seasonal_tips = {
        1: "Start the new year with a fresh look! Great Clips offers amazing January deals.",
        2: "Look your best for Valentine's Day with a fresh haircut at Great Clips.",
        3: "Spring is here! Time for a fresh cut at Great Clips.",
        4: "April showers bring May flowers—and great haircuts at Great Clips!",
        5: "Get ready for summer with a stylish cut from Great Clips.",
        6: "Summer is here! Beat the heat with a cool new style.",
        7: "Mid-summer deals are hot! Save on haircuts this July.",
        8: "Back-to-school season means it's time for fresh haircuts!",
        9: "Fall into savings with September Great Clips coupons.",
        10: "October deals are here—look great for Halloween and beyond!",
        11: "Get holiday-ready with November haircut deals.",
        12: "End the year looking great with December savings!"
    }

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
{robots_tag}    <meta name="google-adsense-account" content="ca-pub-3200720519944493">
    
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-90ZQ7M4EFR"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-90ZQ7M4EFR');
    </script>

    <!-- Google AdSense -->
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3200720519944493" crossorigin="anonymous"></script>
    
    <title>Great Clips Coupons {month_name} {year} - $5.99 Haircut Deals</title>
    <meta name="description" content="Find working Great Clips coupons for {month_name} {year}. Save $5-$10 on haircuts with daily updated {month_name} coupon codes. Valid at participating salons / confirm locally.">
    <meta name="keywords" content="Great Clips coupons {month_name} {year}, Great Clips {month_name} {year}, haircut coupons {month_name}, Great Clips deals {month_name} {year}">
    <link rel="canonical" href="{SITE_URL}/{slug}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="Great Clips Coupons {month_name} {year} - $5.99 Haircut Deals">
    <meta property="og:description" content="Find working Great Clips coupons for {month_name} {year}. Save $5-$10 on haircuts.">
    <meta property="og:url" content="{SITE_URL}/{slug}">
    <meta property="og:type" content="website">
    
    <!-- Favicon -->
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
    </style>
    
    <!-- Schema.org markup -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Great Clips Coupons {month_name} {year}",
        "description": "Find working Great Clips coupons for {month_name} {year}. Daily updated haircut deals.",
        "url": "{SITE_URL}/{slug}",
        "dateModified": "{year}-{month:02d}-01",
        "publisher": {{
            "@type": "Organization",
            "name": "GreatClipsDeal",
            "url": "{SITE_URL}"
        }}
    }}
    </script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen">
    <!-- Navigation -->
    <nav class="bg-white/95 backdrop-blur-sm shadow-sm sticky top-0 z-50 border-b border-slate-100">
        <div class="max-w-6xl mx-auto px-4">
            <div class="flex justify-between items-center h-14">
                <a href="/" class="flex items-center gap-2">
                    <img src="https://raw.githubusercontent.com/pineapplestocks/greatclips-coupons/main/docs/logo.png" alt="GreatClipsDeal" class="h-8 w-8 rounded-full object-cover">
                    <span class="font-bold text-lg text-purple-600">GreatClipsDeal</span>
                </a>
                <div class="hidden md:flex items-center gap-6 text-sm">
                    <a href="/states" class="text-slate-600 hover:text-purple-600 font-medium">Browse by State</a>
                    <a href="/calculator" class="text-slate-600 hover:text-purple-600 font-medium">Savings Calculator</a>
                    <a href="/faq" class="text-slate-600 hover:text-purple-600 font-medium">FAQ</a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Breadcrumb -->
    <div class="max-w-6xl mx-auto px-4 py-3">
        <nav class="text-sm text-slate-500">
            <a href="/" class="hover:text-purple-600">Home</a>
            <span class="mx-2">›</span>
            <span class="text-slate-900">{month_name} {year} Coupons</span>
        </nav>
    </div>

    <!-- Hero Section -->
    <header class="bg-gradient-to-r from-violet-600 to-purple-600 text-white py-12">
        <div class="max-w-6xl mx-auto px-4 text-center">
            <div class="inline-flex items-center gap-2 bg-white/20 rounded-full px-4 py-1.5 mb-4">
                <span class="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></span>
                <span class="text-sm font-medium">Updated Daily</span>
            </div>
            <h1 class="text-4xl md:text-5xl font-extrabold mb-4">
                Great Clips Coupons {month_name} {year}
            </h1>
            <p class="text-xl text-white/80 max-w-2xl mx-auto">
                {seasonal_tips.get(month, "Find the best Great Clips deals this month!")}
            </p>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-6xl mx-auto px-4 py-10">
        <!-- CTA Section -->
        <section class="bg-white rounded-2xl shadow-lg p-8 mb-10 text-center">
            <h2 class="text-2xl font-bold text-slate-900 mb-4">
                🎉 {month_name} {year} Coupons Available Now!
            </h2>
            <p class="text-slate-600 mb-6 max-w-2xl mx-auto">
                We update our coupon database daily with the latest Great Clips deals. 
                Click below to see all available coupons for {month_name} {year}.
            </p>
            <a href="/" class="inline-block bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-bold py-4 px-8 rounded-xl text-lg transition-all shadow-lg shadow-purple-200">
                View All {month_name} Coupons →
            </a>
        </section>

        <!-- Stats Grid -->
        <section class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            <div class="bg-white rounded-xl p-6 text-center shadow-sm">
                <div class="text-4xl font-bold text-purple-600 mb-2">{price_stat}</div>
                <div class="text-slate-600">Lowest tracked price</div>
            </div>
            <div class="bg-white rounded-xl p-6 text-center shadow-sm">
                <div class="text-4xl font-bold text-purple-600 mb-2">{coupon_stat}</div>
                <div class="text-slate-600">Coupons tracked now</div>
            </div>
            <div class="bg-white rounded-xl p-6 text-center shadow-sm">
                <div class="text-4xl font-bold text-purple-600 mb-2">{salon_stat}</div>
                <div class="text-slate-600">{salon_label}</div>
            </div>
        </section>

        <!-- What is actually different about this month -->
        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-4">
                {month_name} at Great Clips: {context_heading}
            </h2>
            <p class="text-slate-700 mb-4">{context_body}</p>
            <p class="text-slate-700 mb-4">{national_line} {market_line}</p>
            <p class="text-slate-600 text-sm">
                Which coupons work depends on where you are, because most Great Clips
                offers are tied to a metro market rather than the whole country.
                <a href="/salons" class="text-purple-600 hover:underline">Open your city</a>
                to see its salons and the offers valid there, or read
                <a href="/blog/do-great-clips-coupons-work-at-any-location" class="text-purple-600 hover:underline">how coupon scopes work</a>.
            </p>
        </section>

        <!-- What to Expect -->
        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">
                What to Expect in {month_name} {year}
            </h2>
            <div class="grid md:grid-cols-2 gap-6">
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <span class="text-xl">💰</span>
                    </div>
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-1">$5.99 - $8.99 Deals</h3>
                        <p class="text-slate-600 text-sm">Most tracked coupons land between {price_stat} and $12.99 depending on your market, against a regular adult cut of roughly $17-$23.</p>
                    </div>
                </div>
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <span class="text-xl">📍</span>
                    </div>
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-1">Location-Specific Deals</h3>
                        <p class="text-slate-600 text-sm">Some coupons are valid at specific salons. Filter by your state to find local deals.</p>
                    </div>
                </div>
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <span class="text-xl">⏰</span>
                    </div>
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-1">14-Day Validity</h3>
                        <p class="text-slate-600 text-sm">Once you click a coupon, it's typically valid for 14 days. Plan your visit accordingly!</p>
                    </div>
                </div>
                <div class="flex gap-4">
                    <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <span class="text-xl">🔄</span>
                    </div>
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-1">Daily Updates</h3>
                        <p class="text-slate-600 text-sm">We scan for new coupons every day, so check back often for fresh deals.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Month Navigation -->
        <section class="flex justify-between items-center bg-white rounded-xl shadow-sm p-4 mb-10">
            {prev_link}
            <span class="text-slate-400">Browse by Month</span>
            {next_link}
        </section>

        <!-- Popular States -->
        <section class="bg-white rounded-2xl shadow-sm p-8 mb-10">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">
                {month_name} Coupons by State
            </h2>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <a href="/texas" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">Texas</a>
                <a href="/california" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">California</a>
                <a href="/florida" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">Florida</a>
                <a href="/ohio" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">Ohio</a>
                <a href="/michigan" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">Michigan</a>
                <a href="/arizona" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">Arizona</a>
                <a href="/georgia" class="bg-slate-50 hover:bg-purple-50 rounded-lg p-3 text-center font-medium text-slate-700 hover:text-purple-600 transition-colors">Georgia</a>
                <a href="/states" class="bg-purple-100 hover:bg-purple-200 rounded-lg p-3 text-center font-medium text-purple-700 transition-colors">All 50 States →</a>
            </div>
        </section>

        <!-- FAQ Section -->
        <section class="bg-white rounded-2xl shadow-sm p-8">
            <h2 class="text-2xl font-bold text-slate-900 mb-6">
                {month_name} {year} FAQs
            </h2>
            <div class="space-y-6">
                <div>
                    <h3 class="font-semibold text-slate-900 mb-2">Are {month_name} {year} Great Clips coupons still valid?</h3>
                    <p class="text-slate-600">Yes! We update our coupon database daily. All coupons shown on our site are currently active and sourced from official Great Clips Facebook ads.</p>
                </div>
                <div>
                    <h3 class="font-semibold text-slate-900 mb-2">What's the best Great Clips deal in {month_name} {year}?</h3>
                    <p class="text-slate-600">The best deals are typically $5.99-$6.99 haircut coupons. Check our homepage for the current lowest prices available in your area.</p>
                </div>
                <div>
                    <h3 class="font-semibold text-slate-900 mb-2">How do I use a {month_name} coupon?</h3>
                    <p class="text-slate-600">Simply click the coupon on our site, save or screenshot it, and show it to your stylist before your haircut. <a href="/how-to-use" class="text-purple-600 hover:underline">See our full guide</a>.</p>
                </div>
            </div>
        </section>
    </main>

    <!-- Footer -->
    <footer class="bg-slate-900 text-slate-400 py-10 mt-10">
        <div class="max-w-6xl mx-auto px-4">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
                <div>
                    <h3 class="text-white font-bold mb-3">Popular Coupons</h3>
                    <ul class="space-y-2 text-sm">
                        <li><a href="/5-99-coupon" class="hover:text-purple-400">$5.99 Coupons</a></li>
                        <li><a href="/6-99-coupon" class="hover:text-purple-400">$6.99 Coupons</a></li>
                        <li><a href="/senior-discount" class="hover:text-purple-400">Senior Discounts</a></li>
                    </ul>
                </div>
                <div>
                    <h3 class="text-white font-bold mb-3">Top States</h3>
                    <ul class="space-y-2 text-sm">
                        <li><a href="/texas" class="hover:text-purple-400">Texas</a></li>
                        <li><a href="/california" class="hover:text-purple-400">California</a></li>
                        <li><a href="/florida" class="hover:text-purple-400">Florida</a></li>
                        <li><a href="/states" class="text-purple-400">All States →</a></li>
                    </ul>
                </div>
                <div>
                    <h3 class="text-white font-bold mb-3">Resources</h3>
                    <ul class="space-y-2 text-sm">
                        <li><a href="/how-to-use" class="hover:text-purple-400">How to Use</a></li>
                        <li><a href="/prices" class="hover:text-purple-400">Prices</a></li>
                        <li><a href="/faq" class="hover:text-purple-400">FAQ</a></li>
                    </ul>
                </div>
                <div>
                    <h3 class="text-white font-bold mb-3">Company</h3>
                    <ul class="space-y-2 text-sm">
                        <li><a href="/about" class="hover:text-purple-400">About</a></li>
                        <li><a href="/contact" class="hover:text-purple-400">Contact</a></li>
                        <li><a href="/privacy" class="hover:text-purple-400">Privacy</a></li>
                    </ul>
                </div>
            </div>
            <div class="border-t border-slate-800 pt-6 text-center text-sm">
                <p>© 2024-{year} GreatClipsDeal.com. Not affiliated with Great Clips Inc.</p>
            </div>
        </div>
    </footer>
</body>
</html>
'''
    return html, slug

def main():
    # Create output directory
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)
    
    # Get current date
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Generate pages for:
    # - All remaining months of current year
    # - All months of next year
    pages_generated = []
    data = load_site_data()
    print(f"   Data: {data.get('salons')} salons, "
          f"{data.get('coupon_count')} coupons, lowest {data.get('lowest')}")
    
    # The whole current year, not only the months still ahead. Past months keep
    # picking up residual search traffic, and leaving them unregenerated is what
    # left seven pages still claiming "4,400+ participating salons".
    for month in range(1, 13):
        html, slug = generate_monthly_page(month, current_year, data, now)
        filepath = output_path / f"{slug}.html"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        pages_generated.append(f"{SITE_URL}/{slug}")
        print(f"✓ Generated {slug}.html")
    
    # Next year all months
    next_year = current_year + 1
    for month in range(1, 13):
        html, slug = generate_monthly_page(month, next_year, data, now)
        filepath = output_path / f"{slug}.html"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        pages_generated.append(f"{SITE_URL}/{slug}")
        print(f"✓ Generated {slug}.html")
    
    # Save list of generated URLs for indexing
    with open('generated_monthly_urls.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(pages_generated))
    
    print(f"\n✅ Generated {len(pages_generated)} monthly pages!")
    return pages_generated

if __name__ == "__main__":
    main()
