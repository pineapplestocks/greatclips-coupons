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
                <p class="font-semibold text-slate-900 mb-2">About this data</p>
                <p>Salon counts, addresses and hours come from the official Great Clips
                   salon locator and were last reviewed on {esc(REVIEWED_DATE)}. Coupon
                   figures come from our own tracking, refreshed every six hours. Counts
                   on this site are actual counts, not estimates &mdash; if a number here
                   disagrees with another site, ours is the one you can check against the
                   <a href="/salons" class="text-purple-600 hover:underline">salon directory</a>.</p>
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
