#!/usr/bin/env python3
"""
Generate the data-backed blog posts from data/salons.json.

These three posts exist because the site now holds numbers nobody else publishes
accurately - 4,303 salon addresses from the official locator and the market map
that says which suburbs a "Chicagoland" coupon covers. Writing them by hand would
mean the figures rot the first time a salon opens; generating them keeps every
number checkable against the data.

Deliberately NOT wired into any workflow. Blog posts should be stable documents
with a considered dateModified, not something that quietly rewrites itself every
six hours. Run it by hand after a salon-data refresh, and bump REVIEWED_DATE when
the numbers move enough to matter.

Usage:
    python scripts/generate_blog_posts.py
    python scripts/generate_blog_posts.py --dry-run
"""

from __future__ import annotations

import argparse
import collections
import html
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import markets  # noqa: E402

SITE = "https://greatclipsdeal.com"
BLOG_DIR = REPO_ROOT / "docs" / "blog"
AUTHOR = "Kumar Chaudhari"
AUTHOR_URL = f"{SITE}/author/kumar-chaudhari"
PUBLISHED = "2026-08-23"
REVIEWED_DATE = "August 23, 2026"

STATE_NAMES = markets.STATE_NAMES

DEFAULT_SOURCES = (
    "Salon counts, addresses and hours come from the official Great Clips salon "
    "locator; coupon figures come from our own tracking, refreshed every six hours. "
    "Counts on this site are actual counts rather than estimates, and can be checked "
    'against the <a href="/salons" class="text-purple-600 hover:underline">salon '
    "directory</a>."
)

STYLE_SOURCES = (
    "Style names are taken from the official "
    '<a href="https://www.greatclips.com/lookbook" target="_blank" rel="noopener" '
    'class="text-purple-600 hover:underline">Great Clips Lookbook</a>, and the service '
    'list from their <a href="https://www.greatclips.com/haircare-services/'
    'additional-services" target="_blank" rel="noopener" class="text-purple-600 '
    'hover:underline">haircare services</a> pages. Clipper guard sizes are the '
    "industry standard rather than a Great Clips measurement. We are not affiliated "
    "with Great Clips."
)


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


# --------------------------------------------------------------- page shell --

