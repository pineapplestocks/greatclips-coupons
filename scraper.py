"""
Great Clips Coupon Scraper
Scrapes Facebook Ad Library for Great Clips coupons and extracts offer details.

Works both locally and in GitHub Actions.
"""

import re
import json
import time
import os
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Configuration
SEARCH_URL = "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&q=Great%20Clips%20coupon&search_type=keyword_unordered"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OUTPUT_DIR, "data")
JSON_FILE = os.path.join(DATA_DIR, "coupons.json")

# Settings
MAX_SCROLLS = 30  # Number of scrolls on Facebook Ad Library
IS_CI = os.environ.get('CI') == 'true'  # Running in GitHub Actions?


def scrape_facebook_ad_library():
    """Open Facebook Ad Library, scroll to load ads, extract offer URLs"""
    print("=" * 60)
    print("🏪 Great Clips Coupon Scraper")
    print("=" * 60)
    print()
    
    with sync_playwright() as p:
        print("🚀 Launching browser...")
        browser = p.chromium.launch(headless=True)
        
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        print(f"🌐 Navigating to Facebook Ad Library...")
        page.goto(SEARCH_URL, wait_until="networkidle", timeout=60000)
        
        print("⏳ Waiting for page to load...")
        time.sleep(5)
        
        # Handle cookie consent
        try:
            cookie_buttons = page.query_selector_all('button:has-text("Allow"), button:has-text("Accept")')
            for btn in cookie_buttons:
                btn.click()
                time.sleep(1)
        except:
            pass
        
        # Scroll to load results
        print(f"📜 Scrolling to load ads (max {MAX_SCROLLS} scrolls)...")
        
        last_height = 0
        scroll_count = 0
        no_change_count = 0
        
        while scroll_count < MAX_SCROLLS:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            scroll_count += 1
            time.sleep(1)
            
            new_height = page.evaluate("document.body.scrollHeight")
            
            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= 5:
                    print(f"   ✅ Reached end after {scroll_count} scrolls")
                    break
            else:
                no_change_count = 0
                
            last_height = new_height
            
            if scroll_count % 10 == 0:
                print(f"   📄 Scrolled {scroll_count} times...")
        
        html_content = page.content()
        browser.close()
    
    return html_content


def extract_offer_urls(html_content):
    """Extract all offers.greatclips.com URLs from the HTML"""
    print()
    print("🔍 Extracting offer URLs...")
    
    soup = BeautifulSoup(html_content, "html.parser")
    offer_pattern = r'https?://offers\.greatclips\.com/[A-Za-z0-9]+'
    
    offer_urls = set()
    
    # Search all links
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if "offers.greatclips.com" in href:
            matches = re.findall(offer_pattern, href)
            offer_urls.update(matches)
        
        if "l.php" in href or "lm.facebook.com" in href:
            import urllib.parse
            decoded = urllib.parse.unquote(href)
            matches = re.findall(offer_pattern, decoded)
            offer_urls.update(matches)
    
    # Search entire HTML
    all_text = str(soup)
    text_matches = re.findall(offer_pattern, all_text)
    offer_urls.update(text_matches)
    
    # Clean URLs
    cleaned_urls = set()
    for url in offer_urls:
        clean = url.split("?")[0].split("&")[0].split("#")[0]
        if clean.startswith("http"):
            cleaned_urls.add(clean)
    
    print(f"   ✅ Found {len(cleaned_urls)} unique offer URLs")
    return list(cleaned_urls)


