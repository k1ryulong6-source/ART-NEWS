"""Small SQLite repository. Every connection explicitly enables foreign keys."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"want_to_see", "planning", "seen"}


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
            db.execute("CREATE TABLE IF NOT EXISTS preferences (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)")
            demo = json.loads((ROOT / "data/demo.json").read_text(encoding="utf-8"))
            for table in ("sources", "content", "events", "content_events"):
                columns_allowed = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
                for record in demo[table]:
                    record = {k: v for k, v in record.items() if k in columns_allowed}
                    columns = list(record)
                    db.execute(f"INSERT OR IGNORE INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", list(record.values()))

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def dataset(self, mode="demo"):
        demo = 1 if mode == "demo" else 0
        with self.connect() as db:
            content = [dict(row) for row in db.execute("SELECT * FROM content WHERE is_demo=? ORDER BY published_at DESC", (demo,))]
            events = [dict(row) for row in db.execute("SELECT * FROM events WHERE is_demo=? ORDER BY start_date", (demo,))]
            ids = {record["id"] for record in content}
            event_ids = {record["id"] for record in events}
            links = [dict(row) for row in db.execute("SELECT * FROM content_events") if row["content_id"] in ids and row["event_id"] in event_ids]
            sources = [dict(row) for row in db.execute("SELECT * FROM sources")]
        reference = "2026-10-13" if demo else datetime.now(ZoneInfo(self.preferences().get("reading_timezone", "Asia/Tokyo"))).date().isoformat()
        return {"schema_version": 1, "mode": mode, "reference_date": reference, "content": content, "events": events, "content_events": links, "sources": sources}

    def preferences(self):
        with self.connect() as db:
            row = db.execute("SELECT value FROM preferences WHERE id=1").fetchone()
        return json.loads(row[0]) if row else json.loads((ROOT / "config/preferences.json").read_text(encoding="utf-8"))

    def save_preferences(self, preferences):
        with self.connect() as db:
            db.execute("INSERT INTO preferences VALUES(1,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value", (json.dumps(preferences, ensure_ascii=False),))
        return preferences

    def bookmarks(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM bookmarks ORDER BY created_at DESC")]

    def save_bookmark(self, target_type, target_id, status="want_to_see", note=""):
        if target_type not in ("content", "event") or status not in STATUSES:
            raise ValueError("无效收藏类型或状态")
        table = "content" if target_type == "content" else "events"
        column = "content_id" if target_type == "content" else "event_id"
        stamp = now()
        with self.connect() as db:
            if not db.execute(f"SELECT id FROM {table} WHERE id=?", (target_id,)).fetchone():
                raise KeyError("内容不存在")
            old = db.execute(f"SELECT id FROM bookmarks WHERE {column}=?", (target_id,)).fetchone()
            bookmark_id = old[0] if old else str(uuid4())
            if old:
                db.execute("UPDATE bookmarks SET status=?,note=?,updated_at=? WHERE id=?", (status, note, stamp, bookmark_id))
            else:
                db.execute(f"INSERT INTO bookmarks (id,{column},status,note,created_at,updated_at) VALUES(?,?,?,?,?,?)", (bookmark_id, target_id, status, note, stamp, stamp))
            return dict(db.execute("SELECT * FROM bookmarks WHERE id=?", (bookmark_id,)).fetchone())

    def delete_bookmark(self, bookmark_id):
        with self.connect() as db:
            return db.execute("DELETE FROM bookmarks WHERE id=?", (bookmark_id,)).rowcount > 0

    def import_data(self, preferences, bookmarks):
        # Validate every reference before writing anything; import is atomic.
        stamp = now()
        with self.connect() as db:
            for item in bookmarks:
                has_content = bool(item.get("content_id"))
                has_event = bool(item.get("event_id"))
                if has_content == has_event or item.get("status") not in STATUSES:
                    raise ValueError("导入收藏格式无效")
                table, key = ("content", "content_id") if has_content else ("events", "event_id")
                if not db.execute(f"SELECT id FROM {table} WHERE id=?", (item[key],)).fetchone():
                    raise ValueError("导入收藏引用了当前不存在的内容；请先恢复对应内容库")
            db.execute("INSERT INTO preferences VALUES(1,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value", (json.dumps(preferences, ensure_ascii=False),))
            for item in bookmarks:
                key = "content_id" if item.get("content_id") else "event_id"
                old = db.execute(f"SELECT id FROM bookmarks WHERE {key}=?", (item[key],)).fetchone()
                if old:
                    db.execute("UPDATE bookmarks SET status=?,note=?,updated_at=? WHERE id=?", (item["status"], item.get("note", ""), stamp, old[0]))
                else:
                    db.execute(f"INSERT INTO bookmarks(id,{key},status,note,created_at,updated_at) VALUES(?,?,?,?,?,?)", (str(uuid4()), item[key], item["status"], item.get("note", ""), stamp, stamp))
        return len(bookmarks)
