import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

from video.planner import build_plan, classify_amount, fingerprint, inspect_offer, verify_offer, VERSION
from video.render import approximate_cues, group_boundaries, timestamp, Speaker
from video.__main__ import metadata, write_json

TODAY=date(2026,9,16)


def page(description="$8.99 haircut",terms="Valid at Great Clips in Ocala. Expires 10/09/2026"):
    return f'<div id="description">{description}</div><div id="terms_and_conditions">{terms}</div>'


def row(city="Ocala"):
    return {"url":"https://offers.greatclips.com/example","city":city,"address":"123 Example Street","location_name":"Example Salon"}


class PlanningTests(unittest.TestCase):
    def test_bare_price_never_becomes_haircut_price(self):
        self.assertIsNone(classify_amount("Coupon $5.00"))
        self.assertEqual(classify_amount("Save $5.00 on a haircut"),("amount_off","5.00"))
        self.assertEqual(classify_amount("$8.99 haircut"),("haircut_price","8.99"))

    def test_conflicting_prices_declined(self):
        self.assertIsNone(classify_amount("$5 off a $20 haircut"))
        self.assertIsNone(classify_amount("$8.99 haircut or $10.99 haircut"))

    def test_expiration_required_and_near_expiry_declined(self):
        for text in ["Valid in Ocala", "Valid in Ocala. Expires 09/17/2026", "Valid in Ocala. Expires 08/31/2026"]:
            offer,reason=inspect_offer(row(),page(terms=text),TODAY)
            self.assertIsNone(offer)
            self.assertTrue(reason)

    def test_confirmed_local_offer(self):
        offer,reason=inspect_offer(row(),page(),TODAY)
        self.assertIsNone(reason)
        self.assertEqual(offer["label"],"$8.99 haircut")
        self.assertEqual(offer["location"],"Ocala")

    def test_wrong_location_and_missing_sections_declined(self):
        self.assertIsNone(inspect_offer(row("Tampa"),page(),TODAY)[0])
        self.assertIsNone(inspect_offer(row(),"<p>$8.99 haircut</p>",TODAY)[0])

    def test_hidden_expired_template_does_not_override_real_terms(self):
        self.assertIsNotNone(inspect_offer(row(),page()+'<template>This offer has ended</template>',TODAY)[0])
        self.assertIsNone(inspect_offer(row(),page("This offer has ended"),TODAY)[0])

    def test_first_run_is_evergreen_without_network(self):
        def fail(*args):
            raise AssertionError("Should not fetch offers for an evergreen tutorial")
        plan=build_plan({"coupons":[row()]},{"videos":[]},today=TODAY,verifier=fail)
        self.assertEqual(plan["type"],"guide")
        self.assertEqual(len(plan["scenes"]),9)

    def test_guide_deduplication(self):
        state={"videos":[{"id":fingerprint(VERSION),"type":"guide"}]}
        self.assertEqual(build_plan({},state,mode="guide",today=TODAY)["status"],"skipped")

    def test_no_new_deals_skips(self):
        plan=build_plan({"coupons":[row()]},{"videos":[]},"deals",TODAY,
                        verifier=lambda *args:(None,"unavailable"))
        self.assertEqual(plan["status"],"skipped")
        self.assertEqual(len(plan["rejected"]),1)

    def test_deal_dedupe_and_reissued_codes(self):
        def verify(c,today):
            return inspect_offer(c,page(terms=f"Valid in {c['city']}. Expires 10/09/2026"),today)
        feed={"coupons":[row(),row(),row("Tampa")]}
        plan=build_plan(feed,{"videos":[]},"deals",TODAY,verify)
        self.assertEqual(len(plan["offers"]),2)
        state={"videos":[{"id":plan["id"],"type":"deals","date":"2026-09-01","offer_keys":[o["key"] for o in plan["offers"]]}]}
        self.assertEqual(build_plan(feed,state,"deals",TODAY,verify)["status"],"skipped")

    def test_weekly_limit_prevents_fetches(self):
        state={"videos":[{"id":"prior","type":"deals","date":"2026-09-14"}]}
        self.assertEqual(build_plan({},state,"deals",TODAY)["status"],"skipped")

    def test_local_videos_keep_locations_separate_and_deduplicate(self):
        def verify(c,today):
            return inspect_offer(c,page(terms=f"Valid in {c['city']}. Expires 10/09/2026"),today)
        feed={"coupons":[row(),row("Tampa")]}
        first=build_plan(feed,{"videos":[]},"local",TODAY,verify)
        self.assertEqual(first["location"],"Ocala")
        self.assertEqual(len(first["offers"]),1)
        self.assertIn("123 Example Street",first["scenes"][1]["narration"])
        state={"videos":[{"id":first["id"],"type":"local","date":TODAY.isoformat(),
                          "location":"Ocala","offer_keys":[o["key"] for o in first["offers"]]}]}
        second=build_plan(feed,state,"local",TODAY,verify)
        self.assertEqual(second["location"],"Tampa")
        state["videos"].append({"id":second["id"],"type":"local","date":TODAY.isoformat(),
                                "location":"Tampa","offer_keys":[o["key"] for o in second["offers"]]})
        self.assertEqual(build_plan(feed,state,"local",TODAY,verify)["status"],"skipped")

    def test_local_weekly_limit_applies_to_new_offers_in_same_location(self):
        state={"videos":[{"id":"prior","type":"local","location":"Ocala","date":"2026-09-14"}]}
        plan=build_plan({"coupons":[row()]},state,"local",TODAY,
                        verifier=lambda c,t:inspect_offer(c,page(),t))
        self.assertEqual(plan["status"],"skipped")

    def test_untrusted_or_malformed_urls_never_fetched(self):
        with patch("video.planner.requests.get") as request:
            for url in ["http://offers.greatclips.com/test","https://example.com/test",
                        "https://offers.greatclips.com:invalid/test", "https://user@offers.greatclips.com/test"]:
                self.assertIsNone(verify_offer({"url":url},TODAY)[0])
            request.assert_not_called()

    def test_redirects_and_network_failures_declined(self):
        import requests
        with patch("video.planner.requests.get") as request:
            request.return_value.status_code=302
            self.assertIsNone(verify_offer(row(),TODAY)[0])
            request.side_effect=requests.Timeout()
            self.assertIsNone(verify_offer(row(),TODAY)[0])


