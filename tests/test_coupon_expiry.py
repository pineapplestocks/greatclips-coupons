import contextlib
import io
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
import generate_website as website
from coupon_validity import is_expired


class CouponExpiryTests(unittest.TestCase):
    def test_printed_date_is_inclusive(self):
        today = date(2026, 10, 28)
        self.assertTrue(is_expired({"expiration": "10/27/2026"}, today))
        self.assertFalse(is_expired({"expiration": "10/28/2026"}, today))
        self.assertFalse(is_expired({"expiration": "10/29/2026"}, today))
        self.assertTrue(is_expired({"expiration": "2026-10-27"}, today))
        self.assertFalse(is_expired({"expiration": None}, today))

    def test_build_unicode_and_expiry(self):
        today = date.today()
        def coupon(name, expiry):
            return {"url": "https://offers.greatclips.com/" + name,
                    "price": "$9.99", "location_name": name, "state": "AZ",
                    "type": "local", "expiration": expiry}
        current = coupon("Café – birthday 🎂", today.strftime("%m/%d/%Y"))
        expired = coupon("ExpiredRegressionOffer", (today-timedelta(days=1)).strftime("%m/%d/%Y"))
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)/"coupons.json"
            output = Path(tmp)/"index.html"
            data.write_text(json.dumps({"scraped_at": today.isoformat(), "coupons": [current, expired]}), encoding="utf-8")
            with patch.object(website, "DATA_FILE", str(data)), patch.object(website, "OUTPUT_DIR", tmp), patch.object(website, "OUTPUT_FILE", str(output)), patch.object(website, "expand_area_coupons", return_value=[]), contextlib.redirect_stdout(io.StringIO()):
                website.generate_website()
            html = output.read_text(encoding="utf-8")
            self.assertIn("Caf", html)
            self.assertIn("\\u00e9", html)
            self.assertNotIn("ExpiredRegressionOffer", html)
            self.assertIn("isCurrentCoupon", html)
        self.assertEqual(website.get_expiration({}), "See official offer")

if __name__ == "__main__":
    unittest.main()
