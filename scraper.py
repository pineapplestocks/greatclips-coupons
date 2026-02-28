"""
Great Clips Coupon Scraper
Scrapes Facebook Ad Library for Great Clips coupons and extracts offer details.

Works both locally and in GitHub Actions.
"""

import re
import json
import time
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
try:
    import requests
except ImportError:
    requests = None

# Configuration
SEARCH_URL = "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&q=Great%20Clips%20coupon&search_type=keyword_unordered"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(OUTPUT_DIR, "data")
JSON_FILE = os.path.join(DATA_DIR, "coupons.json")

# Load .env file for local development (no extra dependencies needed)
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# Settings
MAX_SCROLLS = 30  # Number of scrolls on Facebook Ad Library
IS_CI = os.environ.get('CI') == 'true'  # Running in GitHub Actions?
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')  # Free at console.groq.com


def load_existing_coupons():
    """Load existing coupons from JSON file"""
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                coupons = data.get('coupons', [])
                print(f"   📂 Loaded {len(coupons)} existing coupons from file")
                return coupons
        except Exception as e:
            print(f"   ⚠️ Could not load existing coupons: {e}")
            return []
    print(f"   📂 No existing coupons file found")
    return []


def is_expired(coupon):
    """Check if a coupon has expired"""
    exp_str = coupon.get('expiration', '')
    if not exp_str or exp_str == 'N/A':
        # If no expiration, check if it was added more than 30 days ago
        # BUT never expire manually added coupons without expiration
        if coupon.get('manual_add'):
            return False
        added_date = coupon.get('added_date', '')
        if added_date:
            try:
                added = datetime.strptime(added_date, '%Y-%m-%d')
                if datetime.now() - added > timedelta(days=30):
                    return True
            except:
                pass
        return False
    
    try:
        # Parse expiration date (format: MM/DD/YYYY)
        exp_date = datetime.strptime(exp_str, '%m/%d/%Y')
        return datetime.now() > exp_date
    except:
        return False


def get_coupon_key(coupon):
    """Generate a unique key for a coupon based on URL or location + price"""
    # Use URL as primary key since it's unique per offer
    url = coupon.get('url', '')
    if url:
        # Extract the offer ID from URL (e.g., https://offers.greatclips.com/9hKYiQx -> 9hKYiQx)
        match = re.search(r'offers\.greatclips\.com/([^/?]+)', url)
        if match:
            return f"offer_{match.group(1)}"
    
    # Fallback: use location + address + price as key
    location = (coupon.get('location_name', '') or '').strip().lower()
    address = (coupon.get('address', '') or '').strip().lower()
    city = (coupon.get('city', '') or '').strip().lower()
    state = (coupon.get('state', '') or '').strip().upper()
    price = (coupon.get('price', '') or '').strip()
    
    if location and address:
        return f"loc_{location}_{address}_{price}"
    elif location and city:
        return f"loc_{location}_{city}_{state}_{price}"
    elif location:
        return f"loc_{location}_{state}_{price}"
    
    # Last resort: use URL hash
    return f"url_{hash(url)}"