class MediaTests(unittest.TestCase):
    def test_captions_supplement_automatic_tracks_but_preserve_uploaded_english(self):
        from video.youtube import upload_captions
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'captions.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nHello\n')
            service=MagicMock()
            service.captions().list().execute.return_value={'items':[{'snippet':{'language':'en','trackKind':'asr'}}]}
            self.assertEqual(upload_captions(service,'video',p),'uploaded')
            service.captions().insert.assert_called_once()
            service.captions().list().execute.return_value={'items':[{'snippet':{'language':'en','trackKind':'standard'}}]}
            self.assertEqual(upload_captions(service,'video',p),'existing')
            service.captions().insert.assert_called_once()

    def test_live_metadata_edit_preserves_privacy_and_backs_up_snippet(self):
        from video.youtube import update_metadata
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'youtube-receipt.json').write_text(json.dumps({'video_id':'owned-video'}))
            desired={'title':'New title','description':'Accurate new description','tags':['coupon','haircut']}
            (p/'youtube.json').write_text(json.dumps({'snippet':desired}))
            old={'title':'Old title','description':'Old description','tags':[],
                 'categoryId':'26','defaultLanguage':'en','defaultAudioLanguage':'en'}
            service=MagicMock();credentials=MagicMock()
            service.videos().list().execute.return_value={'items':[{'snippet':old}]}
            service.videos().update().execute.return_value={'snippet':{**old,**desired,'tags':['haircut','coupon']}}
            with patch('video.youtube.connect',return_value=(service,credentials)),patch('video.youtube.upload_captions',return_value='uploaded'):
                result=update_metadata(p)
            call=service.videos().update.call_args.kwargs
            self.assertEqual(call['part'],'snippet')
            self.assertNotIn('status',call['body'])
            self.assertEqual(call['body']['snippet']['defaultAudioLanguage'],'en')
            self.assertEqual(json.loads((p/'youtube-before-seo.json').read_text())['snippet'],old)
            self.assertTrue(result['seo_updated'])

    def test_robotic_voice_cannot_be_selected_or_used_as_fallback(self):
        with self.assertRaises(ValueError):
            Speaker("sapi")
        with tempfile.TemporaryDirectory() as d:
            speaker=Speaker("auto",cache=Path(d))
            self.assertEqual(speaker.provider,"kokoro")

    def test_neural_failure_does_not_call_windows_voice(self):
        with tempfile.TemporaryDirectory() as d:
            speaker=Speaker("kokoro",cache=Path(d)/"cache")
            with patch("video.neural.NeuralVoice.speak",side_effect=RuntimeError("model unavailable")),patch("video.render.subprocess.run") as shell:
                with self.assertRaises(RuntimeError):
                    speaker.speak("Test narration.",Path(d)/"test.wav")
                shell.assert_not_called()

    def test_fast_cut_chapters_are_grouped(self):
        plan=build_plan({}, {"videos":[]},today=TODAY)
        timeline=[{"start":i*5,"duration":5,"title":f"Step {i}"} for i in range(9)]
        description=metadata(plan,timeline)["snippet"]["description"]
        self.assertIn("00:00",description)
        self.assertIn("00:10",description)
        self.assertIn("00:30",description)
        self.assertNotIn("00:05",description)
        self.assertNotIn("00:40",description)

    def test_motion_frames_change_with_time(self):
        from video.motion import frame
        from PIL import ImageChops
        shot=build_plan({}, {"videos":[]},today=TODAY)["scenes"][2]
        a=frame(shot,.1,5,2,9,height=720)
        b=frame(shot,1.4,5,2,9,height=720)
        self.assertEqual(a.size,(1280,720))
        self.assertIsNotNone(ImageChops.difference(a,b).getbbox())

    def test_timestamps_carry_minutes(self):
        self.assertEqual(timestamp(59.9996),"00:01:00,000")
        self.assertEqual(timestamp(60.25,True),"0:01:00.25")

    def test_fallback_captions_cover_audio(self):
        cues=approximate_cues("This is a short sentence with enough words to test caption grouping.",10)
        self.assertEqual(cues[0]["start"],0)
        self.assertAlmostEqual(cues[-1]["end"],10)
        self.assertTrue(all(c["end"] > c["start"] for c in cues))

    def test_neural_caption_boundaries_clamped(self):
        cues=group_boundaries([{"start":0,"end":2,"text":"Hello"}],1.9)
        self.assertEqual(cues[0]["end"],1.9)

    def test_metadata_tracking_and_chapters(self):
        plan=build_plan({}, {"videos":[]},today=TODAY)
        result=metadata(plan,[{"start":0,"duration":10,"title":"Introduction"},
                              {"start":10,"duration":10,"title":"Find your city"},
                              {"start":20,"duration":10,"title":"Use the coupon"}])
        self.assertIn("utm_source=youtube",result["snippet"]["description"])
        self.assertIn("00:20 Search coupons near your salon",result["snippet"]["description"])
        self.assertLess(len(result["snippet"]["title"]),100)

    def test_short_video_does_not_claim_invalid_chapters(self):
        plan=build_plan({}, {"videos":[]},today=TODAY)
        result=metadata(plan,[{"start":0,"duration":9,"title":"Intro"},
                              {"start":9,"duration":9,"title":"Offer"}])
        self.assertNotIn('CHAPTERS',result['snippet']['description'])

    def test_local_seo_keeps_offer_type_location_and_expiration(self):
        plan=build_plan({'coupons':[row()]},{'videos':[]},'local',TODAY,
                        verifier=lambda c,t:inspect_offer(c,page('$5 off a haircut'),t))
        result=metadata(plan,[])['snippet']
        self.assertIn('Ocala',result['title'])
        self.assertIn('$5.00 OFF',result['title'])
        self.assertNotIn('$5.00 haircut',result['title'])
        self.assertIn('123 Example Street',result['description'])
        self.assertIn('2026-10-09',result['description'])
        self.assertIn('not nationwide',result['description'])
        self.assertLess(len(result['description']),5000)
        self.assertLess(sum(len(t)+3 for t in result['tags']),500)

    def test_atomic_state_write(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"state.json"
            write_json(path,{"videos":[]})
            self.assertEqual(json.loads(path.read_text()),{"videos":[]})
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_failed_render_does_not_advance_state(self):
        from video.__main__ import main
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"feed.json").write_text('{"coupons":[]}')
            argv=["video","--feed",str(p/"feed.json"),"--state",str(p/"state.json"),"--output",str(p/"out")]
            with patch("sys.argv",argv),patch("video.render.create_video",side_effect=RuntimeError("test failure")):
                with self.assertRaises(RuntimeError):
                    main()
            self.assertFalse((p/"state.json").exists())
            self.assertEqual(json.loads((p/"out/run.json").read_text())["status"],"failed")

    def test_uncertain_upload_persists_intent_to_prevent_duplicates(self):
        from video.__main__ import main
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"feed.json").write_text('{"coupons":[]}')
            argv=["video","--feed",str(p/"feed.json"),"--state",str(p/"state.json"),"--output",str(p/"out"),"--upload"]
            with patch("sys.argv",argv),patch("video.render.create_video",return_value=[]),patch("video.youtube.upload",side_effect=RuntimeError("network lost")):
                with self.assertRaises(RuntimeError):
                    main()
            state=json.loads((p/"state.json").read_text())
            self.assertEqual(state["videos"][0]["status"],"upload_started")
            self.assertEqual(build_plan({},state,mode="guide",today=TODAY)["status"],"skipped")


if __name__ == "__main__":
    unittest.main()