def fetch_offer_details(offer_urls):
    """Visit each offer URL and extract details"""
    print()
    print("🔄 Fetching details from each coupon page...")
    print(f"   Processing {len(offer_urls)} coupons...")
    print()
    
    coupons = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        for i, url in enumerate(offer_urls, 1):
            code = url.split("/")[-1]
            coupon = {"url": url, "coupon_code": code}
            
            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
                time.sleep(1.5)
                
                page_text = page.inner_text("body")
                page_html = page.content()
                
                # Try to extract coupon image
                # Look for og:image meta tag first (most reliable)
                og_image = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', page_html, re.IGNORECASE)
                if not og_image:
                    og_image = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', page_html, re.IGNORECASE)
                
                if og_image:
                    coupon["image_url"] = og_image.group(1)
                else:
                    # Fallback: look for main coupon image
                    img_match = re.search(r'<img[^>]*src=["\']([^"\']*(?:coupon|offer|haircut)[^"\']*)["\']', page_html, re.IGNORECASE)
                    if img_match:
                        coupon["image_url"] = img_match.group(1)
                
                # Extract "Valid at Great Clips..." text
                valid_match = re.search(
                    r'(Valid at Great Clips\s+.+?Expires\s+\d{1,2}/\d{1,2}/\d{4})',
                    page_text,
                    re.IGNORECASE | re.DOTALL
                )
                
                if valid_match:
                    valid_text = re.sub(r'\s+', ' ', valid_match.group(1).strip())
                    coupon["valid_text"] = valid_text
                    
                    # Extract location details
                    full_match = re.search(
                        r'Valid (?:at Great Clips|only at)\s+(.+?)\s+at\s+(.+?)\s+in\s+(.+?)\s+([A-Z]{2})[\.\s]',
                        valid_text
                    )
                    
                    if full_match:
                        coupon["location_name"] = full_match.group(1).strip()
                        coupon["address"] = full_match.group(2).strip()
                        coupon["city"] = full_match.group(3).strip()
                        coupon["state"] = full_match.group(4).strip()
                    
                    exp_match = re.search(r'Expires\s+(\d{1,2}/\d{1,2}/\d{4})', valid_text)
                    if exp_match:
                        coupon["expiration"] = exp_match.group(1)
                    
                    print(f"  ✅ [{i}/{len(offer_urls)}] {code} - {coupon.get('location_name', 'Found')}")
                else:
                    # Check for US-wide coupon - must say "participating US" or "all US" or "any Great Clips"
                    # AND must NOT have a specific location in "Valid at Great Clips [Location]" format
                    us_wide_match = re.search(
                        r'(?:participating\s+US|all\s+US|any\s+(?:US\s+)?Great\s+Clips|all\s+Great\s+Clips\s+(?:locations?|salons?))',
                        page_text, 
                        re.IGNORECASE
                    )
                    has_specific_location = re.search(
                        r'Valid at Great Clips\s+[A-Z][a-zA-Z\s]+\s+at\s+\d',
                        page_text
                    )
                    
                    if us_wide_match and not has_specific_location:
                        coupon["location_name"] = ""
                        coupon["state"] = "US"
                        print(f"  ✅ [{i}/{len(offer_urls)}] {code} - US-Wide Coupon")
                    else:
                        # Try to get expiration at least
                        exp_match = re.search(r'Expires?\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})', page_text, re.IGNORECASE)
                        if exp_match:
                            coupon["expiration"] = exp_match.group(1)
                        
                        # If we found a price but no location, it's likely a US-wide coupon
                        # Mark as US since there's no specific location
                        if not coupon.get("location_name") and not coupon.get("address") and not coupon.get("city"):
                            coupon["state"] = "US"
                            print(f"  ✅ [{i}/{len(offer_urls)}] {code} - US-Wide (no location)")
                        else:
                            print(f"  ⚠️ [{i}/{len(offer_urls)}] {code} - Limited info")
                
                # Get price
                price_match = re.search(r'\$(\d+\.?\d{0,2})', page_text)
                if price_match:
                    coupon["price"] = "$" + price_match.group(1)
                
            except Exception as e:
                print(f"  ❌ [{i}/{len(offer_urls)}] {code} - Error: {str(e)[:40]}")
                coupon["error"] = str(e)
            
            coupons.append(coupon)
        
        browser.close()
    
    found_count = sum(1 for c in coupons if c.get("location_name") or c.get("valid_text"))
    print()
    print(f"   ✅ Got details for {found_count}/{len(coupons)} coupons")
    
    return coupons


def save_results(coupons):
    """Save results to JSON"""
    print()
    print("💾 Saving results...")
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Sort by price
    def get_price(c):
        try:
            return float(c.get('price', '$999').replace('$', ''))
        except:
            return 999
    
    coupons.sort(key=get_price)
    
    data = {
        "scraped_at": datetime.now().isoformat(),
        "total_coupons": len(coupons),
        "coupons": coupons
    }
    
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    print(f"   ✅ Saved to: {JSON_FILE}")
    
    # Stats
    with_location = sum(1 for c in coupons if c.get("location_name"))
    us_wide = sum(1 for c in coupons if c.get("state") == "US")
    prices = [get_price(c) for c in coupons if get_price(c) < 999]
    
    print()
    print("📊 Stats:")
    print(f"   Total coupons: {len(coupons)}")
    print(f"   With location: {with_location}")
    print(f"   US-wide: {us_wide}")
    if prices:
        print(f"   Price range: ${min(prices):.2f} - ${max(prices):.2f}")


def main():
    # Step 1: Scrape Facebook Ad Library
    html_content = scrape_facebook_ad_library()
    
    # Step 2: Extract offer URLs
    offer_urls = extract_offer_urls(html_content)
    
    if not offer_urls:
        print("❌ No offer URLs found!")
        return
    
    # Step 3: Fetch details from each offer page
    coupons = fetch_offer_details(offer_urls)
    
    # Step 4: Save results
    save_results(coupons)
    
    print()
    print("✅ Done!")


if __name__ == "__main__":
    main()