def merge_coupons(existing_coupons, new_coupons):
    """Merge new coupons with existing ones, avoiding duplicates and removing expired"""
    # Create a dict of existing coupons by key
    coupon_dict = {}
    today = datetime.now().strftime('%Y-%m-%d')
    
    expired_count = 0
    kept_count = 0
    manual_count = 0
    
    # FIRST: Add existing coupons (that aren't expired)
    for coupon in existing_coupons:
        is_manual = coupon.get('manual_add', False)
        
        if is_expired(coupon):
            if is_manual:
                print(f"   ⚠️ Manual coupon expired: {coupon.get('location_name', 'Unknown')} - {coupon.get('price', 'N/A')}")
            expired_count += 1
            continue
        
        key = get_coupon_key(coupon)
        coupon_dict[key] = coupon
        kept_count += 1
        
        if is_manual:
            manual_count += 1
            print(f"   🔒 Preserved manual coupon: {coupon.get('location_name', 'Unknown')} - {coupon.get('price', 'N/A')}")
    
    print(f"   📦 Kept {kept_count} existing coupons ({manual_count} manual, {expired_count} expired and removed)")
    
    # SECOND: Add/update with new coupons
    new_count = 0
    updated_count = 0
    
    for coupon in new_coupons:
        key = get_coupon_key(coupon)
        
        if key not in coupon_dict:
            # New coupon - add it with today's date
            coupon['added_date'] = today
            coupon['last_seen'] = today
            coupon_dict[key] = coupon
            new_count += 1
            print(f"   ➕ New: {coupon.get('location_name', 'Unknown')[:30]} - {coupon.get('price', 'N/A')}")
        else:
            # Existing coupon - update last_seen, optionally update expiration
            existing = coupon_dict[key]
            
            # Only update expiration if new one is valid and existing isn't manual
            if coupon.get('expiration') and coupon.get('expiration') != 'N/A':
                # Don't overwrite manual coupon's expiration unless it's empty
                if not existing.get('manual_add') or not existing.get('expiration'):
                    existing['expiration'] = coupon.get('expiration')
            
            existing['last_seen'] = today
            updated_count += 1
    
    print(f"   ➕ Added {new_count} new coupons")
    print(f"   🔄 Updated {updated_count} existing coupons")
    
    return list(coupon_dict.values())


def classify_coupon_with_llm(page_text):
    """
    Use Groq's free LLM API to classify a coupon's validity text.
    Returns a dict with keys: type, area_name, location_name, city, state, expiration
    type is one of: 'US', 'AREA', 'LOCATION', 'UNKNOWN'
    Falls back to None on any error.
    """
    if not GROQ_API_KEY or not requests:
        return None

    # Only send the most relevant snippet to keep token usage minimal
    # Look for the validity sentence
    snippet_match = re.search(
        r'(Valid[\s\S]{0,400}?(?:salons?|locations?|Expires[^\n]*|\d{1,2}/\d{1,2}/\d{4}))',
        page_text, re.IGNORECASE
    )
    snippet = snippet_match.group(1).strip() if snippet_match else page_text[:500]

    prompt = (
        'Classify this Great Clips coupon validity text. '
        'Return ONLY a JSON object with these exact fields:\n'
        '- "type": "US" (valid anywhere in the US), "AREA" (valid only in a specific city/region), '
        'or "LOCATION" (valid at one specific salon address)\n'
        '- "area_name": the region description if AREA (e.g. "OKC area and N. Central & W OK area"), else null\n'
        '- "location_name": the salon name if LOCATION, else null\n'
        '- "city": the city if LOCATION, else null\n'
        '- "state": 2-letter state code if LOCATION, else null\n'
        '- "expiration": date as MM/DD/YYYY if found, else null\n\n'
        f'Coupon text: "{snippet}"\n\n'
        'JSON only, no explanation.'
    )

    try:
        resp = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {GROQ_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'llama-3.1-8b-instant',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0,
                'max_tokens': 200,
                'response_format': {'type': 'json_object'},
            },
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']
        return json.loads(content)
    except Exception as e:
        print(f'   ⚠️  Groq LLM error: {e}')
        return None


def _apply_llm_classification(coupon, llm, code, idx, total):
    """Apply the result of classify_coupon_with_llm() to a coupon dict."""
    if not llm:
        coupon["state"] = "UNKNOWN"
        print(f"  ⚠️  [{idx}/{total}] {code} - Unclassified (LLM unavailable)")
        return

    ctype = (llm.get("type") or "UNKNOWN").upper()

    if ctype == "US":
        coupon["location_name"] = ""
        coupon["state"] = "US"
        print(f"  ✅ [{idx}/{total}] {code} - US-Wide (LLM)")

    elif ctype == "AREA":
        area_name = llm.get("area_name") or "Unknown Area"
        coupon["location_name"] = area_name if "area" in area_name.lower() else f"{area_name} Area"
        coupon["state"] = "AREA"
        coupon["area_name"] = area_name
        if llm.get("expiration"):
            coupon["expiration"] = llm["expiration"]
        print(f"  ✅ [{idx}/{total}] {code} - {area_name} (LLM)")

    elif ctype == "LOCATION":
        if llm.get("location_name"):
            coupon["location_name"] = llm["location_name"]
        if llm.get("city"):
            coupon["city"] = llm["city"]
        if llm.get("state"):
            coupon["state"] = llm["state"]
        if llm.get("expiration"):
            coupon["expiration"] = llm["expiration"]
        print(f"  ✅ [{idx}/{total}] {code} - {llm.get('location_name', 'Location')} (LLM)")

    else:
        coupon["state"] = "UNKNOWN"
        print(f"  ⚠️  [{idx}/{total}] {code} - Unclassified by LLM")


