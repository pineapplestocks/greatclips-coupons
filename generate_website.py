"""
Generate the coupon website from scraped data.
Embeds coupon data directly into the HTML file.
"""

import json
import os
import re

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "data", "coupons.json")
TEMPLATE_FILE = os.path.join(SCRIPT_DIR, "template.html")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "docs")  # GitHub Pages uses /docs
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")


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
    
    # Add last updated timestamp
    updated_at = data.get('scraped_at', 'Unknown')
    html = html.replace('{{LAST_UPDATED}}', updated_at[:10] if updated_at else 'Unknown')
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"   ✅ Created: {OUTPUT_FILE}")
    
    # Update sitemap with current date
    sitemap_file = os.path.join(OUTPUT_DIR, "sitemap.xml")
    if os.path.exists(sitemap_file):
        from datetime import datetime
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
