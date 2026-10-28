import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from scripts.audit_coupon_pipeline import audit

class CouponPublicationTests(unittest.TestCase):
    def fixture(self, root):
        (root/"data").mkdir();(root/"docs/data").mkdir(parents=True)
        item={"url":"https://offers.greatclips.com/test", "price":"$9.99", "location_name":"Test", "expiration":(date.today()+timedelta(days=5)).strftime("%m/%d/%Y")}
        (root/"data/coupons.json").write_text(json.dumps({"scraped_at":"scan", "coupons":[item]}),encoding="utf-8")
        (root/"docs/data/coupons.json").write_text(json.dumps({"scraped_at":"scan", "total":1, "coupons":[item]}),encoding="utf-8")
        (root/"docs/index.html").write_text('const COUPON_DATA = '+json.dumps([item])+';',encoding="utf-8")
        (root/"docs/sw.js").write_text('self.registration.unregister();',encoding="utf-8")
        return item

    def test_consistent_current_publication_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            self.assertEqual(audit(root)["errors"], [])

    def test_expired_and_mismatched_feed_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);item=self.fixture(root);item["expiration"]="01/01/2000"
            (root/"docs/data/coupons.json").write_text(json.dumps({"total":2,"coupons":[item]}),encoding="utf-8")
            errors=audit(root)["errors"]
            self.assertTrue(any("expired" in e for e in errors))
            self.assertTrue(any("does not match" in e for e in errors))
            self.assertTrue(any("total" in e for e in errors))

    def test_navigation_proxy_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            (root/"docs/sw.js").write_text("const INDEX_SOURCE='raw.githubusercontent.com';",encoding="utf-8")
            self.assertTrue(any("service-worker" in e for e in audit(root)["errors"]))
