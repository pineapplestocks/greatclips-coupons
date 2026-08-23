#!/usr/bin/env python3
"""
Submit URLs to IndexNow so Bing, Yandex, Seznam and Naver learn about them without
waiting to be crawled.

Worth doing here for two reasons. The site grew by 2,551 pages at once, and crawl
discovery for that many new URLs is slow. And IndexNow is a push protocol keyed to
a file we host, so it is unaffected by the robots.txt rules that currently limit
AI crawlers - Bing's index feeds Copilot among others.

Modes:
    --core   homepage, sitemaps, hubs, llms.txt        (safe to run every scrape)
    --all    everything in the sitemaps, in batches    (one-off after a big change)

Usage:
    python scripts/indexnow_submit.py --core
    python scripts/indexnow_submit.py --all
    python scripts/indexnow_submit.py --all --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
HOST = "greatclipsdeal.com"
SITE = f"https://{HOST}"
KEY_FILE = REPO_ROOT / "6b4474afbc6183c57a91.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"
BATCH_SIZE = 500  # IndexNow allows 10,000, but large POSTs got reset; 500 also
                  # means a failed batch loses less.
RETRIES = 4
RETRY_PAUSE = 5   # seconds, multiplied by the attempt number

CORE_PATHS = [
    "/",
    "/sitemap.xml",
    "/sitemap-main.xml",
    "/sitemap-salons.xml",
    "/llms.txt",
    "/salons",
    "/states",
    "/blog",
    "/faq",
]


def read_key() -> str:
    if not KEY_FILE.exists():
        raise SystemExit(f"IndexNow key file missing: {KEY_FILE}")
    return KEY_FILE.read_text(encoding="utf-8").strip()


def urls_from_sitemaps() -> list[str]:
    """Every <loc> in the child sitemaps, de-duplicated, order preserved."""
    found: list[str] = []
    for name in ("sitemap-main.xml", "sitemap-salons.xml"):
        path = DOCS / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        found.extend(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text))
    return list(dict.fromkeys(found))


def submit(urls: list[str], key: str, dry_run: bool) -> bool:
    payload = json.dumps(
        {
            "host": HOST,
            "key": key,
            "keyLocation": f"{SITE}/{KEY_FILE.name}",
            "urlList": urls,
        }
    ).encode("utf-8")

    if dry_run:
        print(f"  [dry run] would submit {len(urls)} urls")
        return True

    # IndexNow throttles repeated submissions and simply resets the connection, so
    # retry with a growing pause rather than treating the first drop as fatal.
    for attempt in range(1, RETRIES + 1):
        request = urllib.request.Request(
            ENDPOINT,
            data=payload,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": f"greatclipsdeal-indexnow/1.0 (+{SITE})",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                # 200 accepted, 202 accepted-pending-key-validation.
                print(f"  submitted {len(urls):>5} urls -> HTTP {response.status}")
                return response.status in (200, 202)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:160]
            # 429 is worth another try; other HTTP errors are not.
            if exc.code != 429:
                print(f"  {len(urls):>5} urls -> HTTP {exc.code}  {body}")
                return False
            print(f"  {len(urls):>5} urls -> HTTP 429, backing off")
        except (urllib.error.URLError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            print(f"  attempt {attempt}/{RETRIES} failed: {reason}")

        if attempt < RETRIES:
            time.sleep(RETRY_PAUSE * attempt)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--core", action="store_true", help="key pages only (default)")
    group.add_argument("--all", action="store_true", help="every sitemap URL")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch", type=int, default=BATCH_SIZE,
                    help=f"urls per request (default {BATCH_SIZE})")
    args = ap.parse_args()

    key = read_key()

    if args.all:
        urls = urls_from_sitemaps()
        if not urls:
            print("No sitemap URLs found - run update_sitemap.py first.")
            return 1
        # Keep the hubs at the front so they are submitted even if a batch fails.
        core = [f"{SITE}{p}" if p != "/" else f"{SITE}/" for p in CORE_PATHS]
        urls = list(dict.fromkeys(core + urls))
    else:
        urls = [f"{SITE}{p}" if p != "/" else f"{SITE}/" for p in CORE_PATHS]

    batch_size = max(1, args.batch)
    print(f"IndexNow: {len(urls)} url(s) in "
          f"{(len(urls) + batch_size - 1) // batch_size} batch(es)")
    ok = True
    for start in range(0, len(urls), batch_size):
        batch = urls[start : start + batch_size]
        if not submit(batch, key, args.dry_run):
            ok = False
        if start + batch_size < len(urls) and not args.dry_run:
            time.sleep(4)  # be polite between batches

    # A failed ping is not a reason to fail the build; the sitemap still works.
    print("Done." if ok else "Done with errors (sitemap discovery still applies).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
