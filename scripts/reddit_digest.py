#!/usr/bin/env python3
"""
Weekly Reddit digest: find fresh threads asking about Great Clips coupons/prices
and draft data-backed replies for Kumar to review and post manually.

Runs in GitHub Actions (see .github/workflows/reddit-digest.yml), which opens a
GitHub issue with the digest. No LLM/API keys required: replies are templates
filled with live numbers from data/coupons.json.

Posting policy (why this script only DRAFTS): auto-posting promotional replies
gets accounts shadowbanned and can get the domain blacklisted on Reddit, which
would also hurt AI-assistant visibility. A human posts these, with edits.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from statistics import median
from urllib.parse import quote
from urllib.request import Request, urlopen

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "..", "data", "coupons.json")
OUT_FILE = os.environ.get("DIGEST_OUT", "digest.md")

USER_AGENT = "greatclipsdeal-weekly-digest/1.0 (research digest; contact: greatclipsdeal@gmail.com)"

SEARCH_QUERIES = [
    "great clips coupon",
    "great clips price",
    "great clips cost haircut",
    "cheap haircut coupon",
    "greatclipsdeal",  # brand-mention monitoring
]

# Words that suggest the thread is a question/discussion we can help with
RELEVANT_HINTS = (
    "coupon", "price", "cost", "deal", "discount", "cheap", "how much", "haircut",
)


def fetch_json(url, headers=None, data=None):
    req = Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})}, data=data)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


_TOKEN_CACHE = {}


def get_oauth_token():
    """App-only OAuth token. Needs REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET
    (free 'script' app from https://www.reddit.com/prefs/apps)."""
    if "token" in _TOKEN_CACHE:
        return _TOKEN_CACHE["token"]
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    import base64
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = fetch_json(
        "https://www.reddit.com/api/v1/access_token",
        headers={"Authorization": f"Basic {auth}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        data=b"grant_type=client_credentials",
    )
    _TOKEN_CACHE["token"] = resp.get("access_token")
    return _TOKEN_CACHE["token"]


def search_reddit(query):
    """Search via OAuth when credentials exist (reliable); otherwise try the
    public endpoint, which Reddit often blocks from datacenter IPs."""
    params = "q=" + quote(query) + "&sort=new&t=week&limit=25&type=link"
    token = get_oauth_token()
    if token:
        url = "https://oauth.reddit.com/search?" + params
        data = fetch_json(url, headers={"Authorization": f"Bearer {token}"})
    else:
        url = "https://www.reddit.com/search.json?" + params
        data = fetch_json(url)
    for child in data.get("data", {}).get("children", []):
        yield child.get("data", {})


def load_live_stats():
    """Pull current numbers from the live coupon data so drafts cite fresh facts."""
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    prices = []
    states = set()
    for c in data.get("coupons", []):
        try:
            p = float((c.get("price") or "").replace("$", ""))
        except ValueError:
            continue
        if 0 < p < 100:
            prices.append(p)
        st = (c.get("state") or "").strip()
        if st and st.upper() not in ("AREA", "UNKNOWN", "US", "OTHER"):
            states.add(st)
    if not prices:
        return None
    return {
        "count": len(prices),
        "lowest": min(prices),
        "median": median(sorted(prices)),
        "states": len(states),
    }


def draft_replies(stats):
    """Three reply templates. Rotate them; only one includes a link."""
    if not stats:
        return ["(No live coupon data available this run — write the reply from the site's current board.)"]
    lowest = f"${stats['lowest']:.2f}"
    med = f"${stats['median']:.2f}"
    return [
        # 1: helpful, no link — builds account credibility
        (
            "Great Clips coupons are run by individual franchise owners through Facebook ads, so there's no "
            "single official coupon page — that's why they seem random. If it helps calibrate: I track these, "
            f"and right now there are about {stats['count']} live offers across {stats['states']} states; "
            f"the typical one is around {med} and the cheapest is {lowest}. Most offers expire within 2-3 weeks "
            "of appearing, so if you see one for your salon, use it soon. Also worth asking your local salon "
            "directly — some honor competitor or expired coupons at their discretion."
        ),
        # 2: data answer with link (use sparingly, when the thread directly asks where to find coupons)
        (
            "They come from franchise owners' Facebook ads, which is why they're so hit-or-miss. I got tired of "
            f"missing them and built a tracker that collects them all — right now it shows ~{stats['count']} live "
            f"coupons, typical price {med}, cheapest {lowest}. It's free, no signup: greatclipsdeal.com. "
            "Fair warning from the data: the viral $5.99 deals are real but only ~15% of offers, so a $9.99-$10.99 "
            "coupon is a normal good deal, not a ripoff."
        ),
        # 3: price-question answer, no link
        (
            "Regular price is usually $15-19 depending on the market. With a coupon you can knock that down a lot — "
            f"I track these and the median coupon right now is about {med}, with the cheapest at {lowest}. "
            "One thing most people don't know: coupon prices vary hugely by state (Texas medians are several "
            "dollars cheaper than California), so what your friend pays in another state isn't what you'll pay."
        ),
    ]


def main():
    now = datetime.now(timezone.utc)
    seen = set()
    threads = []
    errors = []

    for q in SEARCH_QUERIES:
        try:
            for post in search_reddit(q):
                permalink = post.get("permalink") or ""
                if not permalink or permalink in seen:
                    continue
                seen.add(permalink)
                title = post.get("title") or ""
                text = (title + " " + (post.get("selftext") or "")[:500]).lower()
                if "great clips" not in text and "greatclipsdeal" not in text:
                    continue
                if not any(h in text for h in RELEVANT_HINTS):
                    continue
                created = datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc)
                threads.append({
                    "title": title.strip(),
                    "subreddit": post.get("subreddit_name_prefixed") or "",
                    "url": "https://www.reddit.com" + permalink,
                    "score": post.get("score", 0),
                    "comments": post.get("num_comments", 0),
                    "age_days": (now - created).days,
                    "query": q,
                })
            time.sleep(2)  # be polite to reddit
        except Exception as exc:  # noqa: BLE001 - report and continue with other queries
            errors.append(f"`{q}`: {exc}")

    threads.sort(key=lambda t: (-t["score"], t["age_days"]))

    try:
        stats = load_live_stats()
    except Exception:
        stats = None
    replies = draft_replies(stats)

    lines = [f"Weekly scan of Reddit for Great Clips coupon/price threads ({now:%Y-%m-%d}).", ""]
    if threads:
        lines.append(f"**{len(threads)} thread(s) found this week.** Post replies manually from your own "
                     "account, edit the wording each time, and use the linked template at most once or twice "
                     "per week.")
        lines.append("")
        for i, t in enumerate(threads[:10], 1):
            lines.append(f"### {i}. [{t['title']}]({t['url']})")
            lines.append(f"{t['subreddit']} · {t['score']} points · {t['comments']} comments · "
                         f"{t['age_days']}d old · matched `{t['query']}`")
            lines.append("")
            lines.append(f"**Suggested reply (template {(i - 1) % len(replies) + 1}):**")
            lines.append("")
            lines.append("> " + replies[(i - 1) % len(replies)])
            lines.append("")
    else:
        lines.append("No matching threads found this week.")
        lines.append("")

    if errors:
        lines.append("**Errors during search** (Reddit sometimes blocks CI IPs; if this persists every "
                     "week, we should switch to authenticated Reddit API access):")
        lines.extend(f"- {e}" for e in errors)
        lines.append("")

    lines.append("---")
    lines.append("*Reminder: never auto-post these. Vary the wording, answer the actual question, and skip "
                 "the link unless the thread explicitly asks where to find coupons.*")

    body = "\n".join(lines)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"Wrote {OUT_FILE}: {len(threads)} threads, {len(errors)} errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
