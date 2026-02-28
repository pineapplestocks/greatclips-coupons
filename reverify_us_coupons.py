#!/usr/bin/env python3
"""
One-time (and ongoing) script to re-verify coupons tagged state='US' but missing
valid_text. Visits each URL, detects ended offers, and re-classifies via LLM.
"""
import os, json, re, time
from playwright.sync_api import sync_playwright

# Load .env
_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env):
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

try:
    import requests
except ImportError:
    requests = None

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'coupons.json')

ENDED_PHRASES = [
    "this offer has ended",
    "we're sorry! this offer has ended",
    "offer has expired",
    "this offer is no longer available",
]


def classify_with_llm(page_text):
    if not GROQ_API_KEY or not requests:
        return None
    snippet_match = re.search(
        r'(Valid[\s\S]{0,400}?(?:salons?|locations?|Expires[^\n]*|\d{1,2}/\d{1,2}/\d{4}))',
        page_text, re.IGNORECASE
    )
    snippet = snippet_match.group(1).strip() if snippet_match else page_text[:500]
    prompt = (
        'Classify this Great Clips coupon validity text. Return ONLY a JSON object with: '
        '"type" ("US", "AREA", or "LOCATION"), "area_name" (if AREA, else null), '
        '"location_name" (if LOCATION, else null), "city" (if LOCATION, else null), '
        '"state" (2-letter code if LOCATION, else null), "expiration" (MM/DD/YYYY if found, else null).\n\n'
        f'Coupon text: "{snippet}"\n\nJSON only, no explanation.'
    )
    try:
        resp = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
            json={
                'model': 'llama-3.1-8b-instant',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0, 'max_tokens': 200,
                'response_format': {'type': 'json_object'},
            },
            timeout=15
        )
        resp.raise_for_status()
        return json.loads(resp.json()['choices'][0]['message']['content'])
    except Exception as e:
        print(f'    ⚠️  LLM error: {e}')
        return None


def main():
    with open(JSON_FILE, encoding='utf-8') as f:
        data = json.load(f)

    coupons = data['coupons']

    # Only re-check US coupons missing valid_text (not manual)
    to_check = [c for c in coupons if c.get('state') == 'US' and not c.get('valid_text') and not c.get('manual_add')]
    print(f"🔍 Re-verifying {len(to_check)} US coupons with no valid_text...\n")

    if not to_check:
        print("Nothing to re-verify.")
        return

    ended_urls = set()
    updates = {}  # url -> updated fields

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = ctx.new_page()

        for i, coupon in enumerate(to_check, 1):
            url = coupon['url']
            code = coupon.get('coupon_code', url.split('/')[-1])
            print(f"[{i}/{len(to_check)}] {code} ({coupon.get('price', '?')})")

            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
                time.sleep(1)
                page_text = page.inner_text("body")

                # Check if ended
                if any(p in page_text.lower() for p in ENDED_PHRASES):
                    print(f"    🗑️  Offer ended — removing")
                    ended_urls.add(url)
                    continue

                # Try to grab valid_text
                valid_match = re.search(
                    r'(Valid[\s\S]{0,400}?(?:Expires\s+\d{1,2}/\d{1,2}/\d{4}|salons?\.))',
                    page_text, re.IGNORECASE
                )
                valid_text = re.sub(r'\s+', ' ', valid_match.group(1).strip()) if valid_match else ''

                # Use LLM to classify
                llm = classify_with_llm(page_text)
                if not llm:
                    print(f"    ⚠️  LLM unavailable — leaving as-is")
                    continue

                ctype = (llm.get('type') or 'UNKNOWN').upper()
                update = {}

                if valid_text:
                    update['valid_text'] = valid_text

                if ctype == 'US':
                    update['location_name'] = ''
                    update['state'] = 'US'
                    print(f"    ✅ Confirmed US-wide")
                elif ctype == 'AREA':
                    area_name = llm.get('area_name') or 'Unknown Area'
                    update['location_name'] = area_name if 'area' in area_name.lower() else f"{area_name} Area"
                    update['state'] = 'AREA'
                    update['area_name'] = area_name
                    if llm.get('expiration'):
                        update['expiration'] = llm['expiration']
                    print(f"    🗺️  Re-classified → AREA: {area_name}")
                elif ctype == 'LOCATION':
                    if llm.get('location_name'):
                        update['location_name'] = llm['location_name']
                    if llm.get('city'):
                        update['city'] = llm['city']
                    if llm.get('state'):
                        update['state'] = llm['state']
                    if llm.get('expiration'):
                        update['expiration'] = llm['expiration']
                    print(f"    📍 Re-classified → LOCATION: {llm.get('location_name')}, {llm.get('city')}, {llm.get('state')}")
                else:
                    update['state'] = 'UNKNOWN'
                    print(f"    ❓ Unclassified by LLM")

                updates[url] = update

            except Exception as e:
                print(f"    ⚠️  Error: {str(e)[:60]}")

        browser.close()

    # Apply updates
    new_coupons = []
    for c in coupons:
        url = c.get('url', '')
        if url in ended_urls:
            continue
        if url in updates:
            c.update(updates[url])
        new_coupons.append(c)

    removed = len(coupons) - len(new_coupons)
    reclassified = len(updates)

    data['coupons'] = new_coupons
    data['total_coupons'] = len(new_coupons)

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"\n✅ Done: {reclassified} re-classified, {removed} removed (ended)")
    print(f"   Saved {len(new_coupons)} coupons to {JSON_FILE}")


if __name__ == '__main__':
    main()
