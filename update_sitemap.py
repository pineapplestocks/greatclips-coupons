#!/usr/bin/env python3
"""
Update sitemap.xml with new monthly pages.
"""

import os
from datetime import datetime
from pathlib import Path

SITEMAP_PATH = "docs/sitemap.xml"
SITE_URL = "https://greatclipsdeal.com"

def update_sitemap():
    """Add new monthly pages to sitemap"""
    
    # Read generated URLs
    if not os.path.exists('generated_monthly_urls.txt'):
        print("No new URLs to add")
        return
    
    with open('generated_monthly_urls.txt') as f:
        new_urls = [line.strip() for line in f if line.strip()]
    
    if not new_urls:
        print("No new URLs to add")
        return
    
    # Read existing sitemap
    sitemap_path = Path(SITEMAP_PATH)
    if not sitemap_path.exists():
        # Try alternate location
        sitemap_path = Path("sitemap.xml")
    
    if not sitemap_path.exists():
        print(f"Sitemap not found at {SITEMAP_PATH} or sitemap.xml")
        return
    
    with open(sitemap_path) as f:
        sitemap_content = f.read()
    
    # Check which URLs are already in sitemap
    urls_to_add = []
    for url in new_urls:
        # Extract the path part for checking
        path = url.replace(SITE_URL, "").strip("/")
        if f"<loc>{url}</loc>" not in sitemap_content and f"<loc>{SITE_URL}/{path}</loc>" not in sitemap_content:
            urls_to_add.append(url)
    
    if not urls_to_add:
        print("All URLs already in sitemap")
        return
    
    # Generate new URL entries
    today = datetime.now().strftime("%Y-%m-%d")
    new_entries = ""
    for url in urls_to_add:
        new_entries += f'''  <url>
    <loc>{url}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
'''
    
    # Insert before closing </urlset>
    updated_sitemap = sitemap_content.replace("</urlset>", f"{new_entries}</urlset>")
    
    with open(sitemap_path, 'w') as f:
        f.write(updated_sitemap)
    
    print(f"✓ Added {len(urls_to_add)} new URLs to sitemap")
    for url in urls_to_add:
        print(f"  + {url}")

if __name__ == "__main__":
    update_sitemap()
