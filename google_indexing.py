#!/usr/bin/env python3
"""
Google Indexing API - Notify Google when pages are updated.
This dramatically speeds up indexing from days/weeks to hours.

Setup required:
1. Create a Google Cloud Project
2. Enable the Indexing API
3. Create a Service Account
4. Add the service account email to Google Search Console as an owner
5. Download the JSON key and save as GOOGLE_INDEXING_CREDENTIALS secret
"""

import os
import json
import sys
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    print("Installing required packages...")
    os.system("pip install google-auth google-api-python-client --break-system-packages")
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

# Configuration
SITE_URL = "https://greatclipsdeal.com"
SCOPES = ["https://www.googleapis.com/auth/indexing"]

def get_credentials():
    """Load credentials from environment variable or file"""
    # Try environment variable first (for GitHub Actions)
    creds_json = os.environ.get('GOOGLE_INDEXING_CREDENTIALS')
    
    if creds_json:
        creds_dict = json.loads(creds_json)
        return service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
    
    # Fall back to file
    creds_file = Path('google-indexing-credentials.json')
    if creds_file.exists():
        return service_account.Credentials.from_service_account_file(
            str(creds_file), scopes=SCOPES
        )
    
    raise Exception(
        "No credentials found. Set GOOGLE_INDEXING_CREDENTIALS env var "
        "or create google-indexing-credentials.json file"
    )

def submit_url(service, url, action="URL_UPDATED"):
    """
    Submit a URL to Google for indexing.
    
    action can be:
    - URL_UPDATED: URL has been updated (most common)
    - URL_DELETED: URL has been removed
    """
    body = {
        "url": url,
        "type": action
    }
    
    try:
        response = service.urlNotifications().publish(body=body).execute()
        print(f"✓ Submitted: {url}")
        print(f"  Notification time: {response.get('urlNotificationMetadata', {}).get('latestUpdate', {}).get('notifyTime', 'N/A')}")
        return True
    except Exception as e:
        print(f"✗ Failed: {url}")
        print(f"  Error: {str(e)}")
        return False

def submit_batch(urls, action="URL_UPDATED"):
    """Submit multiple URLs for indexing"""
    try:
        credentials = get_credentials()
        service = build('indexing', 'v3', credentials=credentials)
    except Exception as e:
        print(f"❌ Failed to initialize Google Indexing API: {e}")
        print("\n📋 Setup Instructions:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project (or select existing)")
        print("3. Enable 'Web Search Indexing API'")
        print("4. Go to 'Credentials' > 'Create Credentials' > 'Service Account'")
        print("5. Download the JSON key file")
        print("6. Go to Google Search Console > Settings > Users and permissions")
        print("7. Add the service account email as an Owner")
        print("8. Save JSON contents as GOOGLE_INDEXING_CREDENTIALS GitHub secret")
        return []
    
    results = []
    for url in urls:
        success = submit_url(service, url, action)
        results.append({"url": url, "success": success})
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    print(f"\n📊 Summary: {successful}/{len(urls)} URLs submitted successfully")
    
    return results

def get_core_urls():
    """Get list of core URLs to submit for indexing"""
    return [
        f"{SITE_URL}/",
        f"{SITE_URL}/states",
        f"{SITE_URL}/faq",
        f"{SITE_URL}/how-to-use",
        f"{SITE_URL}/prices",
        f"{SITE_URL}/calculator",
        f"{SITE_URL}/5-99-coupon",
        f"{SITE_URL}/6-99-coupon",
        f"{SITE_URL}/blog",
    ]

def get_state_urls():
    """Get all state page URLs"""
    states = [
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
        "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
        "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
        "maine", "maryland", "massachusetts", "michigan", "minnesota",
        "mississippi", "missouri", "montana", "nebraska", "nevada",
        "new-hampshire", "new-jersey", "new-mexico", "new-york",
        "north-carolina", "north-dakota", "ohio", "oklahoma", "oregon",
        "pennsylvania", "rhode-island", "south-carolina", "south-dakota",
        "tennessee", "texas", "utah", "vermont", "virginia", "washington",
        "west-virginia", "wisconsin", "wyoming"
    ]
    return [f"{SITE_URL}/{state}" for state in states]

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Submit URLs to Google Indexing API")
    parser.add_argument('--urls', nargs='+', help='Specific URLs to submit')
    parser.add_argument('--file', help='File containing URLs (one per line)')
    parser.add_argument('--core', action='store_true', help='Submit core pages only')
    parser.add_argument('--states', action='store_true', help='Submit state pages')
    parser.add_argument('--all', action='store_true', help='Submit all pages')
    parser.add_argument('--homepage', action='store_true', help='Submit homepage only')
    
    args = parser.parse_args()
    
    urls = []
    
    if args.urls:
        urls = args.urls
    elif args.file:
        with open(args.file) as f:
            urls = [line.strip() for line in f if line.strip()]
    elif args.homepage:
        urls = [f"{SITE_URL}/"]
    elif args.core:
        urls = get_core_urls()
    elif args.states:
        urls = get_state_urls()
    elif args.all:
        urls = get_core_urls() + get_state_urls()
    else:
        # Default: submit homepage
        urls = [f"{SITE_URL}/"]
    
    if not urls:
        print("No URLs to submit")
        return
    
    print(f"🚀 Submitting {len(urls)} URL(s) to Google Indexing API...\n")
    submit_batch(urls)

if __name__ == "__main__":
    main()
