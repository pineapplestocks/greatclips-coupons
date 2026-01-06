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
from datetime import datetime
from pathlib import Path

SITEMAP_PATH = "docs/sitemap.xml"
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
    
    # === ALL 60 CITIES ===
    cities = [
        # Original 10
        "phoenix", "dallas", "houston", "chicago", "atlanta",
        "columbus", "indianapolis", "minneapolis", "denver", "detroit",
        # New 50
        "los-angeles", "new-york-city", "san-antonio", "san-diego", "san-jose",
        "austin", "jacksonville", "fort-worth", "charlotte", "san-francisco",
        "seattle", "nashville", "oklahoma-city", "las-vegas", "portland",
        "milwaukee", "albuquerque", "tucson", "sacramento", "kansas-city",
        "mesa", "virginia-beach", "omaha", "colorado-springs", "raleigh",
        "miami", "tampa", "orlando", "cleveland", "pittsburgh",
        "cincinnati", "st-louis", "baltimore", "salt-lake-city", "richmond",
        "louisville", "memphis", "birmingham", "boise", "des-moines",
        "spokane", "fresno", "tulsa", "wichita", "arlington",
        "bakersfield", "aurora", "anaheim", "honolulu", "santa-ana",
    ]
    
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


def update_sitemap():
    """Generate complete sitemap (replaces old append-only approach)"""
    sitemap = generate_sitemap()
    
    # Write to file
    output_path = Path(SITEMAP_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(sitemap)
    
    # Count URLs
    url_count = sitemap.count('<url>')
    print(f"✅ Generated complete sitemap with {url_count} URLs → {SITEMAP_PATH}")


# Keep backward compatibility - both function names work
def main():
    update_sitemap()


if __name__ == "__main__":
    main()
