"""
Twitter/X auto-poster for Great Clips coupon updates.

This keeps the automation local to the existing coupon pipeline instead of
generating generic AI tweets. It selects current, unposted coupons from
data/coupons.json, posts a concise update, and records post history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests

try:
    import tweepy
except ImportError:
    tweepy = None


ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
COUPONS_FILE = DATA_DIR / "coupons.json"
POSTED_FILE = DATA_DIR / "posted_tweets.json"

DEFAULT_WEBSITE_URL = "https://greatclipsdeal.com"
MAX_TWEET_LENGTH = 280

TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET")
BUFFER_API_KEY = os.environ.get("BUFFER_API_KEY") or os.environ.get("Buffer")
BUFFER_CHANNEL_ID = os.environ.get("BUFFER_CHANNEL_ID")
BUFFER_ORGANIZATION_ID = os.environ.get("BUFFER_ORGANIZATION_ID")

TEMPLATES = [
    "Great Clips coupon alert: {price} haircut {place}. {expires}\n\nGet the details: {url}\n\n#GreatClips #HaircutCoupon #Deals",
    "New Great Clips deal found: {price} {place}. {expires}\n\nSee current coupons: {url}\n\n#GreatClips #Coupons",
    "Fresh haircut savings: {price} {place}. {expires}\n\nMore coupons: {url}\n\n#GreatClips #HaircutDeals",
    "Great Clips savings update: {price} coupon {place}. {expires}\n\nCheck availability: {url}\n\n#GreatClips #SaveMoney",
]


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, sort_keys=True)
        file.write("\n")


def load_coupons() -> list[dict[str, Any]]:
    data = load_json(COUPONS_FILE, {"coupons": []})
    return [coupon for coupon in data.get("coupons", []) if isinstance(coupon, dict)]


def normalize_posted(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}

    posted_urls = raw.get("posted", [])
    if not isinstance(posted_urls, list):
        posted_urls = []

    history = raw.get("history", [])
    if not isinstance(history, list):
        history = []

    normalized_history = [entry for entry in history if isinstance(entry, dict)]

    known_urls = {
        entry.get("coupon_url")
        for entry in normalized_history
        if isinstance(entry.get("coupon_url"), str)
    }
    for url in posted_urls:
        if isinstance(url, str) and url not in known_urls:
            normalized_history.append({"coupon_url": url})
            known_urls.add(url)

    return {
        "posted": sorted(url for url in known_urls if url),
        "history": normalized_history[-250:],
        "last_post": raw.get("last_post"),
    }


def load_posted() -> dict[str, Any]:
    return normalize_posted(load_json(POSTED_FILE, {}))


def parse_date(value: Any) -> date | None:
    if not value:
        return None

    text = str(value).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def parse_price(value: Any) -> float:
    if value is None:
        return 999.0
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else 999.0


def clean_city(value: Any) -> str:
    return str(value or "").replace(",", "").strip()


def coupon_key(coupon: dict[str, Any]) -> str:
    url = coupon.get("url")
    if isinstance(url, str) and url:
        return url

    digest = hashlib.sha256(
        json.dumps(coupon, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    return f"coupon:{digest}"


def is_universal(coupon: dict[str, Any]) -> bool:
    state = str(coupon.get("state") or "").upper()
    market = str(coupon.get("market") or "").upper()
    note = str(coupon.get("participating_location_note") or "").lower()
    location = str(coupon.get("location_name") or "").lower()
    return state in {"US", "AREA"} or market == "US" or "participating us" in note or "all us" in location


def is_current(coupon: dict[str, Any], today: date | None = None) -> bool:
    today = today or date.today()
    expiration = parse_date(coupon.get("expiration"))
    return expiration is None or expiration >= today


def location_text(coupon: dict[str, Any]) -> str:
    if is_universal(coupon):
        area = coupon.get("area_name") or coupon.get("market")
        if area:
            area_text = str(area).strip()
            if area_text.upper() != "US" and "participating us" not in area_text.lower():
                area_text = re.sub(r"^(participating|off only at participating)\s+", "", area_text, flags=re.I)
                return f"in the {area_text} area"
        return "at participating US locations"

    city = clean_city(coupon.get("city"))
    state = str(coupon.get("state") or "").strip()
    location = str(coupon.get("location_name") or "").strip()

    if city and state:
        return f"in {city}, {state}"
    if state:
        return f"in {state}"
    if location:
        return f"at {location}"
    return "at participating locations"


def expires_text(coupon: dict[str, Any]) -> str:
    expiration = parse_date(coupon.get("expiration"))
    if not expiration:
        return "Limited time offer."
    return f"Expires {expiration.strftime('%b %-d, %Y') if os.name != 'nt' else expiration.strftime('%b %#d, %Y')}."


def coupon_url(coupon: dict[str, Any], website_url: str) -> str:
    slug = coupon.get("coupon_code")
    if isinstance(slug, str) and slug.strip():
        return f"{website_url.rstrip('/')}/coupon-codes/#{slug.strip()}"
    return website_url.rstrip("/")


def create_tweet_text(coupon: dict[str, Any], website_url: str = DEFAULT_WEBSITE_URL) -> str:
    price = str(coupon.get("price") or "coupon").strip()
    tweet = random.choice(TEMPLATES).format(
        price=price,
        place=location_text(coupon),
        expires=expires_text(coupon),
        url=coupon_url(coupon, website_url),
    )

    if len(tweet) <= MAX_TWEET_LENGTH:
        return tweet

    short_tweet = (
        f"Great Clips coupon: {price} {location_text(coupon)}. "
        f"{expires_text(coupon)}\n\n{website_url.rstrip('/')}\n\n#GreatClips #Coupons"
    )
    return short_tweet[: MAX_TWEET_LENGTH - 1].rstrip() if len(short_tweet) > MAX_TWEET_LENGTH else short_tweet


def sort_coupons(coupon: dict[str, Any]) -> tuple[int, float, date, str]:
    expiration = parse_date(coupon.get("expiration")) or date.max
    return (
        0 if is_universal(coupon) else 1,
        parse_price(coupon.get("price")),
        expiration,
        coupon_key(coupon),
    )


def select_coupons(
    coupons: list[dict[str, Any]],
    posted_data: dict[str, Any],
    max_posts: int,
) -> list[dict[str, Any]]:
    posted = set(posted_data.get("posted", []))
    eligible = [
        coupon
        for coupon in coupons
        if coupon_key(coupon) not in posted and is_current(coupon)
    ]
    eligible.sort(key=sort_coupons)
    return eligible[:max_posts]


def twitter_clients() -> tuple[tweepy.Client, tweepy.API]:
    if tweepy is None:
        raise RuntimeError("Install tweepy before posting: pip install tweepy")

    missing = [
        name
        for name, value in {
            "TWITTER_API_KEY": TWITTER_API_KEY,
            "TWITTER_API_SECRET": TWITTER_API_SECRET,
            "TWITTER_ACCESS_TOKEN": TWITTER_ACCESS_TOKEN,
            "TWITTER_ACCESS_SECRET": TWITTER_ACCESS_SECRET,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing Twitter credentials: {', '.join(missing)}")

    auth = tweepy.OAuth1UserHandler(
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_SECRET,
    )
    api_v1 = tweepy.API(auth)
    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET,
    )
    return client, api_v1


def buffer_graphql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    if not BUFFER_API_KEY:
        raise RuntimeError("Missing Buffer API key. Set BUFFER_API_KEY or GitHub secret Buffer.")

    response = requests.post(
        "https://api.buffer.com",
        headers={
            "Authorization": f"Bearer {BUFFER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(f"Buffer API error: {payload['errors']}")
    return payload.get("data", {})


def get_buffer_organization_id() -> str:
    if BUFFER_ORGANIZATION_ID:
        return BUFFER_ORGANIZATION_ID

    data = buffer_graphql(
        """
        query GetOrganizations {
          account {
            organizations {
              id
              name
            }
          }
        }
        """
    )
    organizations = data.get("account", {}).get("organizations", [])
    if not organizations:
        raise RuntimeError("Buffer account has no organizations available.")
    return organizations[0]["id"]


def get_buffer_channel_id() -> str:
    if BUFFER_CHANNEL_ID:
        return BUFFER_CHANNEL_ID

    organization_id = get_buffer_organization_id()
    data = buffer_graphql(
        f"""
        query GetChannels {{
          channels(input: {{ organizationId: {json.dumps(organization_id)} }}) {{
            id
            name
            displayName
            service
            isQueuePaused
          }}
        }}
        """,
    )
    channels = data.get("channels", [])
    x_channels = [
        channel
        for channel in channels
        if str(channel.get("service", "")).lower() in {"twitter", "x"}
    ]
    if not x_channels:
        services = ", ".join(sorted({str(channel.get("service")) for channel in channels}))
        raise RuntimeError(f"No X/Twitter channel found in Buffer. Connected services: {services or 'none'}")

    channel = x_channels[0]
    label = channel.get("displayName") or channel.get("name") or channel["id"]
    print(f"Using Buffer channel: {label} ({channel['id']})")
    if channel.get("isQueuePaused"):
        print("Warning: this Buffer channel queue is paused.")
    return channel["id"]


def post_to_buffer(text: str, image_url: Any, attach_media: bool) -> str:
    channel_id = get_buffer_channel_id()
    assets = ""
    if attach_media and isinstance(image_url, str) and image_url.startswith("https://"):
        assets = f'assets: [{{ image: {{ url: {json.dumps(image_url)} }} }}]'

    query = f"""
    mutation CreatePost {{
      createPost(input: {{
        text: {json.dumps(text)}
        channelId: {json.dumps(channel_id)}
        schedulingType: automatic
        mode: addToQueue
        {assets}
      }}) {{
        ... on PostActionSuccess {{
          post {{
            id
            text
            dueAt
          }}
        }}
        ... on MutationError {{
          message
        }}
      }}
    }}
    """
    data = buffer_graphql(query)
    result = data.get("createPost") or {}
    if result.get("message"):
        raise RuntimeError(f"Buffer failed to create post: {result['message']}")
    post = result.get("post")
    if not post or not post.get("id"):
        raise RuntimeError(f"Unexpected Buffer response: {result}")

    due_at = post.get("dueAt")
    print(f"Queued Buffer post ID: {post['id']}" + (f" for {due_at}" if due_at else ""))
    return str(post["id"])


def download_image(url: Any) -> str | None:
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return None

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    suffix = Path(url.split("?", 1)[0]).suffix
    if suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        suffix = ".jpg"

    image = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        image.write(response.content)
        return image.name
    finally:
        image.close()


def post_tweet(
    client: tweepy.Client,
    api_v1: tweepy.API,
    text: str,
    image_url: Any,
    attach_media: bool,
) -> str:
    media_ids = None
    temp_image = None

    if attach_media:
        try:
            temp_image = download_image(image_url)
            if temp_image:
                media = api_v1.media_upload(filename=temp_image)
                media_ids = [media.media_id]
        except Exception as exc:
            print(f"Media upload skipped: {exc}")
        finally:
            if temp_image:
                try:
                    os.remove(temp_image)
                except OSError:
                    pass

    response = client.create_tweet(text=text, media_ids=media_ids)
    return str(response.data["id"])


def record_post(
    posted_data: dict[str, Any],
    coupon: dict[str, Any],
    post_id: str,
    text: str,
    provider: str,
) -> None:
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    key = coupon_key(coupon)

    posted = set(posted_data.get("posted", []))
    posted.add(key)
    posted_data["posted"] = sorted(posted)
    posted_data["last_post"] = now

    history = posted_data.setdefault("history", [])
    history.append(
        {
            "coupon_url": key,
            "coupon_code": coupon.get("coupon_code"),
            "provider": provider,
            "post_id": post_id,
            "tweet_id": post_id if provider == "twitter" else None,
            "posted_at": now,
            "tweet_text": text,
        }
    )
    posted_data["history"] = history[-250:]


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post Great Clips coupons to Twitter/X.")
    parser.add_argument(
        "--max-posts",
        type=int,
        default=int(os.environ.get("TWITTER_MAX_POSTS_PER_RUN", "1")),
        help="Maximum coupons to post in this run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=env_bool("TWITTER_DRY_RUN"),
        help="Print selected tweets without posting.",
    )
    parser.add_argument(
        "--no-media",
        action="store_true",
        default=env_bool("TWITTER_NO_MEDIA"),
        help="Post text only, without coupon images.",
    )
    parser.add_argument(
        "--provider",
        choices=("auto", "buffer", "twitter"),
        default=os.environ.get("POST_PROVIDER", "auto"),
        help="Posting backend. auto prefers Buffer when BUFFER_API_KEY is set.",
    )
    parser.add_argument(
        "--website-url",
        default=os.environ.get("WEBSITE_URL", DEFAULT_WEBSITE_URL),
        help="Public website URL used in tweets.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    max_posts = max(1, args.max_posts)

    coupons = load_coupons()
    posted_data = load_posted()
    to_post = select_coupons(coupons, posted_data, max_posts)

    print(f"Loaded {len(coupons)} coupons.")
    print(f"Already posted: {len(posted_data.get('posted', []))}.")
    print(f"Selected for this run: {len(to_post)}.")

    if not to_post:
        if not args.dry_run:
            save_json(POSTED_FILE, posted_data)
        return 0

    provider = args.provider
    if provider == "auto":
        provider = "buffer" if BUFFER_API_KEY else "twitter"
    print(f"Posting provider: {provider}.")

    client = api_v1 = None
    if not args.dry_run:
        if provider == "twitter":
            client, api_v1 = twitter_clients()
        elif provider != "buffer":
            raise RuntimeError(f"Unsupported provider: {provider}")

    for index, coupon in enumerate(to_post, start=1):
        text = create_tweet_text(coupon, args.website_url)
        print(f"\n[{index}/{len(to_post)}] {coupon.get('price', 'Deal')} - {location_text(coupon)}")
        print(text)

        if args.dry_run:
            continue

        if provider == "buffer":
            post_id = post_to_buffer(
                text=text,
                image_url=coupon.get("image_url"),
                attach_media=not args.no_media,
            )
        else:
            post_id = post_tweet(
                client=client,
                api_v1=api_v1,
                text=text,
                image_url=coupon.get("image_url"),
                attach_media=not args.no_media,
            )
            print(f"Posted tweet ID: {post_id}")
        record_post(posted_data, coupon, post_id, text, provider)

    if not args.dry_run:
        save_json(POSTED_FILE, posted_data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