# Phrases that indicate an offer page is no longer valid
_ENDED_PHRASES = [
    "this offer has ended",
    "we're sorry! this offer has ended",
    "offer has expired",
    "this offer is no longer available",
]


def purge_ended_offers(coupons):
    """
    Visit every coupon URL and:
    - Remove any whose page shows an 'offer ended' message
    - Re-classify any state='US' coupons missing valid_text (old fallback mis-tags)
    Manual coupons (manual_add=True) are skipped.
    Returns the cleaned list.
    """
    to_purge_check = [c for c in coupons if c.get('url') and not c.get('manual_add')]
    to_reclassify  = [c for c in to_purge_check if c.get('state') == 'US' and not c.get('valid_text')]

    if not to_purge_check:
        return coupons

    print()
    print(f"🔍 Verifying {len(to_purge_check)} offer URLs ({len(to_reclassify)} US coupons to re-classify)...")

    ended_urls = set()
    reclassify_updates = {}  # url -> updated fields

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = ctx.new_page()

        for i, coupon in enumerate(to_purge_check, 1):
            url = coupon['url']
            code = coupon.get('coupon_code', url.split('/')[-1])
            needs_reclassify = url in {c['url'] for c in to_reclassify}

            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
                time.sleep(0.5)
                page_text = page.inner_text("body")

                # Check for ended offers
                if any(phrase in page_text.lower() for phrase in _ENDED_PHRASES):
                    ended_urls.add(url)
                    print(f"  🗑️  [{i}/{len(to_purge_check)}] {code} - Offer ended, removing")
                    continue

                # Re-classify US coupons that were tagged by the old fallback
                if needs_reclassify:
                    llm = classify_coupon_with_llm(page_text)
                    if llm:
                        ctype = (llm.get('type') or 'UNKNOWN').upper()
                        update = {}
                        # Capture valid_text if found
                        vm = re.search(
                            r'(Valid[\s\S]{0,400}?(?:Expires\s+\d{1,2}/\d{1,2}/\d{4}|salons?\.))',
                            page_text, re.IGNORECASE
                        )
                        if vm:
                            update['valid_text'] = re.sub(r'\s+', ' ', vm.group(1).strip())

                        if ctype == 'US':
                            update['location_name'] = ''
                            update['state'] = 'US'
                            print(f"  ✅ [{i}/{len(to_purge_check)}] {code} - Confirmed US-wide (LLM)")
                        elif ctype == 'AREA':
                            area_name = llm.get('area_name') or 'Unknown Area'
                            update['location_name'] = area_name if 'area' in area_name.lower() else f"{area_name} Area"
                            update['state'] = 'AREA'
                            update['area_name'] = area_name
                            if llm.get('expiration'):
                                update['expiration'] = llm['expiration']
                            print(f"  🗺️  [{i}/{len(to_purge_check)}] {code} - Re-classified → AREA: {area_name}")
                        elif ctype == 'LOCATION':
                            if llm.get('location_name'):
                                update['location_name'] = llm['location_name']
                            if llm.get('city'):
                                update['city'] = llm['city']
                            if llm.get('state'):
                                update['state'] = llm['state']
                            if llm.get('expiration'):
                                update['expiration'] = llm['expiration']
                            print(f"  📍 [{i}/{len(to_purge_check)}] {code} - Re-classified → LOCATION: {llm.get('location_name')}")
                        else:
                            update['state'] = 'UNKNOWN'
                            print(f"  ⚠️  [{i}/{len(to_purge_check)}] {code} - Unclassified by LLM")

                        reclassify_updates[url] = update
                    else:
                        print(f"  ⚠️  [{i}/{len(to_purge_check)}] {code} - LLM unavailable, leaving as-is")

            except Exception as e:
                print(f"  ⚠️  [{i}/{len(to_purge_check)}] {code} - Unreachable: {str(e)[:40]}")

        browser.close()

    # Apply all changes
    cleaned = []
    for c in coupons:
        url = c.get('url', '')
        if url in ended_urls:
            continue
        if url in reclassify_updates:
            c.update(reclassify_updates[url])
        cleaned.append(c)

    removed = len(coupons) - len(cleaned)
    if removed:
        print(f"   🗑️  Removed {removed} ended offer(s)")
    if reclassify_updates:
        print(f"   🔄 Re-classified {len(reclassify_updates)} previously mis-tagged coupon(s)")
    if not removed and not reclassify_updates:
        print(f"   ✅ All offers verified")
    return cleaned


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

                # Skip offers that have already ended
                if "this offer has ended" in page_text.lower():
                    print(f"  🗑️  [{i}/{len(offer_urls)}] {code} - Offer ended, skipping")
                    continue

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
                    # ── Fast-path regex checks ──────────────────────────────────
                    # 1. Explicit US-wide language ("participating US salons", etc.)
                    us_wide_match = re.search(
                        r'(?:participating\s+US|all\s+US|any\s+(?:US\s+)?Great\s+Clips|'
                        r'all\s+Great\s+Clips\s+(?:locations?|salons?)|'
                        r'all\s+participating\s+(?:US\s+)?Great\s+Clips)',
                        page_text,
                        re.IGNORECASE
                    )
                    # 2. Any "area" language → definitely NOT US-wide
                    any_area_hint = re.search(
                        r'\b(?:area|region|metro)\b.{0,60}(?:Great\s+Clips|salons?|locations?)',
                        page_text, re.IGNORECASE
                    )
                    # 3. Narrow area regex (original, kept for speed)
                    area_match = re.search(
                        r'(?:participating|only at)\s+([A-Za-z\s]+?)\s+area\s+Great\s+Clips',
                        page_text, re.IGNORECASE
                    )
                    # 4. Broader area fallback
                    area_fallback = re.search(
                        r'([A-Za-z][\w\s,\.&-]{2,60}?)\s+area\s+(?:Great\s+Clips\s+)?salons?',
                        page_text, re.IGNORECASE
                    )

                    # Always try to grab expiration
                    exp_match = re.search(r'Expires?\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})', page_text, re.IGNORECASE)
                    if exp_match:
                        coupon["expiration"] = exp_match.group(1)

                    if us_wide_match and not any_area_hint:
                        # Clear US-wide signal and no area hints → safe to mark US
                        coupon["location_name"] = ""
                        coupon["state"] = "US"
                        print(f"  ✅ [{i}/{len(offer_urls)}] {code} - US-Wide Coupon")

                    elif area_match:
                        area_name = area_match.group(1).strip()
                        coupon["location_name"] = f"{area_name} Area"
                        coupon["state"] = "AREA"
                        coupon["area_name"] = area_name
                        print(f"  ✅ [{i}/{len(offer_urls)}] {code} - {area_name} Area Coupon")

                    elif area_fallback:
                        area_name = area_fallback.group(1).strip()
                        bad = {'the', 'your', 'local', 'nearby', 'this', 'a', 'an', 'any'}
                        if area_name.lower() not in bad:
                            coupon["location_name"] = f"{area_name} Area"
                            coupon["state"] = "AREA"
                            coupon["area_name"] = area_name
                            print(f"  ✅ [{i}/{len(offer_urls)}] {code} - {area_name} Area Coupon")
                        else:
                            # Ambiguous — ask the LLM
                            llm = classify_coupon_with_llm(page_text)
                            _apply_llm_classification(coupon, llm, code, i, len(offer_urls))

                    else:
                        # ── Ambiguous: no clear signal either way ──────────────
                        # Try LLM first; fall back conservatively to AREA/unknown
                        llm = classify_coupon_with_llm(page_text)
                        if llm:
                            _apply_llm_classification(coupon, llm, code, i, len(offer_urls))
                        elif not coupon.get("location_name") and not coupon.get("address") and not coupon.get("city"):
                            # No LLM key configured and nothing parsed — leave unclassified
                            # rather than wrongly promoting to US-wide featured section
                            coupon["state"] = "UNKNOWN"
                            print(f"  ⚠️  [{i}/{len(offer_urls)}] {code} - Unclassified (no LLM key)")
                        else:
                            print(f"  ⚠️  [{i}/{len(offer_urls)}] {code} - Limited info")
                
                # Get price
                price_match = re.search(r'\$(\d+\.?\d{0,2})', page_text)
                if price_match:
                    coupon["price"] = "$" + price_match.group(1)
                
            except Exception as e:
                print(f"  ❌ [{i}/{len(offer_urls)}] {code} - Error: {str(e)[:40]}")
                # Skip coupons with errors - they have no useful data
                continue
            
            # Only save coupons that have useful data (price or location)
            if coupon.get("price") or coupon.get("location_name") or coupon.get("state"):
                coupons.append(coupon)
        
        browser.close()
    
    found_count = sum(1 for c in coupons if c.get("location_name") or c.get("valid_text"))
    print()
    print(f"   ✅ Got details for {found_count}/{len(coupons)} coupons")
    
    return coupons


