import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
import scraper

FUTURE = (date.today() + timedelta(days=7)).strftime("%m/%d/%Y")
PAST = (date.today() - timedelta(days=1)).strftime("%m/%d/%Y")


def offer(expiry=FUTURE, price="$9.99", hidden_ended=False):
    hidden = '<div style="display:none">This offer has ended</div>' if hidden_ended else ''
    return '<div id="description">Great Clips haircut for '+price+'</div><div id="terms_and_conditions">Valid at participating Denver area Great Clips salons. Offer expires '+expiry+'.</div>'+hidden


def record(**fields):
    return {"url":"https://offers.greatclips.com/test", "price":"$9.99", "state":"AREA", "area_name":"Denver", "expiration":FUTURE, "last_verified":"2026-01-01", **fields}


class CouponScraperTests(unittest.TestCase):
    def setUp(self):
        self.logs=contextlib.redirect_stdout(io.StringIO()); self.logs.__enter__()
    def tearDown(self):
        self.logs.__exit__(None,None,None)

    def test_expired_discovered_record_cannot_return(self):
        self.assertEqual(scraper.merge_coupons([record(expiration=PAST)], [record(expiration=PAST)]), [])

    def test_expired_rediscovery_invalidates_cached_future_date(self):
        self.assertEqual(scraper.merge_coupons([record()], [record(expiration=PAST)]), [])

    def test_expired_source_url_is_reported_for_removal(self):
        rejected=set()
        with patch.object(scraper, "fetch_html", return_value=offer(PAST)):
            self.assertEqual(scraper.fetch_offer_details([record()["url"]], rejected), [])
        self.assertEqual(rejected, {record()["url"]})

    def test_changed_terms_refresh_existing_record(self):
        result=scraper.merge_coupons([record()], [record(price="$12.99", area_name="New region")])
        self.assertEqual(result[0]["price"], "$12.99")
        self.assertEqual(result[0]["area_name"], "New region")

    def test_challenge_cannot_create_offer(self):
        with patch.object(scraper, "fetch_html", return_value='<html>Checking your browser. Please wait.</html>'):
            self.assertEqual(scraper.fetch_offer_details([record()["url"]]), [])

    def test_unreadable_does_not_refresh_verification(self):
        for html in ('<html>Checking your browser</html>', '<html>Service unavailable</html>', None):
            with self.subTest(html=html), patch.object(scraper, "fetch_html", return_value=html):
                result=scraper.purge_ended_offers([record()])
                self.assertEqual(result[0]["last_verified"], "2026-01-01")

    def test_live_terms_override_future_cached_expiration(self):
        with patch.object(scraper, "fetch_html", return_value=offer(PAST)):
            self.assertEqual(scraper.purge_ended_offers([record()]), [])

    def test_manual_ended_offer_is_removed(self):
        with patch.object(scraper, "fetch_html", return_value='<h1>This offer is no longer available</h1>'):
            self.assertEqual(scraper.purge_ended_offers([record(manual_add=True)]), [])

    def test_hidden_ended_template_does_not_drop_live_offer(self):
        with patch.object(scraper, "fetch_html", return_value=offer(hidden_ended=True)):
            result=scraper.purge_ended_offers([record()])
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["last_verified"], date.today().isoformat())

    def test_live_price_is_authoritative(self):
        with patch.object(scraper, "fetch_html", return_value=offer(price="$12.99")):
            self.assertEqual(scraper.purge_ended_offers([record()])[0]["price"], "$12.99")

    def test_expired_new_page_is_skipped(self):
        with patch.object(scraper, "fetch_html", return_value=offer(PAST)):
            self.assertEqual(scraper.fetch_offer_details([record()["url"]]), [])

    def test_verification_report_records_unavailable_pages(self):
        report = {}
        with patch.object(scraper, "fetch_html", return_value='<p>Checking your browser</p>'):
            scraper.purge_ended_offers([record()], report)
        self.assertEqual(report, {"attempted":1, "verified":0, "removed":0, "unavailable":1})

    def test_no_successful_refresh_when_every_offer_is_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"coupons.json"
            path.write_text(json.dumps({"coupons":[record()]}), encoding="utf-8")
            before=path.read_text(encoding="utf-8")
            with patch.object(scraper, "DATA_DIR",tmp), patch.object(scraper,"JSON_FILE",str(path)), patch.object(scraper,"fetch_html",return_value=None):
                with self.assertRaisesRegex(RuntimeError,"No offer pages"):
                    scraper.save_results([])
            self.assertEqual(path.read_text(encoding="utf-8"),before)

    def test_long_market_name_does_not_get_truncated(self):
        html = offer().replace('Denver', 'Orlando, Ocala, Daytona Beach & Melbourne')
        with patch.object(scraper, "fetch_html", return_value=html):
            result=scraper.fetch_offer_details([record()["url"]])
        self.assertEqual(result[0]["area_name"], 'Orlando, Ocala, Daytona Beach & Melbourne')

    def test_direct_script_import_works_outside_repository(self):
        scripts = str(Path(__file__).resolve().parents[1]/"scripts")
        env=os.environ.copy(); env.pop("PYTHONPATH",None)
        with tempfile.TemporaryDirectory() as tmp:
            run=subprocess.run([sys.executable,"-c","import sys; sys.path.insert(0, "+repr(scripts)+"); import national_offer"],cwd=tmp,env=env,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)

if __name__ == "__main__":
    unittest.main()
