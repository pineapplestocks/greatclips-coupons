"""Date-only coupon validity: an offer remains valid through its printed date."""
from datetime import date, datetime


def is_expired(coupon, today=None):
    value = str(coupon.get("expiration") or "").strip()
    if not value or value.upper() == "N/A":
        return False
    for pattern in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).date() < (today or date.today())
        except ValueError:
            continue
    return False