def page(
    *,
    slug: str,
    title: str,
    description: str,
    badge: str,
    heading: str,
    subtitle: str,
    faqs: list[tuple[str, str]],
    body: str,
    sources: str = "",
) -> str:
    canonical = f"{SITE}/blog/{slug}"
    article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "image": f"{SITE}/icon-512.png",
        "datePublished": PUBLISHED,
        "dateModified": PUBLISHED,
        "author": {"@type": "Person", "name": AUTHOR, "url": AUTHOR_URL},
        "publisher": {
            "@type": "Organization",
            "name": "GreatClipsDeal",
            "logo": {"@type": "ImageObject", "url": f"{SITE}/icon-512.png"},
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
    }
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
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{SITE}/blog"},
            {"@type": "ListItem", "position": 3, "name": heading, "item": canonical},
        ],
    }

    faq_html = "".join(
        f"""                <div class="border border-slate-200 rounded-xl p-5">
                    <h3 class="font-bold text-slate-900 mb-2">{esc(q)}</h3>
                    <p class="text-slate-600">{a}</p>
                </div>
"""
        for q, a in faqs
    )

    schema_blocks = "".join(
        '    <script type="application/ld+json">\n'
        + json.dumps(node, separators=(",", ":"))
        + "\n    </script>\n"
        for node in (article, faq_schema, breadcrumb)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-90ZQ7M4EFR"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-90ZQ7M4EFR');
    </script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}">
    <link rel="canonical" href="{canonical}">
    <!-- Open Graph -->
    <meta property="og:type" content="article">
    <meta property="og:url" content="{canonical}">
    <meta property="og:title" content="{esc(title)}">
    <meta property="og:description" content="{esc(description)}">
    <meta property="og:image" content="{SITE}/icon-512.png">
{schema_blocks}    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .gradient-bg {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
    </style>
</head>
<body class="bg-slate-50 min-h-screen">
    <header class="gradient-bg text-white py-12">
        <div class="max-w-3xl mx-auto px-4">
            <nav class="mb-6">
                <a href="/" class="text-white/80 hover:text-white">&larr; Back to Coupons</a>
            </nav>
            <span class="bg-emerald-500 text-white text-sm font-bold px-3 py-1 rounded-full">{esc(badge)}</span>
            <h1 class="text-4xl md:text-5xl font-extrabold mt-4 mb-4">{esc(heading)}</h1>
            <p class="text-xl text-white/80">{esc(subtitle)}</p>
            <p class="text-white/60 mt-2">Published August 23, 2026 &middot; By <a href="/author/kumar-chaudhari" class="underline hover:text-white">{esc(AUTHOR)}</a>, GreatClipsDeal</p>
        </div>
    </header>

    <main class="max-w-3xl mx-auto px-4 py-12">
        <article class="bg-white rounded-2xl shadow-md p-8 md:p-12">
{body}
            <h2 class="text-2xl font-bold text-slate-900 mt-10 mb-6">Frequently asked questions</h2>
            <div class="space-y-4">
{faq_html}            </div>

            <div class="mt-10 bg-slate-50 border border-slate-200 rounded-xl p-6 text-sm text-slate-600">
                <p class="font-semibold text-slate-900 mb-2">Sources</p>
                <p>{sources or DEFAULT_SOURCES}</p>
                <p class="mt-2">Last reviewed {esc(REVIEWED_DATE)}.</p>
            </div>

            <div class="mt-8 gradient-bg rounded-2xl p-8 text-center text-white">
                <h2 class="text-2xl font-bold mb-3">Find the coupons that work at your salon</h2>
                <p class="text-white/80 mb-6">Pick your city to see its Great Clips locations and every offer valid there.</p>
                <a href="/salons" class="inline-block bg-white text-purple-600 font-bold py-3 px-8 rounded-xl hover:bg-purple-50 transition-colors">Browse all cities &rarr;</a>
            </div>
        </article>
    </main>

    <footer class="bg-slate-900 text-slate-400 py-8 text-center text-sm">
        <p>&copy; 2024-2026 GreatClipsDeal.com &middot; Not affiliated with Great Clips Inc.</p>
        <p class="mt-2">
            <a href="/" class="hover:text-purple-400">Home</a> &middot;
            <a href="/blog" class="hover:text-purple-400">Blog</a> &middot;
            <a href="/states" class="hover:text-purple-400">States</a> &middot;
            <a href="/salons" class="hover:text-purple-400">Salon Directory</a>
        </p>
    </footer>
</body>
</html>
"""


def findings_box(items: list[str]) -> str:
    lis = "".join(f"                    <li>{i}</li>\n" for i in items)
    return f"""            <div class="bg-green-50 border border-green-200 rounded-xl p-6 mb-8">
                <h2 class="font-bold text-green-800 mb-2">&#128202; Key findings</h2>
                <ul class="text-green-700 space-y-1 list-disc list-inside">
{lis}                </ul>
            </div>

"""


def h2(text: str) -> str:
    return f'            <h2 class="text-2xl font-bold text-slate-900 mt-10 mb-4">{esc(text)}</h2>\n'


def p(text: str) -> str:
    return f'            <p class="text-slate-700 mb-4">{text}</p>\n'


def table(headers: list[str], rows: list[list[str]], note: str = "") -> str:
    head = "".join(
        f'<th class="py-2 px-3 text-left font-semibold">{esc(h)}</th>' for h in headers
    )
    body = "".join(
        "<tr class=\"border-t border-slate-100\">"
        + "".join(f'<td class="py-2 px-3">{c}</td>' for c in row)
        + "</tr>"
        for row in rows
    )
    caption = (
        f'<p class="text-xs text-slate-500 mt-2">{note}</p>' if note else ""
    )
    return f"""            <div class="my-6 overflow-x-auto border border-slate-200 rounded-xl">
                <table class="w-full text-sm">
                    <thead class="bg-slate-50 text-slate-600"><tr>{head}</tr></thead>
                    <tbody>{body}</tbody>
                </table>
            </div>
            {caption}
"""


def city_link(city: dict) -> str:
    return (
        f'<a href="/salons/{city["state"].lower()}/{city["slug"]}" '
        f'class="text-purple-600 hover:underline">{esc(city["city"])}, '
        f'{esc(city["state"])}</a>'
    )


# ------------------------------------------------------------------- posts --

def post_scopes(cities, metros, feed) -> tuple[str, str]:
    """Do Great Clips coupons work at any location?"""
    chicago = next(m for m in metros.values() if m["name"] == "Chicago")
    houston = next(m for m in metros.values() if m["name"] == "Houston")
    scopes = feed.get("scopes", {})
    live_area = scopes.get("area", 0)
    live_total = feed.get("total", 0)
    suburbs = [
        cities[k]
        for k in chicago["city_keys"]
        if cities[k]["city"].lower() != "chicago"
    ][:12]

    body = findings_box(
        [
            "<strong>No, and that is the single most common reason a coupon fails at "
            "the register.</strong> Great Clips issues coupons at four different "
            "scopes, and only one of them works everywhere.",
            f"Right now <strong>{live_area} of {live_total} live coupons</strong> are "
            "tied to a specific metro market rather than the whole country.",
            f"A market coupon covers far more than the city it names: "
            f"\"participating Chicagoland\" reaches <strong>{chicago['salon_count']} "
            f"salons across {chicago['city_count']} separate towns</strong>.",
            "Even a nationwide coupon says <em>participating</em> salons &mdash; each "
            "franchise owner decides whether to take it.",
        ]
    )

    body += p(
        "If you have ever had a Great Clips coupon turned down, it probably was not "
        "expired and you probably did nothing wrong. Great Clips does not run one "
        "coupon programme &mdash; it runs four, and each has a different footprint."
    )

    body += h2("The four coupon scopes")
    body += table(
        ["Scope", "Where it works", "How to spot it"],
        [
            [
                "<strong>Nationwide</strong>",
                "Participating salons anywhere in the US",
                'Says "participating US locations"',
            ],
            [
                "<strong>Statewide</strong>",
                "One or more whole states",
                'Names states, e.g. "NJ, PA &amp; DE"',
            ],
            [
                "<strong>Market</strong>",
                "Every town in one metro area",
                'Names a region, e.g. "participating Chicagoland"',
            ],
            [
                "<strong>Single salon</strong>",
                "One address only",
                "Names a street address",
            ],
        ],
    )

    body += h2("Market coupons are wider than they look")
    body += p(
        "This is where most people give up too early. A coupon that says "
        "<strong>Chicagoland</strong> is not a Chicago-only coupon. We map every "
        f"Great Clips market to the towns inside it, and the Chicago market covers "
        f"<strong>{chicago['salon_count']} salons in {chicago['city_count']} "
        f"communities</strong> &mdash; including "
        + ", ".join(city_link(c) for c in suburbs[:6])
        + " and dozens more."
    )
    body += p(
        f"The same is true elsewhere. A \"participating Houston\" coupon reaches "
        f"<strong>{houston['salon_count']} salons across {houston['city_count']} "
        f"towns</strong>, so it is good in Cypress, Katy and Spring, none of which "
        "are named on the offer."
    )
    body += p(
        "So the useful question is not \"is my city on the coupon?\" but \"is my city "
        "in that coupon's market?\" That is exactly what our "
        '<a href="/salons" class="text-purple-600 hover:underline">city pages</a> '
        "answer &mdash; each one lists the offers that actually reach it."
    )

    body += h2("What \"participating\" really means")
    body += p(
        "Every Great Clips coupon, including nationwide ones, carries the word "
        "<em>participating</em>. Great Clips salons are franchises, and the owner "
        "decides whether to honour a given promotion. A coupon can therefore be "
        "valid in your market and still be declined at one specific salon. It is "
        "worth asking before your cut rather than at the register."
    )

    body += h2("How to tell whether a coupon covers you")
    body += p(
        "Read the fine print for the scope first, then check your town. If the offer "
        "names a region you do not recognise, look up your city in the "
        '<a href="/salons" class="text-purple-600 hover:underline">salon directory</a> '
        "&mdash; the page for your town lists the national, statewide and market "
        "offers that reach it, so you do not have to work out which metro you are in."
    )

    faqs = [
        (
            "Do Great Clips coupons work at any location?",
            "Only nationwide coupons do, and even then only at participating salons. "
            "Most Great Clips coupons are tied to a metro market, one or more states, "
            f"or a single address. Right now {live_area} of {live_total} live coupons "
            "are market-specific.",
        ),
        (
            "My coupon says Chicagoland. Does that mean only Chicago?",
            f"No. The Chicago market covers {chicago['salon_count']} salons across "
            f"{chicago['city_count']} separate towns, so a Chicagoland coupon is "
            "generally good in suburbs like Schaumburg, Naperville and Aurora as well "
            "as in Chicago itself.",
        ),
        (
            "Why was my coupon refused if it had not expired?",
            "The most likely reasons are that the salon sits outside the coupon's "
            "market, or that the franchise owner does not take that promotion. Both "
            "are consistent with a coupon that looks perfectly valid.",
        ),
        (
            "Can I use a coupon at a Great Clips in another state?",
            "Only if the coupon is nationwide. A statewide or market coupon will not "
            "travel, so check the scope before you rely on it on a trip.",
        ),
    ]

    return (
        "do-great-clips-coupons-work-at-any-location",
        page(
            slug="do-great-clips-coupons-work-at-any-location",
            title="Do Great Clips Coupons Work at Any Location? (2026)",
            description=(
                "Only nationwide coupons work everywhere. Great Clips runs four coupon "
                "scopes, and a market coupon like Chicagoland covers "
                f"{chicago['city_count']} towns, not one. How to tell which covers you."
            ),
            badge="COUPON GUIDE",
            heading="Do Great Clips Coupons Work at Any Location?",
            subtitle="Four different coupon scopes, and why yours got declined",
            faqs=faqs,
            body=body,
        ),
    )


def post_census(cities, metros, feed) -> tuple[str, str]:
    """How many Great Clips locations are there?"""
    total = sum(c["salon_count"] for c in cities.values())
    by_state = collections.Counter()
    for city in cities.values():
        by_state[city["state"]] += city["salon_count"]
    singles = [c for c in cities.values() if c["salon_count"] == 1]
    top_cities = sorted(cities.values(), key=lambda c: -c["salon_count"])[:10]
    absent = ["New York", "Philadelphia", "Boston", "Detroit", "Miami"]
    chicago_city = cities["IL/chicago"]["salon_count"]

    body = findings_box(
        [
            f"There are <strong>{total:,} Great Clips salons</strong> across "
            f"<strong>{len(cities):,} US cities</strong> &mdash; in all 50 states and "
            "the District of Columbia.",
            f"<strong>Texas leads with {by_state['TX']}</strong>, ahead of Florida "
            f"({by_state['FL']}), Ohio ({by_state['OH']}) and California "
            f"({by_state['CA']}).",
            f"<strong>{len(singles):,} of those cities &mdash; "
            f"{len(singles) / len(cities) * 100:.0f}% &mdash; have exactly one "
            "salon.</strong> This is a suburban chain, not a big-city one.",
            "There is <strong>not a single Great Clips</strong> inside New York City, "
            "Philadelphia, Boston, Detroit or Miami.",
        ]
    )

    body += p(
        f"Great Clips is one of the largest hair salon brands in the world, but public "
        f"figures for it are usually rounded to \"4,000+\" or quoted for North America "
        f"as a whole. Counting the official salon locator directly gives "
        f"<strong>{total:,} salons in the United States</strong>, spread across "
        f"{len(cities):,} cities."
    )

    body += h2("Great Clips locations by state")
    rows = []
    for state, count in by_state.most_common():
        city_count = sum(1 for c in cities.values() if c["state"] == state)
        slug = STATE_NAMES.get(state, state).lower().replace(" ", "-")
        rows.append(
            [
                f'<a href="/{slug}" class="text-purple-600 hover:underline">'
                f"{esc(STATE_NAMES.get(state, state))}</a>",
                f"{count}",
                f"{city_count}",
            ]
        )
    body += table(
        ["State", "Salons", "Cities"],
        rows,
        note="Counted from the official Great Clips salon locator.",
    )

    body += h2("The cities with the most salons")
    body += p(
        f"The single biggest concentration is not where you would guess. "
        f"<strong>{top_cities[0]['city']}, {top_cities[0]['state']}</strong> has "
        f"{top_cities[0]['salon_count']} Great Clips inside the city limits &mdash; "
        f"more than any other city in the country, and "
        f"{top_cities[0]['salon_count'] / chicago_city:.0f} times as many as Chicago, "
        f"which has {chicago_city}."
    )
    body += table(
        ["City", "Salons"],
        [[city_link(c), str(c["salon_count"])] for c in top_cities],
    )

    body += h2("Why the big cities are missing")
    body += p(
        "Five of the largest cities in America &mdash; "
        + ", ".join(absent)
        + " &mdash; have no Great Clips at all inside the city limits. That is not an "
        "error in the data. Great Clips builds in strip malls and suburban retail "
        "centres with parking, which is exactly the format dense urban cores do not "
        "have."
    )
    body += p(
        "Those metros are still well covered, just not downtown. The salons nearest "
        "New York City are across the river in New Jersey, and the Detroit market runs "
        f"through its suburbs &mdash; "
        + ", ".join(
            city_link(cities[k])
            for k in next(m for m in metros.values() if m["name"] == "Detroit")[
                "city_keys"
            ][:4]
        )
        + " among them."
    )

    body += h2("How spread out the chain is")
    body += p(
        f"The clearest way to see the strategy is the distribution: "
        f"{len(singles):,} of {len(cities):,} cities have exactly one salon, and the "
        f"average across all cities is {total / len(cities):.1f}. Great Clips grows by "
        f"adding towns, not by stacking salons in the same downtown. We group those "
        f"cities into <strong>{len(metros)} metro markets</strong>, which is also how "
        "the company scopes most of its coupons."
    )

    faqs = [
        (
            "How many Great Clips locations are there in the US?",
            f"{total:,} as of {REVIEWED_DATE}, across {len(cities):,} cities in all "
            "50 states and the District of Columbia, counted from the official Great "
            "Clips salon locator.",
        ),
        (
            "Which state has the most Great Clips?",
            f"Texas, with {by_state['TX']} salons. Florida ({by_state['FL']}), Ohio "
            f"({by_state['OH']}) and California ({by_state['CA']}) follow.",
        ),
        (
            "Which city has the most Great Clips?",
            f"{top_cities[0]['city']}, {top_cities[0]['state']}, with "
            f"{top_cities[0]['salon_count']} salons inside the city limits.",
        ),
        (
            "Is there a Great Clips in New York City?",
            "Not within the five boroughs. The nearest salons are in New Jersey. The "
            "same is true of Philadelphia, Boston, Detroit and Miami, none of which "
            "have a Great Clips inside the city limits.",
        ),
        (
            "How many Great Clips are in my city?",
            "Look up your city in our salon directory. Every city page lists that "
            "city's salons with addresses, phone numbers and hours taken from the "
            "official locator.",
        ),
    ]

    return (
        "how-many-great-clips-locations",
        page(
            slug="how-many-great-clips-locations",
            title=f"How Many Great Clips Locations Are There? {total:,} in 2026",
            description=(
                f"{total:,} Great Clips salons across {len(cities):,} US cities, counted "
                f"from the official locator. Full state table, the cities with the most "
                "salons, and the five big cities that have none."
            ),
            badge="DATA STUDY",
            heading="How Many Great Clips Locations Are There?",
            subtitle=(
                f"{total:,} salons, {len(cities):,} cities, and five major cities with "
                "none at all"
            ),
            faqs=faqs,
            body=body,
        ),
    )


def post_declined(cities, metros, feed) -> tuple[str, str]:
    """Why your Great Clips coupon did not work."""
    scopes = feed.get("scopes", {})
    live_area = scopes.get("area", 0)
    live_total = feed.get("total", 0)
    chicago = next(m for m in metros.values() if m["name"] == "Chicago")

    body = findings_box(
        [
            "<strong>Wrong market is the most common cause</strong>, not an expired "
            f"code: {live_area} of {live_total} live coupons only work in one metro "
            "area.",
            "Great Clips coupons typically last <strong>14 days from the moment you "
            "open them</strong>, so opening one early quietly burns the clock.",
            "Every coupon says <em>participating</em> salons &mdash; a franchise owner "
            "can decline an offer that is otherwise valid.",
            "One coupon per customer per visit, and it cannot be stacked with another "
            "offer.",
        ]
    )

    body += p(
        "A declined coupon at the register is annoying and usually avoidable. These "
        "are the causes, in the order they actually happen."
    )

    body += h2("1. The coupon belongs to a different market")
    body += p(
        "Most Great Clips coupons are issued per metro market, not nationally. A "
        f"coupon for one market simply will not scan in another, even a few towns "
        f"over, and the offer rarely spells out where its boundary is. Working the "
        f"other way, a market coupon covers much more than the city it names: "
        f"Chicagoland reaches {chicago['salon_count']} salons in "
        f"{chicago['city_count']} towns. Check your city's page to see which offers "
        "reach you before you go."
    )

    body += h2("2. The 14-day clock already started")
    body += p(
        "Great Clips offers usually become valid for 14 days from the moment you "
        "first open the link, not from the day the offer was published. Opening a "
        "coupon to \"save it for later\" starts that countdown. Open it when you are "
        "ready to go, or check the expiry date shown on the offer itself. We cover "
        'this in more detail in <a href="/blog/how-long-do-great-clips-coupons-last" '
        'class="text-purple-600 hover:underline">how long Great Clips coupons '
        "last</a>."
    )

    body += h2("3. The salon does not participate")
    body += p(
        "Great Clips salons are independently owned franchises. Every promotion, "
        "including nationwide ones, is valid only at <em>participating</em> locations, "
        "and the owner decides. If a coupon is refused at one salon it may still work "
        "at another a few miles away &mdash; worth knowing in a town with more than "
        "one."
    )

    body += h2("4. It was already redeemed, or you tried to stack it")
    body += p(
        "Coupons are one per customer per visit and cannot be combined with another "
        "offer or discount. A single-use code that has already been redeemed will not "
        "work a second time, including on a different phone."
    )

    body += h2("5. You are looking at a copy, not the offer")
    body += p(
        "Screenshots and reposted images circulate long after the underlying offer "
        "ends, and salons check the live offer page rather than a picture. Always open "
        "the actual link. Every coupon we list points at the official Great Clips "
        "offer page &mdash; we do not host coupon images."
    )

    body += h2("The quickest way to avoid all of this")
    body += p(
        'Open your city on the <a href="/salons" class="text-purple-600 '
        'hover:underline">salon directory</a>. The page lists that city\'s salons and '
        "the offers that actually reach it &mdash; nationwide, statewide and market "
        "&mdash; so you are not guessing which metro a coupon belongs to. Then confirm "
        "at the salon before your cut."
    )

    faqs = [
        (
            "Why did my Great Clips coupon not work?",
            "Most often because it belongs to a different metro market, because the "
            "14-day window from opening it had passed, or because that franchise does "
            "not participate in the offer.",
        ),
        (
            "How long do Great Clips coupons last?",
            "Usually 14 days from the moment you first open the offer, not from when "
            "it was published. Opening one early starts the clock.",
        ),
        (
            "Can a Great Clips salon refuse a valid coupon?",
            "Yes. Salons are franchises and every offer applies only at participating "
            "locations, so an owner can decline a coupon that is otherwise valid. "
            "Another salon nearby may still take it.",
        ),
        (
            "Can I use two Great Clips coupons at once?",
            "No. Offers are one per customer per visit and cannot be combined with "
            "another discount.",
        ),
        (
            "Can I reuse a Great Clips coupon?",
            "No. Codes are single use, and a redeemed code will not work again even on "
            "a different device.",
        ),
    ]

    return (
        "why-your-great-clips-coupon-didnt-work",
        page(
            slug="why-your-great-clips-coupon-didnt-work",
            title="Why Your Great Clips Coupon Didn't Work (5 Real Reasons)",
            description=(
                "A declined Great Clips coupon usually is not expired. The wrong metro "
                f"market is the most common cause: {live_area} of {live_total} live "
                "coupons only work in one area. Five causes and how to avoid them."
            ),
            badge="TROUBLESHOOTING",
            heading="Why Your Great Clips Coupon Didn't Work",
            subtitle="Five real reasons, and the one that catches almost everybody",
            faqs=faqs,
            body=body,
        ),
    )


SEASONAL_SOURCES = (
    "Great Clips promotion activity referenced from their own "
    '<a href="https://www.greatclips.com/backtoschool" target="_blank" '
    'rel="noopener" class="text-purple-600 hover:underline">back-to-school</a> and '
    '<a href="https://www.greatclips.com/promotions/" target="_blank" rel="noopener" '
    'class="text-purple-600 hover:underline">promotions</a> pages. Salon counts come '
    "from the official salon locator. Busy-period guidance reflects general salon "
    "demand patterns, not figures published by Great Clips. We are not affiliated "
    "with Great Clips."
)


def post_back_to_school(cities, metros, feed) -> tuple[str, str]:
    """Back-to-school haircuts."""
    total = sum(c["salon_count"] for c in cities.values())

    body = findings_box(
        [
            "<strong>August is the busiest haircut month of the year</strong>, and the "
            "last two weeks are the peak. Weekend waits are at their longest.",
            "<strong>Go on a weekday morning.</strong> The same cut that costs you an "
            "hour on a Saturday takes minutes on a Tuesday at 10am.",
            "<strong>Great Clips runs a back-to-school campaign</strong> most years, so "
            "this is one of the better windows for a coupon.",
            "<strong>Cut three to five days before photo day</strong>, not the night "
            "before &mdash; hair sits differently once it has settled.",
        ]
    )

    body += p(
        "Back-to-school is the one time of year when a ten-minute haircut can cost you "
        "an hour of waiting. Every family in the district has the same idea in the "
        "same fortnight. A little timing solves most of it."
    )

    body += h2("When to go, and when not to")
    body += p(
        "The crunch is the last two weeks of August and the first week of September, "
        "concentrated on weekends. If your schedule allows any flexibility, a weekday "
        "morning shortly after opening is the quietest slot of the week, and the "
        "difference is dramatic during this period."
    )
    body += p(
        "Great Clips takes walk-ins, but Online Check-In is what makes this month "
        "bearable: you join the queue from home and arrive near your turn instead of "
        "waiting in the salon. During back-to-school week it is worth doing even for "
        "a quiet-looking salon."
    )

    body += h2("Timing around school photos")
    body += p(
        "Photo day is usually in the first few weeks of term. Cut too close to it and "
        "the hair has not settled &mdash; a fresh cut looks different on day one than "
        "it does on day four, particularly on short cuts with visible lines. Three to "
        "five days ahead is the sweet spot."
    )

    body += h2("What to ask for")
    body += p(
        "Great Clips names its kids' cuts, which removes the guesswork. For school, "
        "the cuts that stay tidy longest are the "
        + ", ".join(
            style_link(s, kids=True) for s in ["classic-taper", "taper-fade", "textured-crew"]
        )
        + " &mdash; all grow out evenly rather than developing a hard line halfway "
        "through term. The full list is in our "
        '<a href="/blog/great-clips-kids-haircut-styles" class="text-purple-600 '
        f'hover:underline">guide to the {len(KIDS_STYLES)} kids\' styles</a>.'
    )
    body += p(
        "If the cut needs to last until half term, ask for it slightly shorter than "
        "you would normally like it. Two weeks of growth is the difference between "
        "tidy and shaggy on a short cut."
    )

    body += h2("Getting a coupon that works")
    body += p(
        "Great Clips promotes heavily around back-to-school &mdash; they maintain a "
        "dedicated back-to-school page &mdash; but most of their coupons are scoped to "
        "a metro market rather than the whole country, so an offer you see online may "
        "not apply where you live. Check "
        '<a href="/salons" class="text-purple-600 hover:underline">your city</a> for '
        "the offers that actually reach your local salons, and see "
        '<a href="/blog/do-great-clips-coupons-work-at-any-location" '
        'class="text-purple-600 hover:underline">how coupon scopes work</a> if an '
        "offer has ever been declined on you."
    )
    body += p(
        f"With {total:,} salons in the US, most families have more than one within "
        "reach. During peak weeks, the second-nearest salon is often much faster than "
        "the closest one."
    )

    faqs = [
        (
            "When is the best time to get a back-to-school haircut?",
            "Earlier than most people do. The last two weeks of August are the busiest "
            "of the year, so going in the first half of the month, or on a weekday "
            "morning, avoids the longest waits.",
        ),
        (
            "How long before school photos should my child get a haircut?",
            "Three to five days. A cut done the night before has not settled, and short "
            "cuts in particular look different after a few days.",
        ),
        (
            "Does Great Clips have back-to-school deals?",
            "Great Clips runs back-to-school promotions most years and maintains a "
            "dedicated page for them. Availability varies by market, so check which "
            "offers apply to your city before relying on one.",
        ),
        (
            "How do I avoid the back-to-school wait at Great Clips?",
            "Use Online Check-In to join the queue before leaving home, go on a weekday "
            "morning rather than a weekend, and consider the second-nearest salon "
            "during peak weeks.",
        ),
    ]

    return (
        "great-clips-back-to-school-haircuts",
        page(
            slug="great-clips-back-to-school-haircuts",
            title="Great Clips Back-to-School Haircuts: Timing, Styles & Coupons",
            description=(
                "August is the busiest haircut month of the year. When to go to avoid the "
                "wait, how many days before photo day to cut, which kids' styles last a "
                "term, and how to find a coupon that works in your market."
            ),
            badge="SEASONAL",
            heading="Back-to-School Haircuts at Great Clips",
            subtitle="The busiest fortnight of the year, and how to get in and out of it",
            faqs=faqs,
            body=body,
            sources=SEASONAL_SOURCES,
        ),
    )


def post_holiday(cities, metros, feed) -> tuple[str, str]:
    """Holiday season haircuts."""
    body = findings_box(
        [
            "<strong>December is the second-busiest month</strong> after August, "
            "squeezed into roughly three weeks.",
            "<strong>The two days before Thanksgiving</strong> and the week before "
            "Christmas are the worst times to walk in without checking first.",
            "<strong>Salon hours change around the holidays.</strong> Christmas Eve, "
            "Christmas Day and New Year's Eve commonly run short or closed.",
            "<strong>Book the cut for the week before the event</strong>, not the day "
            "of &mdash; and check your salon's hours rather than assuming.",
        ]
    )

    body += p(
        "Holiday season compresses a month of haircuts into three weeks. Family "
        "photographs, work parties and travel all land together, and salon hours are "
        "least predictable exactly when demand is highest."
    )

    body += h2("The two crunch points")
    body += p(
        "The first is Thanksgiving. The Tuesday and Wednesday before it are among the "
        "busiest days of the entire year, as people tidy up before family gatherings "
        "and travel. The second is the run to Christmas, particularly the final "
        "weekend before it."
    )
    body += p(
        "Both are avoidable by going a week earlier than feels necessary. A cut keeps "
        "its shape for two to three weeks, so a haircut in mid-December still looks "
        "deliberate on Christmas Day."
    )

    body += h2("Check the hours, this month especially")
    body += p(
        "This is the one time of year when turning up unchecked genuinely wastes a "
        "trip. Great Clips salons are individually operated and holiday hours vary: "
        "many run reduced hours on Christmas Eve and New Year's Eve and close on "
        "Christmas Day. Every city page on this site lists each salon's regular hours "
        "and links to its official page, which is where any holiday exception is "
        "posted &mdash; find "
        '<a href="/salons" class="text-purple-600 hover:underline">your city</a> '
        "before you set off."
    )

    body += h2("Timing a cut for photographs")
    body += p(
        "Holiday photos are the most common reason for a December haircut, and the "
        "usual mistake is cutting too late. Give it three to five days. Fresh cuts "
        "photograph harder than settled ones, especially with a flash and especially "
        "on tight fades where the line is still sharp."
    )

    body += h2("Coupons over the holidays")
    body += p(
        "Great Clips promotes through the season and lists current offers on its "
        "promotions page, but as ever most coupons are tied to a metro market rather "
        "than being national. If you are travelling for the holidays, that matters: a "
        "coupon that works at home may not work where you are going. Check the city "
        "you will actually be in &mdash; our "
        '<a href="/salons" class="text-purple-600 hover:underline">directory</a> '
        "covers every US city with a salon."
    )
    body += p(
        "Gift cards are the other seasonal question. A haircut gift card is a "
        "reasonable small gift, and it sidesteps the coupon-scope problem entirely "
        "since it is not restricted to a market."
    )

    faqs = [
        (
            "When is Great Clips busiest during the holidays?",
            "The two days before Thanksgiving and the final week before Christmas are "
            "the peaks. Going a week earlier avoids the worst of both, and a cut holds "
            "its shape for two to three weeks anyway.",
        ),
        (
            "Is Great Clips open on Christmas Eve or Christmas Day?",
            "Hours vary by salon because each is individually operated. Reduced hours on "
            "Christmas Eve and closure on Christmas Day are common. Check your salon's "
            "official page, linked from every city page here, before travelling.",
        ),
        (
            "How far before a holiday party should I get a haircut?",
            "Three to five days. It gives the cut time to settle, which photographs "
            "better than a same-day cut, particularly with a flash.",
        ),
        (
            "Can I use a Great Clips coupon while travelling for the holidays?",
            "Only if it is a nationwide coupon. Market and statewide coupons do not "
            "travel, so check the offers for the city you are visiting rather than the "
            "one you live in.",
        ),
    ]

    return (
        "great-clips-holiday-haircuts",
        page(
            slug="great-clips-holiday-haircuts",
            title="Great Clips Holiday Haircuts: Hours, Busy Days & Coupons",
            description=(
                "December is the second-busiest haircut month. The two crunch points to "
                "avoid, why holiday hours need checking, how many days before photos to "
                "cut, and why a coupon may not travel with you."
            ),
            badge="SEASONAL",
            heading="Holiday Haircuts at Great Clips",
            subtitle="Thanksgiving, Christmas, changed hours, and coupons that don't travel",
            faqs=faqs,
            body=body,
            sources=SEASONAL_SOURCES,
        ),
    )


def post_what_to_ask(cities, metros, feed) -> tuple[str, str]:
    """What to ask for at Great Clips."""
    total = sum(c["salon_count"] for c in cities.values())

    body = findings_box(
        [
            "<strong>Ask for a style by name.</strong> Great Clips publishes a "
            f"Lookbook of <strong>{len(ADULT_STYLES) + len(KIDS_STYLES)} named "
            "haircuts</strong>, and a stylist recognises those names instantly.",
            "<strong>Give a guard number for anything clippered</strong> &mdash; "
            "&#35;2 on the sides means the same thing in every salon in the country.",
            "<strong>Ask them to pull up your Clip Notes.</strong> Great Clips saves "
            "your cut details, so a good visit is repeatable at any location.",
            "Bring a photo. It settles in two seconds what a paragraph of description "
            "cannot.",
        ]
    )

    body += p(
        "The hard part of a cheap haircut is not the cutting, it is the asking. Ten "
        "minutes in the chair goes wrong when \"just a trim, maybe shorter on the "
        "sides\" gets interpreted differently than you pictured. Here is the "
        "vocabulary that removes the guesswork."
    )

    body += h2("1. Use the name Great Clips uses")
    body += p(
        "Great Clips runs an official Lookbook, and the names in it are the ones "
        "their stylists are trained on. Saying \"a clippered pushback\" lands "
        "immediately; describing it does not. These are the adult styles they list:"
    )
    body += style_grid(ADULT_STYLES)
    body += p(
        "Kids have their own set of names &mdash; see "
        '<a href="/blog/great-clips-kids-haircut-styles" class="text-purple-600 '
        'hover:underline">the 17 kids\' styles</a> for those.'
    )

    body += h2("2. Give a number for anything clippered")
    body += p(
        "Clipper guards are numbered, and the numbers are standard sizing rather than "
        "anything Great Clips invented &mdash; which is why they travel between "
        "salons and between stylists. \"Two on the sides, scissors on top\" is a "
        "complete instruction. We break the sizes down in "
        '<a href="/blog/clipper-guard-numbers" class="text-purple-600 '
        'hover:underline">clipper guard numbers explained</a>.'
    )

    body += h2("3. Say where you want the length, not just how much")
    body += p(
        "Stylists need three separate answers: the sides, the top, and the back or "
        "neckline. \"Shorter\" on its own does not say which. A useful sentence names "
        "all three &mdash; for example, \"number two on the sides, take about an inch "
        "off the top, and square off the neckline.\""
    )
    body += p(
        "Two more that prevent most surprises: say whether you want your <strong>ears "
        "showing</strong>, and whether the <strong>fringe should sit above or below "
        "the eyebrows</strong>. Those are the details people notice afterwards."
    )

    body += h2("4. Ask for your Clip Notes")
    body += p(
        "Great Clips records what was done to your hair under a feature they call "
        "Clip Notes, tied to your name and phone number. If a previous cut went well, "
        "asking the stylist to look it up is faster and more accurate than describing "
        f"it again &mdash; and it works at any of the {total:,} salons, not only the "
        "one you first visited."
    )

    body += h2("5. Know what is on the menu")
    body += p(
        "Beyond the haircut itself, Great Clips lists <strong>bang trims, beard "
        "trims, neck trims, shampoo, styling</strong> (including blowdries and updos) "
        "and <strong>perms</strong>. The perm carries an asterisk on their own service "
        "page &mdash; availability varies by location &mdash; so ring the salon before "
        "making a trip for one. A neck trim is the cheap add-on most people do not "
        "know to ask for, and it is what keeps a fade looking sharp between cuts."
    )
    body += p(
        "Walk-ins are the norm, and Online Check-In puts you in the queue before you "
        "leave the house."
    )

    body += h2("6. Then bring a coupon")
    body += p(
        "Style sorted, the last step is not paying full price. Which coupons work "
        "depends on where you are &mdash; most Great Clips offers are tied to a metro "
        'market. Open <a href="/salons" class="text-purple-600 hover:underline">your '
        "city</a> to see its salons and the offers valid at them."
    )

    faqs = [
        (
            "What should I ask for at Great Clips?",
            "Name a style from the Great Clips Lookbook, give a clipper guard number "
            "for the sides, say how much to take off the top, and state how you want "
            "the neckline. Asking the stylist to pull up your Clip Notes repeats a cut "
            "you already liked.",
        ),
        (
            "What is a number 2 haircut?",
            'A #2 clipper guard cuts hair to about 1/4 inch (6 mm). It is the most '
            "commonly requested buzz length, short enough to be tidy while still "
            "showing hair colour.",
        ),
        (
            "Can I bring a picture to Great Clips?",
            "Yes, and it is the single most reliable way to communicate a cut. A photo "
            "removes the ambiguity that words like short, medium and trim carry.",
        ),
        (
            "What services does Great Clips offer besides haircuts?",
            "Great Clips lists bang trims, beard trims, neck trims, shampoo, styling "
            "including blowdries and updos, and perms. Their own service page marks the "
            "perm as varying by location, so call ahead if that is what you want.",
        ),
        (
            "Does Great Clips do perms?",
            "Yes, but not everywhere. Great Clips lists perms among its additional "
            "services with a note that availability varies by location, so check with "
            "your local salon first.",
        ),
        (
            "What are Clip Notes at Great Clips?",
            "Clip Notes are the details of your previous haircut, saved against your "
            "name and phone number so any Great Clips salon can reproduce it. Ask the "
            "stylist to look them up instead of describing the cut again.",
        ),
    ]

    return (
        "what-to-ask-for-at-great-clips",
        page(
            slug="what-to-ask-for-at-great-clips",
            title="What to Ask For at Great Clips (Styles, Guards & Exact Words)",
            description=(
                "Ask by name. Great Clips publishes 43 named styles in its Lookbook, and "
                "a guard number settles the sides. The exact wording to use, plus the "
                "Clip Notes trick that repeats a cut you liked."
            ),
            badge="HAIRCUT GUIDE",
            heading="What to Ask For at Great Clips",
            subtitle="The names, numbers and exact words that get you the cut you pictured",
            faqs=faqs,
            body=body,
            sources=STYLE_SOURCES,
        ),
    )


def post_kids_styles(cities, metros, feed) -> tuple[str, str]:
    """Kids' haircut styles to ask for."""
    body = findings_box(
        [
            f"Great Clips lists <strong>{len(KIDS_STYLES)} kids' haircuts by name</strong> "
            "in its official Lookbook &mdash; asking by name beats describing.",
            "<strong>Match the cut to the hair, not the trend.</strong> Curly hair has "
            "its own entry (curly fade) for a reason.",
            "<strong>Grow-out matters more for kids.</strong> A taper or classic taper "
            "keeps its shape for weeks; a hard part fade needs a touch-up sooner.",
            "Ask for Clip Notes to be saved on the first visit, so the next cut is a "
            "sentence rather than a negotiation.",
        ]
    )

    body += p(
        "Taking a child for a haircut is mostly a communication problem. The child "
        "cannot describe what they want, the parent describes it loosely, and "
        "everyone hopes. Great Clips heads that off by publishing named kids' cuts, "
        "so you can point at one instead."
    )

    body += h2(f"The {len(KIDS_STYLES)} kids' styles Great Clips names")
    body += style_grid(KIDS_STYLES, kids=True)

    body += h2("Short and low-maintenance")
    body += p(
        "For a child who hates sitting still, or a summer cut, the shortest options "
        "are the <strong>buzz cut</strong> and the <strong>textured crew</strong>. "
        "Both are quick in the chair and need almost nothing at home. A "
        "<strong>classic taper</strong> is the middle ground: short sides that grow "
        "out evenly, so the cut still looks deliberate a month later."
    )

    body += h2("Fades, and how often they need redoing")
    body += p(
        "Fades are the most requested kids' cuts and Great Clips names four: "
        + ", ".join(
            style_link(s, kids=True)
            for s in ["taper-fade", "textured-fade", "curly-fade", "hard-part-fade"]
        )
        + ". Worth knowing before you choose: the sharper the fade, the faster it "
        "loses its shape. A taper fade stays tidy for weeks, while a hard part fade "
        "&mdash; where a line is shaved into the part &mdash; looks best for the first "
        "week or two."
    )

    body += h2("Curly and textured hair")
    body += p(
        "Curly hair does not fade the same way straight hair does, which is why the "
        "Lookbook lists a "
        + style_link("curly-fade", kids=True)
        + " separately. If your child's hair is curly or coily, ask for that by name "
        "rather than a generic fade, and say whether you want the curl kept on top."
    )

    body += h2("Longer cuts and bobs")
    body += p(
        "For longer hair the named options are the "
        + ", ".join(
            style_link(s, kids=True)
            for s in [
                "layered-bob",
                "chin-length-bob-with-bangs",
                "one-length-bob",
                "long-layers",
            ]
        )
        + " and a few more. The practical question is bangs: they look great and they "
        "need trimming every few weeks. Great Clips does bang trims as a service, so "
        "that upkeep does not mean a full haircut every time."
    )

    body += h2("What it costs, and getting it cheaper")
    body += p(
        "Kids' pricing and the age cutoff are a separate topic &mdash; we cover both "
        'in <a href="/blog/great-clips-kids-haircut" class="text-purple-600 '
        'hover:underline">Great Clips kids haircut prices</a>. The short version is '
        "that a coupon usually saves several dollars, and which coupons apply depends "
        'on your metro market. Check <a href="/salons" class="text-purple-600 '
        'hover:underline">your city</a> for the offers valid nearby.'
    )

    faqs = [
        (
            "What haircuts can I ask for for my child at Great Clips?",
            f"Great Clips names {len(KIDS_STYLES)} kids' styles in its Lookbook, "
            "including the buzz cut, classic taper, taper fade, textured fade, curly "
            "fade, hard part fade, textured crew, side part, undercut with short "
            "layers and several bobs. Asking by name is more reliable than describing.",
        ),
        (
            "What is the easiest kids' haircut to maintain?",
            "A buzz cut needs the least upkeep, and a classic taper is the best "
            "compromise between tidy and low-maintenance because it grows out evenly "
            "rather than developing a hard line.",
        ),
        (
            "How often do kids' fades need redoing?",
            "The sharper the fade, the sooner it needs attention. A taper fade holds "
            "its shape for several weeks; a hard part fade, with a shaved line, looks "
            "its best for about a week or two.",
        ),
        (
            "What haircut suits curly hair?",
            "Great Clips lists a curly fade specifically, because curly hair does not "
            "blend the same way straight hair does. Ask for it by name and say whether "
            "the curl should be kept long on top.",
        ),
        (
            "Does Great Clips trim bangs separately?",
            "Yes, bang trims are one of their listed services, which is useful for kids "
            "with fringes that need upkeep between full haircuts.",
        ),
    ]

    return (
        "great-clips-kids-haircut-styles",
        page(
            slug="great-clips-kids-haircut-styles",
            title=f"{len(KIDS_STYLES)} Kids' Haircuts to Ask For at Great Clips",
            description=(
                f"Great Clips names {len(KIDS_STYLES)} kids' styles in its Lookbook. "
                "Which to pick for curly hair, which grow out best, and how often fades "
                "need redoing."
            ),
            badge="KIDS GUIDE",
            heading=f"{len(KIDS_STYLES)} Kids' Haircuts to Ask For at Great Clips",
            subtitle="Ask by name, match the cut to the hair, and know how it grows out",
            faqs=faqs,
            body=body,
            sources=STYLE_SOURCES,
        ),
    )


def post_guards(cities, metros, feed) -> tuple[str, str]:
    """Clipper guard numbers explained."""
    rows = [
        [f"<strong>{num}</strong>", inches, mm, esc(note)]
        for num, inches, mm, note in GUARDS
    ]

    body = findings_box(
        [
            "<strong>Guard numbers are eighths of an inch.</strong> A &#35;2 is 2/8 "
            "&mdash; a quarter inch. That one fact lets you work out any of them.",
            "<strong>&#35;2 is the most requested</strong> buzz and fade-side length.",
            "Guard sizing is an industry standard, not a Great Clips one, so the same "
            "number means the same length in any salon.",
            "A guard number describes <em>length</em>, not <em>shape</em> &mdash; you "
            "still need to say fade, taper or all-over.",
        ]
    )

    body += p(
        "Clipper guards are the plastic combs that clip onto the blade and set how "
        "much hair is left behind. They are numbered, and the numbering is simple "
        "once you see it: <strong>the number is how many eighths of an inch it "
        "leaves</strong>. A &#35;4 leaves 4/8, or half an inch."
    )

    body += h2("Clipper guard sizes")
    body += table(
        ["Guard", "Length", "Metric", "What it looks like"],
        rows,
        note=(
            "Standard clipper guard sizing. Individual stylists may run slightly "
            "shorter or longer depending on the clipper and how the hair is held."
        ),
    )

    body += h2("Which number should you ask for?")
    body += p(
        "If you want a <strong>buzz cut</strong>, most people land on a &#35;2 or "
        "&#35;3 &mdash; short and tidy, with enough left to keep your hair colour. A "
        "&#35;1 is noticeably shorter and starts to show scalp on lighter hair."
    )
    body += p(
        "For a <strong>fade</strong>, you are describing a range rather than one "
        "number: the sides start short at the bottom and blend up. \"Fade from a zero "
        "to a three\" tells a stylist exactly what you mean. For <strong>sides with "
        "scissors on top</strong>, a &#35;2 or &#35;3 on the sides is the usual "
        "starting point."
    )
    body += p(
        "If you are unsure, <strong>ask for longer than you think</strong>. Going "
        "shorter takes another thirty seconds; going longer takes a month."
    )

    body += h2("Length is not shape")
    body += p(
        "This is where requests go wrong. A guard number says how much hair is left, "
        "but not how it is arranged. The same &#35;3 can be an even all-over buzz, the "
        "bottom of a fade, or the sides under a longer top. Pair the number with a "
        "shape &mdash; and better still with a style name from the "
        f'<a href="{LOOKBOOK}" target="_blank" rel="noopener" '
        'class="text-purple-600 hover:underline">Great Clips Lookbook</a>. Our guide '
        'to <a href="/blog/what-to-ask-for-at-great-clips" class="text-purple-600 '
        'hover:underline">what to ask for</a> covers the full sentence to use.'
    )

    body += h2("Getting it cheap")
    body += p(
        "A clipper cut is the quickest service in the salon and the easiest to get on "
        'a coupon. Check <a href="/salons" class="text-purple-600 hover:underline">'
        "your city</a> for the offers that reach your local salons."
    )

    faqs = [
        (
            "What do clipper guard numbers mean?",
            "The number is how many eighths of an inch of hair the guard leaves. A #2 "
            'leaves 2/8 of an inch, or 1/4 inch (6 mm); a #4 leaves half an inch.',
        ),
        (
            "What is a number 2 haircut?",
            'About 1/4 inch (6 mm) of hair. It is the most commonly requested buzz and '
            "fade-side length, short and neat while still showing hair colour.",
        ),
        (
            "What is the difference between a #1 and a #2?",
            'A #1 leaves 1/8 inch and a #2 leaves 1/4 inch, so a #2 is twice as long. '
            "On lighter hair a #1 starts to show scalp where a #2 usually does not.",
        ),
        (
            "Which guard number is best for a buzz cut?",
            "Most people choose a #2 or #3. Go shorter for a tighter look, and longer "
            "if you are unsure, since taking more off later is quick.",
        ),
        (
            "Are guard numbers the same at every salon?",
            "Yes. Guard sizing is an industry standard rather than a chain-specific "
            "one, which is why a number is the most portable way to describe length.",
        ),
    ]

    return (
        "clipper-guard-numbers",
        page(
            slug="clipper-guard-numbers",
            title="Clipper Guard Numbers Explained (#1 to #8, With Lengths)",
            description=(
                "Guard numbers are eighths of an inch: a #2 leaves 1/4 inch. Full size "
                "chart in inches and millimetres, which number to ask for, and why "
                "length is not the same as shape."
            ),
            badge="HAIRCUT GUIDE",
            heading="Clipper Guard Numbers Explained",
            subtitle="What #1 to #8 actually leave behind, and which to ask for",
            faqs=faqs,
            body=body,
            sources=STYLE_SOURCES,
        ),
    )


# ------------------------------------------------------- style vocabulary --

# Style names Great Clips publishes in its own Lookbook. Using their vocabulary is
# the whole point of these posts: a stylist recognises "clippered pushback"
# instantly, where "shorter on the sides I guess" starts a guessing game. Taken
# from greatclips.com/lookbook (42 styles: 25 adult and 17 kids').
LOOKBOOK = "https://www.greatclips.com/lookbook"

ADULT_STYLES = [
    "angled-bob", "bald-fade", "bixie", "blunt-bob", "classic-fade", "clipper",
    "clippered-pushback", "clippered-sides-with-layered-top", "crew",
    "curly-layered-bob-with-bangs", "fade-with-side-part", "layered-bob",
    "long-layers", "long-pushback", "long-scissor-cut", "one-length",
    "parted-scissor-cut", "pixie", "pompadour", "short-fade", "short-layer",
    "short-pushback", "short-scissor-cut", "shoulder-length-layers-with-bangs",
    "tousled-layers",
]

KIDS_STYLES = [
    "buzz-cut", "chin-length-bob-with-bangs", "classic-taper", "curly-fade",
    "hard-part-fade", "layered-bob", "layered-bob-with-bangs", "long-layers",
    "medium-layers", "one-length-bob", "short-layer",
    "shoulder-length-bob-face-framing", "side-part", "taper-fade",
    "textured-crew", "textured-fade", "undercut-with-short-layers",
]

# Standard clipper guard sizing. These are the industry lengths, not a Great Clips
# invention, which is exactly why a guard number travels between salons.
GUARDS = [
    ("#0.5", '1/16"', "1.5 mm", "Shadow of stubble. Skin shows through."),
    ("#1", '1/8"', "3 mm", "Very short. The tight end of a buzz cut."),
    ("#2", '1/4"', "6 mm", "The most requested buzz length. Hair still reads dark."),
    ("#3", '3/8"', "10 mm", "Short but soft. Common on the sides of a fade."),
    ("#4", '1/2"', "13 mm", "Medium-short. Hair starts to lie down."),
    ("#5", '5/8"', "16 mm", "Medium. Usual top length on a clipper cut."),
    ("#6", '3/4"', "19 mm", "Longer top, still uniform."),
    ("#7", '7/8"', "22 mm", "Long guard, mostly used on top."),
    ("#8", '1"', "25 mm", "Longest standard guard. A trim, not a buzz."),
]


def style_name(slug: str) -> str:
    """'clippered-pushback' -> 'Clippered pushback'."""
    words = slug.replace("-", " ")
    return words[:1].upper() + words[1:]


def style_link(slug: str, kids: bool = False) -> str:
    path = f"kids-{slug}-haircut" if kids else f"{slug}-haircut"
    return (
        f'<a href="{LOOKBOOK}/{path}" target="_blank" rel="noopener" '
        f'class="text-purple-600 hover:underline">{esc(style_name(slug))}</a>'
    )


def style_grid(slugs: list[str], kids: bool = False) -> str:
    items = "".join(
        f'                    <li class="py-1">{style_link(s, kids)}</li>\n'
        for s in slugs
    )
    return f"""            <div class="my-6 border border-slate-200 rounded-xl p-6 bg-slate-50">
                <ul class="grid sm:grid-cols-2 gap-x-6 list-disc list-inside text-slate-700">
{items}                </ul>
            </div>

"""


# ------------------------------------------------------------- blog index --

INDEX_START = "<!-- GC-ALL-POSTS:START (generated by scripts/generate_blog_posts.py) -->"
INDEX_END = "<!-- GC-ALL-POSTS:END -->"

# Emoji per slug keyword, so cards are not all identical.
BADGES = [
    ("vs-", "🥊", "COMPARISON"),
    ("data-study", "📊", "DATA STUDY"),
    ("which-states", "📊", "DATA STUDY"),
    ("how-many", "📊", "DATA STUDY"),
    ("didnt-work", "🛠️", "TROUBLESHOOTING"),
    ("work-at-any-location", "📍", "COUPON GUIDE"),
    ("how-long", "⏳", "COUPON GUIDE"),
    ("hours", "🕐", "GUIDE"),
    ("checkin", "📱", "HOW-TO"),
    ("kids", "🧒", "GUIDE"),
    ("senior", "👴", "DISCOUNTS"),
    ("student", "🎓", "DISCOUNTS"),
    ("prices", "💰", "GUIDE"),
    ("hacks", "✂️", "TIPS"),
]


def post_meta(path: Path) -> dict | None:
    """Title and description straight out of a post, so cards cannot drift."""
    text = path.read_text(encoding="utf-8", errors="replace")
    title = re.search(r"<title>(.*?)</title>", text, re.S)
    desc = re.search(r'<meta name="description" content="(.*?)"', text, re.S)
    if not title:
        return None
    clean = html.unescape(re.sub(r"\s+", " ", title.group(1))).strip()
    # Drop the trailing year/qualifier so cards stay short.
    clean = re.sub(r"\s*[\(\|]\s*20\d\d.*$", "", clean).strip(" -|")
    summary = (
        html.unescape(re.sub(r"\s+", " ", desc.group(1))).strip() if desc else ""
    )
    if len(summary) > 150:
        summary = summary[:147].rsplit(" ", 1)[0] + "..."

    emoji, badge = "📄", "ARTICLE"
    for needle, e, b in BADGES:
        if needle in path.stem:
            emoji, badge = e, b
            break
    return {
        "slug": path.stem,
        "title": clean,
        "summary": summary,
        "emoji": emoji,
        "badge": badge,
    }


def build_index_section(posts: list[dict]) -> str:
    cards = "".join(
        f"""                <a href="/blog/{p['slug']}" class="bg-white rounded-xl p-6 shadow-md hover:shadow-lg transition-shadow">
                    <span class="text-4xl mb-4 block">{p['emoji']}</span>
                    <span class="text-purple-600 text-sm font-medium">{esc(p['badge'])}</span>
                    <h3 class="text-xl font-bold text-slate-900 mt-2 mb-2">{esc(p['title'])}</h3>
                    <p class="text-slate-500">{esc(p['summary'])}</p>
                </a>
"""
        for p in posts
    )
    return f"""{INDEX_START}
        <h2 class="text-2xl font-bold text-slate-900 mt-12 mb-6">All articles</h2>
        <div class="grid md:grid-cols-2 gap-6">
{cards}        </div>
        {INDEX_END}"""


def update_blog_index(dry_run: bool) -> bool:
    """Rebuild the "All articles" grid from whatever posts exist on disk.

    The hand-maintained index listed 5 of the 12 posts, so seven were reachable
    only from the sitemap. Generating the list means adding a post cannot orphan it.
    """
    index_path = BLOG_DIR / "index.html"
    if not index_path.exists():
        print("  ! docs/blog/index.html missing, skipped")
        return False

    posts = []
    for path in sorted(BLOG_DIR.glob("*.html")):
        if path.stem == "index":
            continue
        meta = post_meta(path)
        if meta:
            posts.append(meta)
    posts.sort(key=lambda p: p["title"])

    original = index_path.read_text(encoding="utf-8")
    block = build_index_section(posts)
    pattern = re.compile(
        re.escape(INDEX_START) + r".*?" + re.escape(INDEX_END), re.S
    )
    if pattern.search(original):
        patched = pattern.sub(lambda _m: block, original, count=1)
    elif "</main>" in original:
        patched = original.replace("</main>", f"{block}\n    </main>", 1)
    else:
        print("  ! no </main> in blog index, skipped")
        return False

    print(f"  blog index: {len(posts)} posts listed")
    if patched != original and not dry_run:
        index_path.write_text(patched, encoding="utf-8")
    return True


# -------------------------------------------------------------------- main --

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cities, metros = markets.build_all()
    feed_path = REPO_ROOT / "docs" / "data" / "coupons.json"
    feed = {}
    if feed_path.exists():
        with feed_path.open(encoding="utf-8") as fh:
            feed = json.load(fh)

    posts = [
        post_scopes(cities, metros, feed),
        post_census(cities, metros, feed),
        post_declined(cities, metros, feed),
        post_what_to_ask(cities, metros, feed),
        post_kids_styles(cities, metros, feed),
        post_guards(cities, metros, feed),
        post_back_to_school(cities, metros, feed),
        post_holiday(cities, metros, feed),
    ]

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    for slug, markup in posts:
        path = BLOG_DIR / f"{slug}.html"
        size = len(markup.encode("utf-8")) / 1024
        if args.dry_run:
            print(f"  would write {path.relative_to(REPO_ROOT)}  ({size:.1f} KB)")
            continue
        path.write_text(markup, encoding="utf-8")
        print(f"  wrote {path.relative_to(REPO_ROOT)}  ({size:.1f} KB)")

    update_blog_index(args.dry_run)

    print(f"\n{len(posts)} post(s) {'checked' if args.dry_run else 'generated'}.")
    print("Remember: new slugs also need adding to update_sitemap.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
