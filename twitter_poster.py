"""
Twitter Auto-Poster for Great Clips Coupons
Posts coupons slowly throughout the day to avoid spam detection.
Includes social media preview image with each tweet.
"""

import os
import json
import random
import requests
import tweepy
from datetime import datetime, timedelta

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
COUPONS_FILE = os.path.join(DATA_DIR, "coupons.json")
POSTED_FILE = os.path.join(DATA_DIR, "posted_tweets.json")

# Twitter API credentials (from GitHub Secrets)
TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.environ.get('TWITTER_ACCESS_SECRET')

# Website URL
WEBSITE_URL = "https://greatclipsdeal.com"

# Social media preview image
PREVIEW_IMAGE_URL = "https://5cfac31ce2fbf02462a3-5c2a4595f00d000c62f38115ac0c4e4e.ssl.cf1.rackcdn.com/uploads_production/promotion_images/file/15833/50707-002-1200x600-US-Sparkfly-1off-10off5.jpg"
LOCAL_IMAGE_PATH = os.path.join(DATA_DIR, "twitter_image.jpg")

# How many coupons to post per run (to spread throughout day)
MAX_POSTS_PER_RUN = 3


def load_coupons():
    """Load coupons from JSON file"""
    if os.path.exists(COUPONS_FILE):
        with open(COUPONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('coupons', [])
    return []


def load_posted():
    """Load list of already-posted coupon URLs"""
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    return {"posted": [], "last_post": None}


def save_posted(posted_data):
    """Save posted coupons list"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(POSTED_FILE, 'w', encoding='utf-8') as f:
        json.dump(posted_data, f, indent=2)


def create_tweet_text(coupon):
    """Generate tweet text for a coupon"""
    price = coupon.get('price', 'discount')
    location = coupon.get('location_name', '')
    city = coupon.get('city', '')
    state = coupon.get('state', '')
    expiration = coupon.get('expiration', '')
    
    # Different tweet templates for variety
    templates = [
        "✂️ Great Clips Coupon Alert! {price} haircut{location_text}! {exp_text}\n\n🔗 Get yours: {url}\n\n#GreatClips #HaircutCoupon #Deals",
        "💇 Save on your next haircut! {price} at Great Clips{location_text}. {exp_text}\n\n👉 {url}\n\n#GreatClips #Coupons #SaveMoney",
        "🔥 {price} Great Clips coupon{location_text}! Don't miss out. {exp_text}\n\n✂️ Grab it: {url}\n\n#GreatClips #HaircutDeals",
        "💰 Cheap haircuts! {price} at Great Clips{location_text}. {exp_text}\n\nFind more deals: {url}\n\n#GreatClips #Frugal #Deals",
        "✂️ Haircut deal: {price} Great Clips coupon{location_text}! {exp_text}\n\n🎯 {url}\n\n#GreatClips #Coupon #Savings"
    ]
    
    # Build location text
    if state == 'US' or not location:
        location_text = " (any US location)"
    elif city and state:
        location_text = f" in {city}, {state}"
    elif state:
        location_text = f" in {state}"
    else:
        location_text = f" at {location[:20]}" if location else ""
    
    # Build expiration text
    if expiration and expiration != 'N/A':
        exp_text = f"Expires {expiration}."
    else:
        exp_text = "Limited time!"
    
    # Pick a random template
    template = random.choice(templates)
    
    tweet = template.format(
        price=price,
        location_text=location_text,
        exp_text=exp_text,
        url=WEBSITE_URL
    )
    
    # Ensure tweet is under 280 characters
    if len(tweet) > 280:
        tweet = tweet[:277] + "..."
    
    return tweet


def download_preview_image():
    """Download the social media preview image"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Download image
        response = requests.get(PREVIEW_IMAGE_URL, timeout=30)
        response.raise_for_status()
        
        with open(LOCAL_IMAGE_PATH, 'wb') as f:
            f.write(response.content)
        
        print(f"   ✅ Downloaded preview image")
        return LOCAL_IMAGE_PATH
    except Exception as e:
        print(f"   ⚠️ Could not download image: {e}")
        return None


def post_to_twitter(tweet_text):
    """Post a tweet with image using Twitter API"""
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        print("   ❌ Twitter credentials not found in environment variables")
        return False
    
    try:
        # Create Twitter API v1.1 client (needed for media upload)
        auth = tweepy.OAuth1UserHandler(
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_SECRET
        )
        api_v1 = tweepy.API(auth)
        
        # Create Twitter API v2 client (for posting tweet)
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET
        )
        
        # Upload image using v1.1 API
        media_id = None
        if os.path.exists(LOCAL_IMAGE_PATH):
            try:
                media = api_v1.media_upload(filename=LOCAL_IMAGE_PATH)
                media_id = media.media_id
                print(f"   ✅ Uploaded image, media_id: {media_id}")
            except Exception as e:
                print(f"   ⚠️ Could not upload image: {e}")
        
        # Post tweet with image
        if media_id:
            response = client.create_tweet(text=tweet_text, media_ids=[media_id])
        else:
            response = client.create_tweet(text=tweet_text)
        
        print(f"   ✅ Tweet posted! ID: {response.data['id']}")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to post tweet: {e}")
        return False


