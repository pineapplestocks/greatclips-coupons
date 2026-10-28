#!/usr/bin/env python3
"""Reject expired/inconsistent published coupons before deploying generated pages."""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from coupon_validity import is_expired
from generate_website import normalize_coupons, is_blocked_coupon


def audit(root=ROOT):
    errors = []
    source = json.loads((root/"data/coupons.json").read_text(encoding="utf-8"))
    feed = json.loads((root/"docs/data/coupons.json").read_text(encoding="utf-8"))
    html = (root/"docs/index.html").read_text(encoding="utf-8")
    match = re.search(r"const COUPON_DATA = (\[.*?\]);", html, re.S)
    if not match:
        errors.append("Homepage coupon JSON is missing")
        homepage = []
    else:
        homepage = json.loads(match.group(1))
    for name, coupons in (("feed", feed.get("coupons", [])), ("homepage", homepage)):
        for c in coupons:
            if is_expired(c):
                errors.append(name+": expired offer "+str(c.get("coupon_code") or c.get("url")))
            if is_blocked_coupon(c):
                errors.append(name+": blocked offer")
            raw = c.get("expiration")
            if raw and str(raw).upper() != "N/A":
                valid = False
                for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                    try:
                        datetime.strptime(raw, fmt); valid = True; break
                    except (ValueError, TypeError):
                        pass
                if not valid:
                    errors.append(name+": unreadable expiration "+str(raw))
    expected = normalize_coupons([c for c in source.get("coupons", []) if not is_blocked_coupon(c)])
    key = lambda c: (c.get("url"), c.get("price"), c.get("expiration"))
    if set(map(key, expected)) != set(map(key, feed.get("coupons", []))):
        errors.append("Published feed does not match current source offers")
    if set(map(key, expected)) != set(map(key, homepage)):
        errors.append("Homepage does not match current source offers")
    if feed.get("total") != len(feed.get("coupons", [])):
        errors.append("Feed total is incorrect")
    if feed.get("scraped_at") != source.get("scraped_at"):
        errors.append("Feed scan timestamp does not match source")
    sw = (root/"docs/sw.js").read_text(encoding="utf-8")
    if "INDEX_SOURCE" in sw or "raw.githubusercontent.com" in sw:
        errors.append("Legacy service-worker navigation proxy is still enabled")
    return {"source_offers":len(source.get("coupons", [])), "published_offers":len(feed.get("coupons", [])),
            "homepage_records":len(homepage), "scraped_at":source.get("scraped_at"), "verification":source.get("verification"), "errors":errors}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", help="Write a JSON audit report")
    args=parser.parse_args()
    try:
        report=audit()
    except (OSError, ValueError, TypeError) as e:
        report={"errors":[str(e)]}
    if args.report:
        path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    return 1 if report["errors"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
