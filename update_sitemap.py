#!/usr/bin/env python3
"""
Generate complete sitemap.xml with ALL pages every time.
This replaces the old append-only approach to ensure nothing gets lost.

Includes:
- Homepage & core pages
- Coupon landing pages  
- Blog posts
- Monthly pages (current year + next year)
- All 50 state pages
- All 60 city pages

Run this after any content updates to keep sitemap current.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# The status lines below use emoji, which crash on a Windows console defaulting to
# cp1252. CI runs UTF-8, but this script is also run by hand on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SITEMAP_PATH = "docs/sitemap.xml"
DOCS_DIR = "docs"
SITE_URL = "https://greatclipsdeal.com"

def get_today():
    return datetime.now().strftime("%Y-%m-%d")

def generate_sitemap():
    today = get_today()
    current_year = datetime.now().year
    next_year = current_year + 1
    
    # Start sitemap
    sitemap = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
'''
    
    # === HOMEPAGE ===
    sitemap += f'''  <url>
    <loc>{SITE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
'''
    
    # === CORE PAGES ===
    core_pages = [
        ("states", "weekly", "0.9"),
        ("faq", "monthly", "0.8"),
        ("how-to-use", "monthly", "0.8"),
        ("how-we-verify-coupons", "weekly", "0.8"),
        ("prices", "monthly", "0.8"),
        ("calculator", "monthly", "0.7"),
        ("about", "monthly", "0.5"),
        ("contact", "monthly", "0.5"),
        ("privacy", "yearly", "0.3"),
        ("terms", "yearly", "0.3"),
    ]
    
    for page, freq, priority in core_pages:
        sitemap += f'''  <url>
    <loc>{SITE_URL}/{page}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>
'''
    
    # === COUPON LANDING PAGES ===
    coupon_pages = [
        ("5-99-coupon", "daily", "0.9"),
        ("6-99-coupon", "daily", "0.9"),
        ("printable-coupons", "daily", "0.8"),
        ("coupon-codes", "daily", "0.8"),
        ("senior-discount", "weekly", "0.8"),
    ]
    
    for page, freq, priority in coupon_pages:
        sitemap += f'''  <url>
    <loc>{SITE_URL}/{page}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>
'''
    
    # === BLOG ===
    blog_pages = [
        "blog",
        "blog/great-clips-prices-2026",
        "blog/great-clips-senior-discount",
        "blog/great-clips-vs-supercuts",
        "blog/coupon-hacks",
        "blog/great-clips-kids-haircut",
        "blog/great-clips-hours",
        "blog/great-clips-online-checkin",
        "blog/great-clips-vs-sport-clips",
        "blog/great-clips-student-discount",
        "blog/great-clips-coupon-prices-data-study",
        "blog/how-long-do-great-clips-coupons-last",
        "blog/which-states-get-the-most-great-clips-coupons",
        "blog/do-great-clips-coupons-work-at-any-location",
        "blog/how-many-great-clips-locations",
        "blog/why-your-great-clips-coupon-didnt-work",
        "blog/what-to-ask-for-at-great-clips",
        "blog/great-clips-kids-haircut-styles",
        "blog/clipper-guard-numbers",
        "blog/great-clips-back-to-school-haircuts",
        "blog/great-clips-holiday-haircuts",
        "author/kumar-chaudhari",
    ]
    
    for page in blog_pages:
        sitemap += f'''  <url>
    <loc>{SITE_URL}/{page}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>
'''
    
    # === MONTHLY PAGES ===
    months = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december"
    ]
    
    # Current year
    for month in months:
        sitemap += f'''  <url>
    <loc>{SITE_URL}/{month}-{current_year}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
'''
    
    # Next year
    for month in months:
        sitemap += f'''  <url>
    <loc>{SITE_URL}/{month}-{next_year}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
'''
    
    # === ALL 50 STATES ===
    states = [
        ("alabama", "0.8"),
        ("alaska", "0.8"),
        ("arizona", "0.8"),
        ("arkansas", "0.8"),
        ("california", "0.9"),
        ("colorado", "0.8"),
        ("connecticut", "0.8"),
        ("delaware", "0.8"),
        ("florida", "0.9"),
        ("georgia", "0.8"),
        ("hawaii", "0.8"),
        ("idaho", "0.8"),
        ("illinois", "0.8"),
        ("indiana", "0.8"),
        ("iowa", "0.8"),
        ("kansas", "0.8"),
        ("kentucky", "0.8"),
        ("louisiana", "0.8"),
        ("maine", "0.8"),
        ("maryland", "0.8"),
        ("massachusetts", "0.8"),
        ("michigan", "0.8"),
        ("minnesota", "0.8"),
        ("mississippi", "0.8"),
        ("missouri", "0.8"),
        ("montana", "0.8"),
        ("nebraska", "0.8"),
        ("nevada", "0.8"),
        ("new-hampshire", "0.8"),
        ("new-jersey", "0.8"),
        ("new-mexico", "0.8"),
        ("new-york", "0.9"),
        ("north-carolina", "0.8"),
        ("north-dakota", "0.8"),
        ("ohio", "0.8"),
        ("oklahoma", "0.8"),
        ("oregon", "0.8"),
        ("pennsylvania", "0.8"),
        ("rhode-island", "0.8"),
        ("south-carolina", "0.8"),
        ("south-dakota", "0.8"),
        ("tennessee", "0.8"),
        ("texas", "0.9"),
        ("utah", "0.8"),
        ("vermont", "0.8"),
        ("virginia", "0.8"),
        ("washington", "0.8"),
        ("west-virginia", "0.8"),
        ("wisconsin", "0.8"),
        ("wyoming", "0.8"),
    ]
    
    for state, priority in states:
        sitemap += f'''  <url>
    <loc>{SITE_URL}/{state}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>{priority}</priority>
  </url>
'''
    
    # === CITY PAGES ===
    # Scanned rather than hardcoded: the hand-maintained list had drifted to 60 of
    # the 68 pages that exist, leaving Akron, Boston, Dayton, El Paso, Jersey City,
    # Newark, Philadelphia and Toledo out of the sitemap entirely.
    cities_dir = Path(DOCS_DIR) / "cities"
    cities = sorted(p.stem for p in cities_dir.glob("*.html") if p.stem != "index")

    for city in cities:
        sitemap += f'''  <url>
    <loc>{SITE_URL}/cities/{city}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.7</priority>
  </url>
'''
    
    # Close sitemap
    sitemap += '</urlset>\n'
    
    return sitemap


def generate_salons_sitemap():
    """Sitemap for the per-city salon pages under docs/salons/.

    Built by scanning the generated files rather than from a hardcoded list, so it
    can never drift from what was actually published. These pages change only when
    the salon data changes, so they live in their own sitemap and keep the daily
    coupon refresh from rewriting thousands of <lastmod> values.
    """
    salons_dir = Path(DOCS_DIR) / "salons"
    if not salons_dir.exists():
        return None, 0

    entries = []
    index_file = salons_dir / "index.html"
    if index_file.exists():
        entries.append((f"{SITE_URL}/salons", _file_date(index_file), "weekly", "0.8"))

    for path in sorted(salons_dir.glob("*/*.html")):
        state = path.parent.name
        slug = path.stem
        entries.append(
            (f"{SITE_URL}/salons/{state}/{slug}", _file_date(path), "weekly", "0.7")
        )

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod, freq, priority in entries:
        xml.append(
            f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n  </url>"
        )
    xml.append("</urlset>\n")
    return "\n".join(xml), len(entries)


def _file_date(path):
    """Last-modified date of a generated file, as YYYY-MM-DD."""
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")


def generate_sitemap_index(children):
    today = get_today()
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for name in children:
        xml.append(
            f"  <sitemap>\n    <loc>{SITE_URL}/{name}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n  </sitemap>"
        )
    xml.append("</sitemapindex>\n")
    return "\n".join(xml)


def _write(relative_path, text):
    path = Path(DOCS_DIR) / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def update_sitemap():
    """Write sitemap-main.xml, sitemap-salons.xml and the sitemap.xml index.

    sitemap.xml stays the single URL registered in Search Console and robots.txt;
    it is now an index pointing at the two child sitemaps.
    """
    main_xml = generate_sitemap()
    _write("sitemap-main.xml", main_xml)
    main_count = main_xml.count("<url>")
    print(f"✅ sitemap-main.xml: {main_count} URLs")

    children = ["sitemap-main.xml"]
    salons_xml, salons_count = generate_salons_sitemap()
    if salons_xml:
        _write("sitemap-salons.xml", salons_xml)
        children.append("sitemap-salons.xml")
        print(f"✅ sitemap-salons.xml: {salons_count} URLs")
    else:
        print("ℹ️  docs/salons/ not built yet - skipping salon sitemap")

    _write("sitemap.xml", generate_sitemap_index(children))
    total = main_count + salons_count
    print(f"✅ sitemap.xml index -> {', '.join(children)}  ({total} URLs total)")


# Keep backward compatibility - both function names work
def main():
    update_sitemap()


if __name__ == "__main__":
    main()