def get_coupons_to_post(coupons, posted_data):
    """Select coupons that haven't been posted recently"""
    posted_urls = set(posted_data.get('posted', []))
    
    # Filter out already posted coupons
    unposted = [c for c in coupons if c.get('url') not in posted_urls]
    
    # Prioritize US-wide coupons and best prices
    def sort_key(c):
        # US-wide coupons first
        is_us = 1 if c.get('state') == 'US' else 0
        # Lower price = higher priority
        try:
            price = float(c.get('price', '$999').replace('$', '').replace(' OFF', ''))
        except:
            price = 999
        return (-is_us, price)
    
    unposted.sort(key=sort_key)
    
    return unposted[:MAX_POSTS_PER_RUN]


def clean_old_posted(posted_data, days=7):
    """Remove posts older than X days from tracking (allow re-posting)"""
    # For simplicity, just keep the last 100 posted URLs
    if len(posted_data.get('posted', [])) > 100:
        posted_data['posted'] = posted_data['posted'][-50:]
    return posted_data


def main():
    print("=" * 60)
    print("🐦 Twitter Auto-Poster for Great Clips Coupons")
    print("=" * 60)
    print()
    
    # Check for credentials
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        print("❌ Missing Twitter API credentials!")
        print("   Set these GitHub Secrets:")
        print("   - TWITTER_API_KEY")
        print("   - TWITTER_API_SECRET")
        print("   - TWITTER_ACCESS_TOKEN")
        print("   - TWITTER_ACCESS_SECRET")
        return
    
    # Download preview image once
    print("🖼️ Downloading preview image...")
    download_preview_image()
    print()
    
    # Load data
    coupons = load_coupons()
    posted_data = load_posted()
    
    print(f"📦 Loaded {len(coupons)} coupons")
    print(f"📝 Previously posted: {len(posted_data.get('posted', []))} coupons")
    print()
    
    # Get coupons to post
    to_post = get_coupons_to_post(coupons, posted_data)
    
    if not to_post:
        print("ℹ️ No new coupons to post (all have been posted recently)")
        return
    
    print(f"📤 Will post {len(to_post)} coupon(s)...")
    print()
    
    # Post each coupon
    for i, coupon in enumerate(to_post):
        print(f"[{i+1}/{len(to_post)}] Posting coupon...")
        print(f"   Price: {coupon.get('price', 'N/A')}")
        print(f"   Location: {coupon.get('location_name', 'Unknown')}")
        
        tweet_text = create_tweet_text(coupon)
        print(f"   Tweet: {tweet_text[:50]}...")
        
        if post_to_twitter(tweet_text):
            # Mark as posted
            if 'posted' not in posted_data:
                posted_data['posted'] = []
            posted_data['posted'].append(coupon.get('url'))
            posted_data['last_post'] = datetime.now().isoformat()
        
        print()
    
    # Clean old entries and save
    posted_data = clean_old_posted(posted_data)
    save_posted(posted_data)
    
    print("✅ Done!")


if __name__ == "__main__":
    main()