def save_results(new_coupons):
    """Merge new coupons with existing ones and save to JSON"""
    print()
    print("💾 Saving results...")
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Load existing coupons
    existing_coupons = load_existing_coupons()
    
    # Merge new coupons with existing (removes expired, avoids duplicates)
    coupons = merge_coupons(existing_coupons, new_coupons)

    # Remove any coupons whose offer page now shows "This offer has ended"
    coupons = purge_ended_offers(coupons)

    # Sort by price (but keep manual/US-wide coupons at the end for visibility)
    def get_sort_key(c):
        try:
            price = float(c.get('price', '$999').replace('$', '').replace(' OFF', ''))
        except:
            price = 999
        # Manual coupons and US-wide sort to the end
        is_special = 1 if (c.get('manual_add') or c.get('state') == 'US') else 0
        return (is_special, price)
    
    coupons.sort(key=get_sort_key)
    
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
    manual = sum(1 for c in coupons if c.get("manual_add"))
    prices = []
    for c in coupons:
        try:
            p = float(c.get('price', '$999').replace('$', '').replace(' OFF', ''))
            if p < 999:
                prices.append(p)
        except:
            pass
    
    print()
    print("📊 Final Stats:")
    print(f"   Total coupons: {len(coupons)}")
    print(f"   With location: {with_location}")
    print(f"   US-wide: {us_wide}")
    print(f"   Manual/protected: {manual}")
    if prices:
        print(f"   Price range: ${min(prices):.2f} - ${max(prices):.2f}")


def main():
    # Step 1: Scrape Facebook Ad Library
    html_content = scrape_facebook_ad_library()
    
    # Step 2: Extract offer URLs
    offer_urls = extract_offer_urls(html_content)
    
    if not offer_urls:
        print("⚠️ No new offer URLs found in Facebook Ad Library")
        print("   Will keep existing coupons that haven't expired...")
        # Still run save_results with empty list to clean up expired coupons
        save_results([])
    else:
        # Step 3: Fetch details from each offer page
        coupons = fetch_offer_details(offer_urls)
        
        # Step 4: Save results (merges with existing)
        save_results(coupons)
    
    print()
    print("✅ Done!")


if __name__ == "__main__":
    main()
