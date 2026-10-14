"""Data persistence and import checks; no server, network or account is needed."""
import json
import asyncio
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.storage import Store
from backend.app import create_app, Preferences, BookmarkInput, ImportInput
from fastapi import HTTPException
from pydantic import ValidationError
import httpx


class StorageChecks(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / "desk.db"
        self.store = Store(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_mode_separation_and_country_dates(self):
        demo = self.store.dataset()
        self.assertTrue(all(record["is_demo"] == 1 for record in demo["content"] + demo["events"]))
        self.assertEqual(self.store.dataset("live")["content"], [])
        releases = {row["country"]: row for row in demo["events"] if row["event_type"] == "cinema_release"}
        self.assertEqual(releases["JP"]["start_date"], "2026-10-16")
        self.assertEqual(releases["CN"]["start_date"], "2026-10-23")
        self.assertEqual(releases["JP"]["timezone"], "Asia/Tokyo")

    def test_restart_and_idempotent_bookmark(self):
        first = self.store.save_bookmark("content", "demo-film")
        updated = self.store.save_bookmark("content", "demo-film", "planning")
        self.assertEqual(first["id"], updated["id"])
        restarted = Store(self.path)
        self.assertEqual(len(restarted.bookmarks()), 1)
        self.assertEqual(restarted.bookmarks()[0]["status"], "planning")
        self.assertTrue(restarted.delete_bookmark(first["id"]))
        self.assertFalse(restarted.delete_bookmark(first["id"]))

    def test_export_restore_twice_and_atomic_rejection(self):
        self.store.save_bookmark("content", "demo-film", "seen", "想再看一次")
        self.store.save_bookmark("event", "demo-photo-tokyo", "planning")
        prefs = self.store.preferences()
        prefs["default_city"] = "京都"
        target = Store(Path(self.temp.name) / "restored.db")
        for _ in range(2):
            target.import_data(prefs, self.store.bookmarks())
        self.assertEqual(len(target.bookmarks()), 2)
        self.assertEqual(target.preferences()["default_city"], "京都")
        before = target.preferences()
        invalid = [{"content_id": "not-present", "status": "seen"}]
        with self.assertRaises(ValueError):
            target.import_data({**prefs, "default_city": "大阪"}, invalid)
        self.assertEqual(target.preferences(), before)
        self.assertEqual(len(target.bookmarks()), 2)

    def test_invalid_target_and_preferences_validation(self):
        with self.assertRaises(KeyError):
            self.store.save_bookmark("content", "missing")
        with self.assertRaises(ValueError):
            self.store.save_bookmark("content", "demo-film", "invalid")
        with self.assertRaises(ValidationError):
            ImportInput(schema_version=1, preferences={}, bookmarks=[{"content_id": "demo-film", "event_id": "demo-film-jp", "status": "seen"}])
        self.assertFalse(Preferences(industry_buzz={"enabled": True, "max_share": .1, "include_unverified_in_today": True}).safe_dict()["industry_buzz"]["include_unverified_in_today"])
        with self.assertRaises(ValueError):
            Preferences(industry_buzz={"enabled": True, "max_share": 3}).safe_dict()

    def test_api_handlers_filter_and_write(self):
        async def check_http():
            app = create_app(Path(self.temp.name) / "api.db")
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://local.test") as client:
                self.assertEqual((await client.get("/api/health")).json()["status"], "ok")
                for path in ("/", "/styles.css", "/theme.css", "/core.js", "/ui.js", "/app.js", "/data.js"):
                    self.assertEqual((await client.get(path)).status_code, 200)
                self.assertEqual((await client.get("/runtime/culture-desk.db")).status_code, 404)
                tokyo = (await client.get("/api/events", params={"city": "东京", "mode": "demo"})).json()
                self.assertTrue(tokyo)
                self.assertTrue(all(row["country"] == "JP" and row["city"] in ("东京", None) for row in tokyo))
                shanghai = (await client.get("/api/content", params={"city": "上海", "q": "新展", "mode": "demo"})).json()
                self.assertTrue(shanghai)
                self.assertTrue(all(row["country"] == "CN" for row in shanghai))
                response = await client.post("/api/bookmarks", json={"target_type": "event", "target_id": "demo-film-jp", "status": "planning"})
                self.assertEqual(response.status_code, 200)
                row = response.json()
                exported = (await client.get("/api/export")).json()
                self.assertEqual(exported["bookmarks"][0]["id"], row["id"])
                response = await client.post("/api/import", json=exported)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len((await client.get("/api/bookmarks")).json()), 1)
                self.assertEqual((await client.post("/api/bookmarks", json={"target_type": "content", "target_id": "missing"})).status_code, 404)
                self.assertEqual((await client.post("/api/import", json={**exported, "bookmarks": [{"content_id": "missing", "status": "seen"}]})).status_code, 422)
                self.assertEqual((await client.get("/api/dataset", params={"mode": "live"})).json()["content"], [])
        asyncio.run(check_http())


if __name__ == "__main__":
    unittest.main()
