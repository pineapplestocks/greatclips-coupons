import tweepy
import json
import os
import random

def get_best_coupons(coupons_file='data/coupons.json', count=3):
    """Get the best coupons to tweet about"""
    with open(coupons_file, 'r') as f:
        data = json.load(f)
    
    # Coupons are nested under 'coupons' key
    coupons = data.get('coupons', [])
    
    # Separate universal and location-specific
    universal = [c for c in coupons if c.get('state') == 'US' or 'All' in c.get('location_name', '')]
    location_specific = [c for c in coupons if c not in universal]
    
    # Sort by price (lowest first)
    def get_price(c):
        try:
            price_str = c.get('price', '$999').replace('$', '').replace(' OFF', '')
            return float(price_str)
        except:
            return 999
    
    location_specific.sort(key=get_price)
    
    best = []
    
    # Always include universal if available
    if universal:
        best.append(universal[0])
    
    # Add cheapest location-specific coupons
    for coupon in location_specific[:count]:
        if coupon not in best:
            best.append(coupon)
    
    return best[:count]

def create_tweet_text(coupons):
    """Create engaging tweet text"""
    
    templates = [
        "✂️ NEW Great Clips Coupons! 💇\n\n",
        "🔥 Fresh Great Clips Deals! ✂️\n\n",
        "💰 Save on Haircuts Today! 💇‍♂️\n\n",
        "✂️ Haircut Coupons Alert! 🚨\n\n",
    ]
    
    tweet = random.choice(templates)
    
    for coupon in coupons:
        price = coupon.get('price', 'Deal')
        location = coupon.get('location_name', '')
        state = coupon.get('state', '')
        
        if state == 'US' or 'All' in location:
            tweet += f"🇺🇸 {price} - ALL US Locations!\n"
        else:
            # Clean up city - remove trailing comma and whitespace
            city = coupon.get('city', '').replace(',', '').strip()
            tweet += f"📍 {price} - {city}, {state}\n"
    
    tweet += "\n🔗 Get yours: greatclipsdeal.com\n"
    tweet += "\n#GreatClips #HaircutCoupons #Coupons #Deals #SaveMoney"
    
    # Twitter limit is 280 characters
    if len(tweet) > 280:
        # Truncate hashtags if needed
        tweet = tweet.split('#')[0].strip() + "\n#GreatClips #Coupons"
    
    return tweet

def post_tweet():
    """Post tweet to Twitter/X"""
    
    # Get credentials from environment variables
    api_key = os.environ.get('TWITTER_API_KEY')
    api_secret = os.environ.get('TWITTER_API_SECRET')
    access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
    access_secret = os.environ.get('TWITTER_ACCESS_SECRET')
    
    if not all([api_key, api_secret, access_token, access_secret]):
        print("❌ Missing Twitter credentials")
        return False
    
    # Authenticate with Twitter API v2
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret
    )
    
    # Get best coupons and create tweet
    try:
        coupons = get_best_coupons()
        tweet_text = create_tweet_text(coupons)
        
        print(f"📝 Tweet ({len(tweet_text)} chars):")
        print(tweet_text)
        print("-" * 40)
        
        # Post the tweet
        response = client.create_tweet(text=tweet_text)
        print(f"✅ Tweet posted! ID: {response.data['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Error posting tweet: {e}")
        return False

if __name__ == "__main__":
    post_tweet()
