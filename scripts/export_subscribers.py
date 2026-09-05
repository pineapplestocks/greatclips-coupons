#!/usr/bin/env python3
"""
Export the D1 subscriber list to a Brevo-ready CSV.

The 9,000 addresses live in the `subscribers` table of the `greatclips-subscribers`
D1 database. They have only ever received transactional mail (one coupon each, via
worker.js), so Brevo has never seen them as a contact list. This dumps them in the
order you should mail them: newest first, because recent subscribers are the most
engaged and the least likely to have gone stale.

Deliverability note: this list has never received a bulk send. Ramp it --
    python scripts/export_subscribers.py --limit 1000                 # batch 1
    python scripts/export_subscribers.py --limit 2000 --offset 1000   # batch 2
    python scripts/export_subscribers.py --offset 3000                # the rest
Check bounce and complaint rates between batches. Hard bounces over ~5% can get
the Brevo account suspended, which would take down coupon delivery site-wide.

Requires `npx wrangler login` (or CLOUDFLARE_API_TOKEN) first.
"""

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

DB_NAME = "greatclips-subscribers"

# Dedupe on lowercased email keeping the most recent signup, drop anything that
# does not look like an address, newest first. worker.js counts total and
# DISTINCT lower(email) separately in its admin summary, so duplicates exist.
QUERY = """
SELECT email, zip_code, city, state, subscribed_at
FROM (
  SELECT email, zip_code, city, state, subscribed_at,
         ROW_NUMBER() OVER (
           PARTITION BY lower(trim(email))
           ORDER BY subscribed_at DESC
         ) AS rn
  FROM subscribers
  WHERE email LIKE '%_@_%.__%'
) WHERE rn = 1
ORDER BY subscribed_at DESC
LIMIT {limit} OFFSET {offset};
"""


def run_query(sql: str) -> list[dict]:
    """Run SQL against the remote D1 database and return the result rows."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".sql", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(sql)
        sql_path = handle.name

    try:
        proc = subprocess.run(
            ["npx", "wrangler", "d1", "execute", DB_NAME,
             "--remote", f"--file={sql_path}", "--json"],
            capture_output=True, text=True, shell=(sys.platform == "win32"),
        )
    finally:
        Path(sql_path).unlink(missing_ok=True)

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        if "Not logged in" in stderr or "authentication" in stderr.lower():
            sys.exit("Not logged in to Cloudflare. Run:  npx wrangler login")
        sys.exit(f"wrangler failed:\n{stderr}")

    # wrangler prints a banner before the JSON payload; find where it starts.
    out = proc.stdout
    start = out.find("[")
    if start == -1:
        sys.exit(f"No JSON in wrangler output:\n{out}")

    payload = json.loads(out[start:])
    if not payload or not payload[0].get("results"):
        return []
    return payload[0]["results"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=-1,
                        help="max contacts to export (-1 = all)")
    parser.add_argument("--offset", type=int, default=0,
                        help="skip this many (for ramped batches)")
    parser.add_argument("--out", default="subscribers.csv",
                        help="output CSV path")
    args = parser.parse_args()

    rows = run_query(QUERY.format(limit=args.limit, offset=args.offset))
    if not rows:
        sys.exit("No subscribers returned. Check the offset, or the table name.")

    out_path = Path(args.out)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        # Brevo maps a column literally named EMAIL to the contact address;
        # the rest import as contact attributes.
        writer = csv.writer(handle)
        writer.writerow(["EMAIL", "ZIP_CODE", "CITY", "STATE", "SUBSCRIBED_AT"])
        for row in rows:
            writer.writerow([
                (row.get("email") or "").strip().lower(),
                row.get("zip_code") or "",
                row.get("city") or "",
                row.get("state") or "",
                row.get("subscribed_at") or "",
            ])

    print(f"Wrote {len(rows):,} contacts to {out_path}")
    print(f"Date range: {rows[-1].get('subscribed_at')} .. {rows[0].get('subscribed_at')}")
    print("\nNext: Brevo > Contacts > Import > upload this CSV to a new list,")
    print("then build a *campaign* (not a transactional send) against that list.")


if __name__ == "__main__":
    main()
