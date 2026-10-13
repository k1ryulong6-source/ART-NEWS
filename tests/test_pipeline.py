import asyncio
import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import httpx

from backend.storage import Store
from backend.ingestion import rss_records, eiga_records, top_records, content_record, event_record, run_ingestion
from backend.enrichment import NoOpProvider, OpenAICompatibleProvider, run_enrichment
from backend.jobs import notify, refresh
from backend.mail import send_notifications
from backend.app import create_app

SOURCE = {"id": "test-source", "name": "Test", "homepage_url": "https://example.invalid", "channels": ["film"], "country": "JP", "language": "ja", "source_type": "media", "access_status": "reviewed", "access_method": "rss", "enabled": True, "verified_at": "2026-10-13", "feed_url": "https://example.invalid/rss"}


class PipelineChecks(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "test.db")
        self.store.register_sources([SOURCE])

    def tearDown(self):
        self.temp.cleanup()

    def record(self, suffix="one", excerpt="Some cultural news"):
        return content_record(SOURCE, "Test movie " + suffix, "https://example.invalid/" + suffix, excerpt)

    def test_rss_gear_filter_and_canonical_tracking_dedup(self):
        xml = b'''\n<?xml version="1.0"?><rss><channel><item><title>Camera review: new camera</title><link>https://example.invalid/gear</link></item><item><title>Director interview</title><link>https://example.invalid/movie?utm_source=x</link><description>&lt;p&gt;A short interview&lt;/p&gt;</description></item></channel></rss>'''
        records, _, _ = rss_records(SOURCE, xml)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["canonical_url"], "https://example.invalid/movie")
        for _ in range(2):
            self.store.ingest_records(records, [], [])
        self.assertEqual(len(self.store.dataset("live")["content"]), 1)

    def test_release_adapter_distinguishes_streaming_and_cinema(self):
        page = '''<h2>2026年 10月16日 公開・配信開始</h2><div class="list-block"><h3 class="title"><a href="/movie/1/">A movie</a></h3><p class="txt">劇場公開</p><a href="/movie/1/theater/">theater</a></div><div class="list-block"><h3 class="title"><a href="/movie/2/">B movie</a></h3><p class="txt">Netflixで配信</p></div>'''
        records, events, links = eiga_records(SOURCE, page)
        self.assertEqual(len(records), 2)
        self.assertEqual([row["event_type"] for row in events], ["cinema_release", "streaming_release"])
        self.assertTrue(all(row["start_date"] == "2026-10-16" and row["timezone"] == "Asia/Tokyo" for row in events))
        self.assertEqual(len(links), 2)

    def test_official_exhibition_requires_explicit_two_dates(self):
        source = {**SOURCE, "channels": ["photography"], "source_type": "official"}
        page = '''<a href="https://example.invalid/exhibition/1/"><img alt="A test exhibition"><span data-date="2026-10-01"></span><span data-date="2026-10-18"></span></a>'''
        records, events, _ = top_records(source, page)
        self.assertEqual(events[0]["end_date"], "2026-10-18")
        self.assertEqual(events[0]["evidence_status"], "official_confirmed")
        self.assertEqual(records[0]["city"], "东京")
        with self.assertRaises(ValueError):
            top_records(source, '<a href="/exhibition/2"><img alt="No dates"></a>')

    def test_date_update_keeps_event_and_bookmark_identity(self):
        record = self.record()
        event = event_record(SOURCE, record, "cinema_release", "2026-10-16")
        self.store.ingest_records([record], [event], [{"content_id": record["id"], "event_id": event["id"]}])
        self.store.save_bookmark("event", event["id"])
        changed = event_record(SOURCE, record, "cinema_release", "2026-10-23")
        self.store.ingest_records([record], [changed], [])
        self.assertEqual(changed["id"], event["id"])
        self.assertEqual(self.store.dataset("live")["events"][0]["start_date"], "2026-10-23")
        self.assertEqual(self.store.bookmarks()[0]["event_id"], event["id"])

    def test_model_output_cache_budget_and_no_event_mutation(self):
        record = self.record()
        event = event_record(SOURCE, record, "cinema_release", "2026-10-16")
        self.store.ingest_records([record, self.record("two")], [event], [])
        calls = []
        def fake(payload):
            calls.append(payload)
            return {"choices": [{"message": {"content": json.dumps({"title_zh": "测试电影", "summary_zh": "一条测试摘要", "start_date": "2099-01-01"})}}]}
        provider = OpenAICompatibleProvider(key="test-only", model="mock", transport=fake)
        result = run_enrichment(self.store, provider, daily_limit=1)
        self.assertEqual(result["ready"], 1)
        self.assertTrue(result["budget_exhausted"])
        run_enrichment(self.store, provider, daily_limit=1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.store.dataset("live")["events"][0]["start_date"], "2026-10-16")

    def test_no_model_and_failure_preserve_readable_originals(self):
        record = self.record()
        self.store.ingest_records([record], [], [])
        self.assertEqual(run_enrichment(self.store, NoOpProvider())["disabled"], 1)
        provider = OpenAICompatibleProvider(key="test-only", transport=lambda _: {"choices": []})
        self.assertEqual(run_enrichment(self.store, provider, daily_limit=1)["failed"], 1)
        original = self.store.dataset("live")["content"][0]
        self.assertEqual(original["canonical_url"], record["canonical_url"])
        self.assertEqual(original["title_original"], record["title_original"])

    def test_favorites_notifications_are_idempotent_and_seen_is_excluded(self):
        record = self.record()
        event = event_record(SOURCE, record, "exhibition", "2026-10-01", "2026-10-18")
        self.store.ingest_records([record], [event], [])
        self.assertEqual(notify(self.store, "2026-10-13"), 0)
        self.store.save_bookmark("event", event["id"])
        self.assertEqual(notify(self.store, "2026-10-13"), 1)
        self.assertEqual(notify(self.store, "2026-10-13"), 0)
        self.store.save_bookmark("event", event["id"], "seen")
        self.assertEqual(notify(self.store, "2026-10-14"), 0)

    def test_mail_disabled_and_mock_delivery_not_repeated(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(send_notifications(self.store)["status"], "disabled")
        record = self.record(); event = event_record(SOURCE, record, "exhibition", "2026-10-01", "2026-10-18")
        self.store.ingest_records([record], [event], []); self.store.save_bookmark("event", event["id"]); notify(self.store, "2026-10-13")
        class FakeSMTP:
            def __init__(self, *a, **kw): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def starttls(self, **kw): pass
            def send_message(self, message): self.message = message
        with patch.dict(os.environ, {"SMTP_HOST": "example.invalid", "SMTP_FROM": "owner@example.invalid", "SMTP_TO": "owner@example.invalid"}, clear=True), patch("backend.mail.datetime") as clock:
            clock.now.return_value = datetime(2026, 10, 13, tzinfo=timezone.utc)
            self.assertEqual(send_notifications(self.store, FakeSMTP)["sent"], 1)
            self.assertEqual(send_notifications(self.store, FakeSMTP)["sent"], 0)

    def test_optional_access_password_and_read_notification_http(self):
        async def run():
            with patch.dict(os.environ, {"CULTURE_DESK_PASSWORD": "test-only"}):
                app = create_app(Path(self.temp.name) / "protected.db")
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://local.test") as client:
                self.assertEqual((await client.get("/api/health")).status_code, 401)
                self.assertEqual((await client.get("/api/health", auth=("owner", "test-only"))).status_code, 200)
                self.assertEqual((await client.get("/api/health", auth=("陌生人", "test-only"))).status_code, 401)
                self.assertEqual((await client.get("/api/notifications", auth=("owner", "test-only"))).json(), [])
        asyncio.run(run())
